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
    """Takes a git checkpoint before modifying code."""
    from ..tools.git_tools import GitTool
    git_tool = GitTool()
    cp = git_tool.create_checkpoint(name=f"auto_before_exec_{state['session_id'][:6]}", description="Automatic checkpoint before agent execution.")
    state["git_checkpoint_id"] = cp.id
    return state

async def coding_agent_node(state: AppState) -> AppState:
    """Executes one step from the execution plan."""
    return await coding_agent.process(state)

async def validation_node(state: AppState) -> AppState:
    """Validates the execution step."""
    from ..tools.shell_tools import ShellTool
    
    idx = state.get("current_step_index", 0)
    plan = state.get("execution_plan")
    
    if not plan or idx >= len(plan.ordered_steps):
        return state
        
    step = plan.ordered_steps[idx]
    
    # Check if there are commands to validate
    if step.commands:
        shell_tool = ShellTool()
        try:
            for cmd in step.commands:
                # We assume permissions are granted at the project level, otherwise this would fail
                await shell_tool.execute(cmd)
        except Exception as e:
            logger.error(f"Validation failed for step {step.title}: {e}")
            from ..models.schemas import ExecutionResult, ExecutionStatus
            res = ExecutionResult(step_id=step.id, success=False, error=str(e))
            state["execution_results"].append(res)
            step.status = ExecutionStatus.FAILED
            step.result_details = str(e)
            return state

    # Increment index if successful
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
            
            # Execute the plan node-by-node directly.
            # git_checkpoint_node → coding_agent_node → validation_node (loops via has_more_steps).
            # We call these directly rather than re-invoking app_graph.ainvoke() from START,
            # which would incorrectly restart requirement gathering.
            logger.info("Execution Plan Approved. Running git checkpoint + coding + validation pipeline.")
            state = await git_checkpoint_node(self.planning_state)
            
            plan = state.get("execution_plan")
            if plan:
                for _ in range(len(plan.ordered_steps)):
                    state = await coding_agent_node(state)
                    state = await validation_node(state)
                    # Stop early if a step failed
                    idx = state.get("current_step_index", 0)
                    if idx > 0 and plan.ordered_steps[idx - 1].status == "failed":
                        logger.warning(f"Execution halted early at step index {idx} due to failure.")
                        break
            
            self.planning_state = state
            
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
