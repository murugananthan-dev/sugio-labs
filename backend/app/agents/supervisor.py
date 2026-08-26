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
)
from .requirement_agent import requirement_agent
from .base import local_llm
from ..contract_graph.graph import contract_graph
from ..permissions.manager import permission_manager

logger = logging.getLogger("sugio_labs.agents.supervisor")


class AgentSupervisor:
    """
    Supervisor Agent orchestrating the entire lifecycle:
    Requirement Gathering ➔ Blueprint Creation ➔ Contract Graph ➔ Impact Analysis ➔ Permission Gateway ➔ Verification.
    """

    def __init__(self):
        self.active_session_id: str = str(uuid.uuid4())
        self.current_question_index: int = 0
        self.collected_answers: Dict[str, str] = {}
        self.current_blueprint: Optional[ProjectBlueprint] = None
        self.activity_logs: List[AgentActivityLog] = []
        self._ws_broadcast = None

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

    async def start_interview(self) -> RequirementQuestion:
        """Starts a new requirement interview from question 0."""
        self.current_question_index = 0
        self.collected_answers.clear()
        self.current_blueprint = None

        await self.log_activity(
            step="Interview Initialized",
            agent_name="RequirementAgent",
            status="running",
            details="Starting requirement gathering session with intelligent recommendations.",
        )

        q = requirement_agent.get_question(0)
        return q

    async def answer_question(self, question_id: str, answer: str) -> Dict[str, Any]:
        """
        Receives an answer for the current question, records it, and returns the next question or the final blueprint.
        """
        self.collected_answers[question_id] = answer
        self.current_question_index += 1

        await self.log_activity(
            step=f"Answer Recorded for {question_id}",
            agent_name="RequirementAgent",
            status="completed",
            details=f"User selected: '{answer}'",
        )

        next_q = requirement_agent.get_question(self.current_question_index)
        if next_q:
            return {"status": "next_question", "question": next_q.model_dump(mode="json")}

        # All questions answered, generate blueprint
        await self.log_activity(
            step="Synthesizing Blueprint",
            agent_name="ArchitectureAgent",
            status="running",
            details="Creating comprehensive Project Blueprint from interview responses.",
        )

        blueprint = requirement_agent.generate_blueprint_from_answers(self.collected_answers)
        self.current_blueprint = blueprint

        await self.log_activity(
            step="Blueprint Generated",
            agent_name="ArchitectureAgent",
            status="completed",
            details=f"Blueprint for '{blueprint.project_name}' created. Awaiting user approval.",
        )

        return {"status": "blueprint_ready", "blueprint": blueprint.model_dump(mode="json")}

    async def approve_blueprint(self) -> Dict[str, Any]:
        """Marks current blueprint as approved and populates the Contract Graph."""
        if not self.current_blueprint:
            raise ValueError("No active blueprint to approve.")

        self.current_blueprint.approved = True

        await self.log_activity(
            step="Blueprint Approved",
            agent_name="Supervisor",
            status="completed",
            details="User approved the architecture blueprint. Building Contract Graph nodes.",
        )

        # Build contract graph for the project
        contract_graph.build_sample_graph()

        await self.log_activity(
            step="Contract Graph Constructed",
            agent_name="ContractGraphEngine",
            status="completed",
            details="Cross-layer Contract Graph initialized with synchronized Frontend, API, Backend, DB, and Test nodes.",
        )

        return {
            "status": "success",
            "message": "Blueprint approved and Contract Graph synchronized.",
            "blueprint": self.current_blueprint.model_dump(mode="json"),
            "graph": contract_graph.export_graph().model_dump(mode="json"),
        }

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
        """Returns snapshot of current supervisor state."""
        return {
            "session_id": self.active_session_id,
            "question_index": self.current_question_index,
            "answers": self.collected_answers,
            "has_blueprint": self.current_blueprint is not None,
            "blueprint": self.current_blueprint.model_dump(mode="json") if self.current_blueprint else None,
            "graph": contract_graph.export_graph().model_dump(mode="json"),
            "pending_permissions": [p.model_dump(mode="json") for p in permission_manager.get_pending_requests().values()],
            "hardware": local_llm.get_hardware_profile(),
        }


agent_supervisor = AgentSupervisor()
