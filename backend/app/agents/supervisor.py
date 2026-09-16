import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from ..contract_graph.graph import contract_graph
from ..models.schemas import (
    AgentActivityLog,
    PermissionAction,
    PermissionResponse,
    ProjectBlueprint,
    RequirementQuestion,
    WSMessage,
    WSMessageType,
)
from ..permissions.manager import permission_manager
from .base import local_llm
from .requirement_agent import requirement_agent

logger = logging.getLogger("sugio_labs.agents.supervisor")


class ChatState(TypedDict):
    messages: List[Dict[str, str]]
    language: str


def call_local_model(state: ChatState):
    """LangGraph chat node. Falls back locally if Ollama cannot answer."""
    prompt = state["messages"][-1]["content"] if state["messages"] else ""
    language = state.get("language", "en")
    system_prompt = "You are Sugio Labs, a local software architecture and development agent."

    if language == "ta":
        system_prompt += " Respond in Tamil where practical."
    elif language == "tanglish":
        system_prompt += " Respond in clear Tanglish."

    try:
        chat_model = local_llm.get_chat_model()
        response = chat_model.invoke([
            ("system", system_prompt),
            ("user", prompt),
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as exc:
        logger.info("Chat model unavailable; using local fallback: %s", exc)
        content = local_llm.heuristic_response(prompt, language)

    return {"messages": [{"role": "assistant", "content": content}]}


builder = StateGraph(ChatState)
builder.add_node("agent", call_local_model)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)
chat_graph = builder.compile()


class AgentSupervisor:
    """Orchestrates planning, contract mapping, impact analysis and approvals."""

    def __init__(self):
        self.active_session_id: str = str(uuid.uuid4())
        self.current_question_index: int = 0
        self.collected_answers: Dict[str, str] = {}
        self.current_blueprint: Optional[ProjectBlueprint] = None
        self.activity_logs: List[AgentActivityLog] = []
        self._ws_broadcast = None

    def set_ws_broadcast(self, broadcast_fn):
        self._ws_broadcast = broadcast_fn

    async def _broadcast(self, message: WSMessage) -> None:
        if not self._ws_broadcast:
            return
        try:
            await self._ws_broadcast(message)
        except Exception as exc:
            logger.debug("WebSocket broadcast failed: %s", exc)

    async def log_activity(self, step: str, agent_name: str, status: str, details: str) -> AgentActivityLog:
        log_entry = AgentActivityLog(
            id=str(uuid.uuid4()),
            step=step,
            agent_name=agent_name,
            status=status,
            details=details,
            timestamp=datetime.utcnow(),
        )
        self.activity_logs.append(log_entry)
        self.activity_logs = self.activity_logs[-100:]
        logger.info("[%s] (%s): %s", agent_name, status, step)

        await self._broadcast(
            WSMessage(
                type=WSMessageType.ACTIVITY_LOG,
                payload=log_entry.model_dump(mode="json"),
            )
        )
        return log_entry

    async def start_interview(self) -> RequirementQuestion:
        """Starts planning. An approved blueprint is kept until the new plan is complete."""
        self.current_question_index = 0
        self.collected_answers.clear()
        if not (self.current_blueprint and self.current_blueprint.approved):
            self.current_blueprint = None

        await self.log_activity(
            step="Planning started",
            agent_name="RequirementAgent",
            status="running",
            details="Collecting the decisions needed to generate a project blueprint.",
        )

        question = requirement_agent.get_question(0)
        if question is None:
            raise RuntimeError("Requirement interview has no configured questions.")
        return question

    async def answer_question(self, question_id: str, answer: str) -> Dict[str, Any]:
        expected = requirement_agent.get_question(self.current_question_index)
        if expected and expected.id != question_id:
            logger.debug("Received answer for %s while current question is %s", question_id, expected.id)

        self.collected_answers[question_id] = answer
        self.current_question_index += 1

        await self.log_activity(
            step=f"Captured {question_id}",
            agent_name="RequirementAgent",
            status="completed",
            details=f"Decision recorded: {answer}",
        )

        next_question = requirement_agent.get_question(self.current_question_index)
        if next_question:
            return {"status": "next_question", "question": next_question.model_dump(mode="json")}

        await self.log_activity(
            step="Generating blueprint",
            agent_name="ArchitectureAgent",
            status="running",
            details="Synthesizing product, stack, modules, routes, persistence and verification strategy.",
        )

        blueprint = requirement_agent.generate_blueprint_from_answers(self.collected_answers)
        self.current_blueprint = blueprint

        await self.log_activity(
            step="Blueprint ready",
            agent_name="ArchitectureAgent",
            status="completed",
            details=f"{blueprint.project_name} is ready for architecture approval.",
        )
        await self._broadcast(
            WSMessage(type=WSMessageType.BLUEPRINT_READY, payload=blueprint.model_dump(mode="json"))
        )

        return {"status": "blueprint_ready", "blueprint": blueprint.model_dump(mode="json")}

    async def approve_blueprint(self) -> Dict[str, Any]:
        if not self.current_blueprint:
            raise ValueError("No active blueprint to approve.")

        self.current_blueprint.approved = True
        contract_graph.build_from_blueprint(self.current_blueprint)
        graph_data = contract_graph.export_graph()

        await self.log_activity(
            step="Blueprint approved",
            agent_name="Supervisor",
            status="completed",
            details="Architecture locked and project-specific Contract Graph generated.",
        )
        await self.log_activity(
            step="Contracts synchronized",
            agent_name="ContractGraphEngine",
            status="completed",
            details=f"Mapped {len(graph_data.nodes)} nodes and {len(graph_data.edges)} dependencies across the stack.",
        )
        await self._broadcast(
            WSMessage(type=WSMessageType.GRAPH_UPDATE, payload=graph_data.model_dump(mode="json"))
        )

        return {
            "status": "success",
            "message": "Blueprint approved and project Contract Graph synchronized.",
            "blueprint": self.current_blueprint.model_dump(mode="json"),
            "graph": graph_data.model_dump(mode="json"),
        }

    async def handle_change_request(self, change_description: str, target_entity: Optional[str] = None) -> Dict[str, Any]:
        target = (target_entity or "").strip()
        if not target:
            lowered = change_description.lower()
            if "phone" in lowered:
                target = "phone"
            elif "email" in lowered:
                target = "email"
            else:
                target = "Student"

        await self.log_activity(
            step="Analyzing change",
            agent_name="ImpactAnalyzer",
            status="running",
            details=f"Tracing contract dependencies for '{target}'.",
        )

        impact_report = contract_graph.analyze_impact(target, {"description": change_description})
        affected = (
            impact_report.affected_frontend
            + impact_report.affected_apis
            + impact_report.affected_backend
            + impact_report.affected_database
            + impact_report.affected_tests
        )

        await self.log_activity(
            step="Impact mapped",
            agent_name="ImpactAnalyzer",
            status="completed",
            details=f"{len(affected)} affected nodes. Risk level: {impact_report.risk_level}.",
        )

        target_description = ", ".join(affected[:4]) if affected else target
        permission_request = await permission_manager.request_permission(
            action=PermissionAction.WRITE_FILE,
            target=target_description,
            details={
                "target_entity": target,
                "change": change_description,
                "impact_summary": impact_report.summary,
                "risk_level": impact_report.risk_level,
                "affected_nodes": affected,
            },
            risk_level=impact_report.risk_level.lower(),
            project_id=self.active_session_id,
        )

        return {
            "impact_report": impact_report.model_dump(mode="json"),
            "permission_request": permission_request.model_dump(mode="json"),
        }

    async def submit_permission_decision(self, response: PermissionResponse) -> Dict[str, Any]:
        granted = permission_manager.handle_user_decision(response)
        await self.log_activity(
            step="Permission decided",
            agent_name="PermissionGateway",
            status="completed" if granted else "failed",
            details=f"Decision for {response.request_id}: {response.decision.value}.",
        )
        return {
            "request_id": response.request_id,
            "decision": response.decision.value,
            "granted": granted,
        }

    def get_session_state(self) -> Dict[str, Any]:
        return {
            "session_id": self.active_session_id,
            "question_index": self.current_question_index,
            "answers": self.collected_answers,
            "has_blueprint": self.current_blueprint is not None,
            "blueprint": self.current_blueprint.model_dump(mode="json") if self.current_blueprint else None,
            "graph": contract_graph.export_graph().model_dump(mode="json"),
            "pending_permissions": [
                permission.model_dump(mode="json")
                for permission in permission_manager.get_pending_requests().values()
            ],
            "hardware": local_llm.get_hardware_profile(),
        }


agent_supervisor = AgentSupervisor()
