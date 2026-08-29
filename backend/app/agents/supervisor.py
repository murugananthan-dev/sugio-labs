import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.schemas import (
    WSMessage,
    WSMessageType,
    AgentActivityLog,
    RequirementQuestion,
    RequirementSpec,
    ProjectBlueprint,
    ContractNode,
    ContractEdge,
    ContractNodeType,
    ContractNodeStatus,
    ContractGraphData,
    ImpactReport,
    PermissionRequest,
    PermissionResponse,
    PermissionDecision,
    PermissionAction,
    AppState,
    ExecutionPlan,
    ExecutionResult,
)
from .requirement_agent import requirement_agent
from .blueprint_agent import blueprint_agent
from .execution_planner import execution_planner
from .coding_agent import coding_agent
from .base import local_llm

from langgraph.graph import StateGraph, START, END
from ..contract_graph.graph import contract_graph
from ..permissions.manager import permission_manager

logger = logging.getLogger("sugio_labs.agents.supervisor")

# Graph Nodes
def requirement_node(state: AppState) -> AppState:
    """Invokes RequirementAgent to update Requirements and decide on next question."""
    return requirement_agent.process(state)

def blueprint_node(state: AppState) -> AppState:
    """Invokes BlueprintAgent to generate architecture blueprint from requirements."""
    state = blueprint_agent.process(state)
    state["approval_status"] = "WAITING_FOR_APPROVAL"
    return state

def execution_planner_node(state: AppState) -> AppState:
    """Invokes ExecutionPlanner to map out execution steps."""
    return execution_planner.process(state)

async def git_checkpoint_node(state: AppState) -> AppState:
    """Takes a git checkpoint before modifying code.

    HARD GATE: If checkpoint creation fails, sets execution_approval_status to
    FAILED and returns immediately. No file mutations may proceed without a
    successful checkpoint.
    """
    from ..tools.git_tools import GitTool
    git_tool = GitTool()
    try:
        cp = git_tool.create_checkpoint(
            name=f"auto_before_exec_{state['session_id'][:6]}",
            description="Automatic checkpoint before agent execution."
        )
        state["git_checkpoint_id"] = cp.id
        logger.info(f"Git checkpoint created: {cp.id}")
    except Exception as exc:
        reason = f"Git checkpoint creation failed: {exc}. Execution blocked — no files will be modified."
        logger.error(reason)
        state["execution_approval_status"] = "FAILED"
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(reason)
        # Do NOT set git_checkpoint_id — absence is the hard gate in CodingAgent
    return state

async def coding_agent_node(state: AppState) -> AppState:
    """Executes one step from the execution plan."""
    return await coding_agent.process(state)

async def validation_node(state: AppState) -> AppState:
    """Validates the execution step by running its declared shell commands.

    Permission note: ShellTool.execute() carries its own single permission check.
    We do NOT call is_action_permitted() here before the tool call — that would
    consume ALLOW_ONCE grants and break single-use semantics.

    Failure rules:
    - PermissionDeniedError → step stays IN_PROGRESS, returns (user must grant)
    - Non-zero exit code → step FAILED (never auto-rollback)
    - Exception → step FAILED
    """
    from ..tools.shell_tools import ShellTool
    from ..permissions.manager import PermissionDeniedError
    from ..models.schemas import ExecutionResult, ExecutionStatus

    idx = state.get("current_step_index", 0)
    plan = state.get("execution_plan")

    if not plan or idx >= len(plan.ordered_steps):
        return state

    step = plan.ordered_steps[idx]

    # Skip validation if step already failed (e.g. in coding_agent)
    if step.status == ExecutionStatus.FAILED:
        return state

    if step.commands:
        shell_tool = ShellTool(session_id=state.get("session_id", "default"))
        for cmd in step.commands:
            try:
                shell_result = await shell_tool.execute(cmd)
            except PermissionDeniedError as exc:
                # Shell permission pending — do not fail the step, just return.
                # ShellTool already called request_permission() internally.
                logger.info(f"Shell permission pending for command: {cmd}")
                step.status = ExecutionStatus.WAITING_PERMISSION
                step.result_details = f"Command permission pending: {cmd}"
                return state
            except Exception as exc:
                logger.error(f"Validation command exception for step '{step.title}': {exc}")
                res = ExecutionResult(
                    step_id=step.id, success=False,
                    error=str(exc), output=""
                )
                state["execution_results"].append(res)
                step.status = ExecutionStatus.FAILED
                step.result_details = str(exc)
                return state

            # Non-zero exit code = FAILED. Never fake a passing validation.
            if not shell_result.get("success", False) or shell_result.get("exit_code", 0) != 0:
                error_msg = (
                    f"Command '{cmd}' exited with code {shell_result.get('exit_code', -1)}. "
                    f"stderr: {shell_result.get('stderr', '')[:500]}"
                )
                logger.error(f"Validation FAILED for step '{step.title}': {error_msg}")
                res = ExecutionResult(
                    step_id=step.id, success=False,
                    error=error_msg,
                    output=shell_result.get("stdout", "")[:500],
                )
                state["execution_results"].append(res)
                step.status = ExecutionStatus.FAILED
                step.result_details = error_msg
                return state

            logger.info(f"Validation command succeeded: {cmd}")

    # Increment index only on clean pass
    state["current_step_index"] += 1
    return state

# Edge Routing Conditions
def is_planning_complete(state: AppState) -> str:
    """Routes based on whether requirements gathering is complete."""
    if state.get("requirements_complete"):
        return "blueprint_node"
    return END

def after_checkpoint(state: AppState) -> str:
    return "coding_agent_node"

def has_more_steps(state: AppState) -> str:
    plan = state.get("execution_plan")
    idx = state.get("current_step_index", 0)

    if plan and idx < len(plan.ordered_steps):
        # Stop graph execution if a step failed
        if idx > 0 and plan.ordered_steps[idx - 1].status == "failed":
             return END
        return "coding_agent_node"
    return END

# Build StateGraph
builder = StateGraph(AppState)
builder.add_node("requirement_node", requirement_node)
builder.add_node("blueprint_node", blueprint_node)
builder.add_node("execution_planner_node", execution_planner_node)
builder.add_node("git_checkpoint_node", git_checkpoint_node)
builder.add_node("coding_agent_node", coding_agent_node)
builder.add_node("validation_node", validation_node)

builder.add_edge(START, "requirement_node")
builder.add_conditional_edges("requirement_node", is_planning_complete)
builder.add_edge("blueprint_node", END) # Halts for Blueprint Approval

# These nodes are manually triggered via handle_blueprint_decision and execution_turn
builder.add_edge("execution_planner_node", END) # Halts for Execution Approval
builder.add_edge("git_checkpoint_node", "coding_agent_node")
builder.add_edge("coding_agent_node", "validation_node")
builder.add_conditional_edges("validation_node", has_more_steps)

app_graph = builder.compile()


class AgentSupervisor:
    """
    Supervisor Agent orchestrating the entire lifecycle:
    Requirement Gathering ➔ Blueprint Creation ➔ Contract Graph ➔ Impact Analysis ➔ Permission Gateway ➔ Verification.
    """

    def __init__(self):
        self.active_session_id: str = str(uuid.uuid4())
        self.activity_logs: List[AgentActivityLog] = []
        self._ws_broadcast = None

        # Internal state memory for the planning graph
        from ..models.schemas import RequirementSpec
        self.planning_state: AppState = {
            "session_id": self.active_session_id,
            "messages": [],
            "detected_language": "en",
            "requirements": RequirementSpec(),
            "requirements_complete": False,
            "current_question": None,
            "blueprint": None,
            "approval_status": "NONE",
            "execution_plan": None,
            "execution_approval_status": "NONE",
            "current_step_index": 0,
            "execution_results": [],
            "git_checkpoint_id": None,
            "errors": []
        }

    def set_ws_broadcast(self, broadcast_fn):
        """Sets the callback function to push messages to connected WebSocket clients."""
        self._ws_broadcast = broadcast_fn

    async def log_activity(self, step: str, agent_name: str, status: str, details: str) -> AgentActivityLog:
        """Records and broadcasts an agent activity step."""
        log_entry = AgentActivityLog(
            id=str(uuid.uuid4()),
            step=step,
            agent_name=agent_name,
            status=status,
            details=details,
            timestamp=datetime.utcnow(),
        )
        self.activity_logs.append(log_entry)
        logger.info(f"[{agent_name}] ({status}): {step} - {details}")

        if self._ws_broadcast:
            try:
                await self._ws_broadcast(
                    WSMessage(
                        type=WSMessageType.ACTIVITY_LOG,
                        payload=log_entry.model_dump(mode="json"),
                    )
                )
            except Exception as e:
                logger.error(f"Failed to broadcast activity log: {e}")

        return log_entry

    async def invoke_planning_turn(self, user_message: str, language: str) -> Dict[str, Any]:
        """Runs the LangGraph planning workflow for one interaction turn."""
        from langchain_core.messages import HumanMessage

        # Block if waiting for approval
        if self.planning_state.get("approval_status") == "WAITING_FOR_APPROVAL":
            return {
                "status": "blocked",
                "message": "Waiting for explicit user approval of the Project Blueprint.",
                "state": self.get_session_state()
            }

        self.planning_state["detected_language"] = language
        self.planning_state["messages"].append(HumanMessage(content=user_message))

        # Run graph
        result_state = app_graph.invoke(self.planning_state)
        self.planning_state = result_state  # persist

        response = {
            "status": "planning",
            "requirements_complete": result_state["requirements_complete"],
            "current_question": result_state.get("current_question"),
            "approval_status": result_state.get("approval_status"),
        }

        if result_state.get("blueprint"):
            response["blueprint"] = result_state["blueprint"].model_dump(mode="json")

        return response

    async def handle_blueprint_decision(self, decision: str, modifications: Optional[str] = None) -> Dict[str, Any]:
        """Handles APPROVE, REJECT, EDIT for the generated blueprint."""
        if self.planning_state.get("approval_status") != "WAITING_FOR_APPROVAL":
            raise ValueError("No blueprint is currently pending approval.")

        if decision == "APPROVE":
            self.planning_state["approval_status"] = "APPROVED"
            if self.planning_state["blueprint"]:
                self.planning_state["blueprint"].approved = True
                contract_graph.build_sample_graph()  # Initialize Contract Graph
            await self.log_activity("Blueprint Approved", "Supervisor", "completed", "User approved blueprint.")

            # Call execution_planner_node directly — avoids re-running the full graph from START.
            # The planning graph halts at END after blueprint_node; resuming via ainvoke() would
            # restart requirement gathering. Direct node dispatch is the correct MVP approach.
            logger.info("Blueprint Approved. Dispatching ExecutionPlannerAgent directly.")
            self.planning_state = execution_planner_node(self.planning_state)

        elif decision == "REJECT":
            self.planning_state["approval_status"] = "REJECTED"
            await self.log_activity("Blueprint Rejected", "Supervisor", "completed", "User rejected blueprint.")

        elif decision == "EDIT":
            from langchain_core.messages import HumanMessage
            self.planning_state["approval_status"] = "EDIT"
            self.planning_state["requirements_complete"] = False
            self.planning_state["blueprint"] = None
            if modifications:
                self.planning_state["messages"].append(HumanMessage(content=f"User requested edits: {modifications}"))
            await self.log_activity("Blueprint Edit Requested", "Supervisor", "completed", "User requested changes to requirements.")

        else:
            raise ValueError(f"Invalid decision: {decision}")

        return {"status": "success", "approval_status": self.planning_state["approval_status"]}

    async def handle_execution_decision(self, decision: str) -> Dict[str, Any]:
        """Handles APPROVE, REJECT, EDIT for the generated execution plan."""
        if self.planning_state.get("execution_approval_status") != "WAITING_FOR_EXECUTION_APPROVAL":
            raise ValueError("No execution plan is currently pending approval.")

        if decision == "APPROVE":
            self.planning_state["execution_approval_status"] = "APPROVED"
            await self.log_activity("Execution Plan Approved", "Supervisor", "completed", "User approved execution plan.")

            # STEP 1: Git checkpoint — hard gate before any mutation.
            # git_checkpoint_node sets execution_approval_status=FAILED on error.
            logger.info("Running git checkpoint before any code mutation.")
            state = await git_checkpoint_node(self.planning_state)

            # If checkpoint failed, do not proceed with any execution.
            if state.get("execution_approval_status") == "FAILED" or not state.get("git_checkpoint_id"):
                self.planning_state = state
                logger.error("Execution aborted: git checkpoint failed.")
                await self.log_activity(
                    "Execution Aborted", "Supervisor", "failed",
                    "Git checkpoint creation failed. No files were modified."
                )
                return {
                    "status": "failed",
                    "reason": state.get("errors", ["Git checkpoint failed"])[-1],
                    "execution_approval_status": state.get("execution_approval_status", "FAILED"),
                    "checkpoint_id": None,
                    "suggestion": "RETRY",
                }

            # STEP 2: Execute coding + validation loop step-by-step.
            plan = state.get("execution_plan")
            if plan:
                for step_idx in range(len(plan.ordered_steps)):
                    current_step = plan.ordered_steps[state.get("current_step_index", 0)]
                    await self.log_activity(
                        f"Executing Step {step_idx + 1}/{len(plan.ordered_steps)}: {current_step.title}",
                        "CodingAgent", "running",
                        f"Step ID: {current_step.id}, Risk: {current_step.risk_level}"
                    )

                    state = await coding_agent_node(state)
                    state = await validation_node(state)

                    # Inspect result after this iteration
                    completed_idx = state.get("current_step_index", 0)
                    prev_step = plan.ordered_steps[completed_idx - 1] if completed_idx > 0 else current_step

                    if prev_step.status.value in ("failed", "waiting_permission"):
                        from ..models.schemas import FailureSuggestion
                        suggestion = (
                            FailureSuggestion.ROLLBACK
                            if prev_step.risk_level in ("high", "critical")
                            else FailureSuggestion.FIX
                        )
                        logger.warning(
                            f"Execution halted at step '{prev_step.id}' (status: {prev_step.status.value})."
                        )
                        await self.log_activity(
                            f"Step Failed: {prev_step.title}",
                            "CodingAgent", "failed",
                            f"Reason: {prev_step.result_details or 'unknown'}. "
                            f"Suggestion: {suggestion.value}. Checkpoint: {state.get('git_checkpoint_id')}."
                        )
                        self.planning_state = state
                        return {
                            "status": "failed",
                            "execution_approval_status": state.get("execution_approval_status"),
                            "failure_report": {
                                "failed_step_id": prev_step.id,
                                "reason": prev_step.result_details or "Unknown failure",
                                "checkpoint_id": state.get("git_checkpoint_id"),
                                "suggestion": suggestion.value,
                            }
                        }

                    # All steps consumed — exit the loop cleanly
                    if completed_idx >= len(plan.ordered_steps):
                        break

            self.planning_state = state

            # STEP 3: Post-execution — update Contract Graph + consistency check.
            await self._update_contract_graph_after_execution(state)

            await self.log_activity(
                "Execution Complete", "Supervisor", "completed",
                f"All steps completed. Checkpoint: {state.get('git_checkpoint_id')}."
            )

        elif decision == "REJECT":
            self.planning_state["execution_approval_status"] = "REJECTED"
            await self.log_activity("Execution Plan Rejected", "Supervisor", "completed", "User rejected execution plan.")

        elif decision == "EDIT":
            self.planning_state["execution_approval_status"] = "EDIT"
            self.planning_state["execution_plan"] = None
            await self.log_activity("Execution Plan Edit Requested", "Supervisor", "completed", "User requested changes to execution plan.")
            # Re-run the execution planner directly so the user gets a revised plan
            logger.info("Execution Plan edit requested. Re-dispatching ExecutionPlannerAgent.")
            self.planning_state["execution_approval_status"] = "WAITING_FOR_EXECUTION_APPROVAL"
            self.planning_state = execution_planner_node(self.planning_state)

        else:
            raise ValueError(f"Invalid decision: {decision}")

        return {"status": "success", "execution_approval_status": self.planning_state["execution_approval_status"]}

    async def handle_change_request(self, change_description: str) -> Dict[str, Any]:
        """
        Handles a user change request (e.g. 'Add emergency_contact phone field to student').
        Executes Cross-Layer Impact Analysis, checks for contract violations, and generates permission requests.
        """
        await self.log_activity(
            step="Change Request Received",
            agent_name="ImpactAnalyzer",
            status="running",
            details=f"Evaluating change request: '{change_description}'",
        )

        # Extract target entity
        target_entity = "phone" if "phone" in change_description.lower() else "Student"
        impact_report = contract_graph.analyze_impact(target_entity, {"description": change_description})

        await self.log_activity(
            step="Impact Analysis Completed",
            agent_name="ImpactAnalyzer",
            status="completed",
            details=f"Blast radius: Risk {impact_report.risk_level}. {len(impact_report.affected_frontend)} FE, {len(impact_report.affected_apis)} API, {len(impact_report.affected_backend)} BE, {len(impact_report.affected_database)} DB nodes affected.",
        )

        # Create permission request for proposed code modifications
        perm_req = await permission_manager.request_permission(
            action=PermissionAction.WRITE_FILE,
            target=f"backend/app/models/student.py + frontend/src/components/StudentForm.tsx",
            details={
                "change": change_description,
                "impact_summary": impact_report.summary,
                "risk_level": impact_report.risk_level,
            },
            risk_level=impact_report.risk_level.lower(),
            project_id=self.active_session_id,
        )

        return {
            "impact_report": impact_report.model_dump(mode="json"),
            "permission_request": perm_req.model_dump(mode="json"),
        }

    async def submit_permission_decision(self, response: PermissionResponse) -> Dict[str, Any]:
        """Processes permission decision from user."""
        granted = permission_manager.handle_user_decision(response)

        status = "granted" if granted else "rejected"
        await self.log_activity(
            step="Permission Decision Processed",
            agent_name="PermissionGateway",
            status="completed" if granted else "failed",
            details=f"User decision for request {response.request_id}: {response.decision.value} ({status}).",
        )

        return {
            "request_id": response.request_id,
            "decision": response.decision.value,
            "granted": granted,
        }

    async def _update_contract_graph_after_execution(self, state: AppState) -> None:
        """
        Post-execution Contract Graph update and consistency check.

        Uses existing ContractGraph APIs only:
        - add_node()    -- upserts; marks touched file nodes as MODIFIED
        - find_violations() -- surfaces cross-layer contract drifts
        - get_node()    -- reads existing node before updating status

        This does NOT rebuild the full semantic graph (which would require
        parsing generated code). It marks the layers affected by the execution
        plan as MODIFIED so the violation checker can surface inconsistencies.
        """
        plan = state.get("execution_plan")
        if not plan:
            return

        # Collect all files touched by this execution run
        touched_files: List[str] = []
        for step in plan.ordered_steps:
            touched_files.extend(step.files_to_modify)

        # Derive affected layers from file paths heuristically
        layer_map = {
            "frontend": ContractNodeType.FRONTEND,
            "src/components": ContractNodeType.FRONTEND,
            "src/pages": ContractNodeType.FRONTEND,
            "backend": ContractNodeType.BACKEND,
            "app/models": ContractNodeType.BACKEND,
            "app/services": ContractNodeType.BACKEND,
            "api": ContractNodeType.API,
            "app/api": ContractNodeType.API,
            "routes": ContractNodeType.API,
            "migrations": ContractNodeType.DATABASE,
            "db": ContractNodeType.DATABASE,
            "database": ContractNodeType.DATABASE,
            "test": ContractNodeType.TEST,
            "tests": ContractNodeType.TEST,
        }

        affected_layers_used: set = set()

        for file_path in touched_files:
            fp_lower = file_path.lower().replace("\\", "/")
            node_type = ContractNodeType.BACKEND  # default
            layer_name = "Backend"

            for key, ntype in layer_map.items():
                if key in fp_lower:
                    node_type = ntype
                    layer_name = key.split("/")[-1].capitalize()
                    break

            node_id = f"exec:{file_path}"
            existing = contract_graph.get_node(node_id)

            if existing:
                # Update status only -- preserve all other node data
                updated = existing.model_copy(
                    update={"status": ContractNodeStatus.MODIFIED}
                )
                contract_graph.add_node(updated)
            else:
                # Register new node for this generated file
                new_node = ContractNode(
                    id=node_id,
                    name=file_path,
                    layer=layer_name,
                    node_type=node_type,
                    metadata={"file_path": file_path, "generated_by": "CodingAgent"},
                    status=ContractNodeStatus.MODIFIED,
                )
                contract_graph.add_node(new_node)

            affected_layers_used.add(layer_name)

        # Run cross-layer consistency check using existing API
        violations = contract_graph.find_violations()
        if violations:
            await self.log_activity(
                "Contract Graph Consistency Check",
                "ContractGraph",
                "failed",
                f"{len(violations)} consistency violation(s) found after execution: "
                + "; ".join(v.description[:80] for v in violations[:3]),
            )
        else:
            await self.log_activity(
                "Contract Graph Consistency Check",
                "ContractGraph",
                "completed",
                f"No violations detected. Affected layers: {sorted(affected_layers_used)}.",
            )

        # Surface the expected-layer consistency check for the demo scenario.
        # After an execution touching a Student model, verify all 5 expected
        # layers (Frontend, Backend, API, Database, Tests) have nodes in the graph.
        if any("student" in f.lower() for f in touched_files):
            expected_layers = {"Frontend", "Backend", "Api", "Database", "Test"}
            present_layers = {node.layer for node in contract_graph.export_graph().nodes}
            missing_layers = expected_layers - present_layers
            if missing_layers:
                await self.log_activity(
                    "Cross-Layer Consistency Warning",
                    "ContractGraph",
                    "failed",
                    f"Student change detected but these layers have no contract nodes: "
                    f"{sorted(missing_layers)}. "
                    "Update may be incomplete across the full stack.",
                )

    def get_session_state(self) -> Dict[str, Any]:
        """Returns snapshot of current supervisor state, including execution plan progress."""
        plan: Optional[ExecutionPlan] = self.planning_state.get("execution_plan")
        results: List[ExecutionResult] = self.planning_state.get("execution_results", [])
        return {
            "session_id": self.planning_state["session_id"],
            "requirements_complete": self.planning_state["requirements_complete"],
            "current_question": self.planning_state["current_question"],
            "has_blueprint": self.planning_state["blueprint"] is not None,
            "blueprint": self.planning_state["blueprint"].model_dump(mode="json") if self.planning_state["blueprint"] else None,
            "approval_status": self.planning_state["approval_status"],
            # Execution plan fields
            "has_execution_plan": plan is not None,
            "execution_plan": plan.model_dump(mode="json") if plan else None,
            "execution_approval_status": self.planning_state.get("execution_approval_status", "NONE"),
            "current_step_index": self.planning_state.get("current_step_index", 0),
            "execution_results": [r.model_dump(mode="json") for r in results],
            "checkpoint_id": self.planning_state.get("git_checkpoint_id"),
            # Infrastructure
            "graph": contract_graph.export_graph().model_dump(mode="json"),
            "pending_permissions": [p.model_dump(mode="json") for p in permission_manager.get_pending_requests().values()],
            "hardware": local_llm.get_hardware_profile(),
        }


agent_supervisor = AgentSupervisor()
