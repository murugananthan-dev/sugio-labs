import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..agents.base import local_llm
from ..agents.requirement_agent import requirement_agent
from ..agents.supervisor import agent_supervisor, chat_graph
from ..contract_graph.graph import contract_graph
from ..models.schemas import PermissionAction, PermissionResponse
from ..permissions.manager import PermissionDeniedError, permission_manager
from ..tools.git_tools import GitTool
from ..tools.mcp_client import mcp_gateway
from ..tools.shell_tools import ShellTool

logger = logging.getLogger("sugio_labs.api.routes")
router = APIRouter(prefix="/api/v1")
git_tool = GitTool()
shell_tool = ShellTool()


@router.get("/health")
async def health_check():
    ollama_ok = await local_llm.is_ollama_online()
    models = await local_llm.list_local_models() if ollama_ok else []
    return {
        "status": "healthy",
        "service": "Sugio Labs Backend",
        "version": "0.2.0",
        "ollama_online": ollama_ok,
        "local_models_detected": models,
        "assistant_mode": "ollama" if ollama_ok else "local_fallback",
    }


@router.get("/system/hardware")
async def get_hardware_info():
    return local_llm.get_hardware_profile()


@router.get("/interview/questions")
async def list_interview_questions():
    return requirement_agent.get_all_questions()


@router.post("/interview/start")
async def start_interview():
    first_question = await agent_supervisor.start_interview()
    return {"question": first_question}


class AnswerPayload(BaseModel):
    question_id: str
    answer: str


@router.post("/interview/answer")
async def submit_answer(payload: AnswerPayload):
    return await agent_supervisor.answer_question(payload.question_id, payload.answer)


@router.post("/blueprint/approve")
async def approve_blueprint():
    try:
        return await agent_supervisor.approve_blueprint()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/contract-graph")
async def get_contract_graph():
    return contract_graph.export_graph()


@router.post("/contract-graph/sample")
async def reset_sample_graph():
    contract_graph.build_sample_graph()
    return {"status": "success", "graph": contract_graph.export_graph()}


class ImpactAnalysisRequest(BaseModel):
    target_entity: str = Field(..., description="Target node, table, field, route, or component")
    change_description: str = Field(..., description="Human-language change request")


@router.post("/impact-analysis")
async def perform_impact_analysis(payload: ImpactAnalysisRequest):
    return await agent_supervisor.handle_change_request(
        change_description=payload.change_description,
        target_entity=payload.target_entity,
    )


@router.get("/permissions/pending")
async def get_pending_permissions():
    return list(permission_manager.get_pending_requests().values())


@router.post("/permissions/decision")
async def submit_permission_decision(decision: PermissionResponse):
    return await agent_supervisor.submit_permission_decision(decision)


class CheckpointPayload(BaseModel):
    name: str
    description: str = ""


@router.get("/git/checkpoints")
async def list_checkpoints():
    return git_tool.list_checkpoints()


@router.post("/git/checkpoint")
async def create_checkpoint(payload: CheckpointPayload):
    checkpoint = git_tool.create_checkpoint(payload.name, payload.description)
    return {"status": "created", "checkpoint": checkpoint.to_dict()}


class RollbackPayload(BaseModel):
    checkpoint_id: str


@router.post("/git/rollback")
async def rollback_to_checkpoint(payload: RollbackPayload):
    target = f"rollback:{payload.checkpoint_id}"
    if not permission_manager.is_action_permitted(
        PermissionAction.GIT_OPERATION,
        target,
        git_tool.session_id,
    ):
        await permission_manager.request_permission(
            action=PermissionAction.GIT_OPERATION,
            target=target,
            details={
                "checkpoint_id": payload.checkpoint_id,
                "warning": "Rollback can discard files created after this checkpoint.",
            },
            risk_level="high",
            project_id=git_tool.session_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Permission required for rollback. Approve the request, then run Restore again.",
        )

    try:
        git_tool.rollback_to_checkpoint(payload.checkpoint_id)
        return {"status": "success", "rolled_back_to": payload.checkpoint_id}
    except (ValueError, RuntimeError, PermissionDeniedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/git/diff")
async def get_git_diff():
    return {"diff": git_tool.get_diff()}


class ShellPayload(BaseModel):
    command: str
    timeout_seconds: int = 60


@router.post("/shell/execute")
async def run_shell_command(payload: ShellPayload):
    try:
        return await shell_tool.execute(payload.command, payload.timeout_seconds)
    except Exception as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/mcp/tools")
async def list_mcp_tools():
    return mcp_gateway.get_tool_definitions()


class MCPExecutePayload(BaseModel):
    tool_name: str
    args: Dict[str, Any]


@router.post("/mcp/execute")
async def execute_mcp_tool(payload: MCPExecutePayload):
    try:
        return await mcp_gateway.execute_tool(payload.tool_name, payload.args)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/session/state")
async def get_session_state():
    state = agent_supervisor.get_session_state()
    state["activity_logs"] = agent_supervisor.activity_logs
    state["checkpoints"] = git_tool.list_checkpoints()
    return state


class ChatPayload(BaseModel):
    message: str
    language: str = Field(default="en", description="en, ta, tanglish")


@router.post("/chat")
async def chat_with_agent(payload: ChatPayload):
    state = {
        "messages": [{"role": "user", "content": payload.message}],
        "language": payload.language,
    }
    result_state = chat_graph.invoke(state)
    response = result_state["messages"][-1]["content"] if result_state["messages"] else "No response generated."
    return {"reply": response, "language": payload.language}
