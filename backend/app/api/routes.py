import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..models.schemas import (
    PermissionRequest,
    PermissionResponse,
    ContractGraphData,
    ContractNode,
    ContractEdge,
    ImpactReport,
    ProjectBlueprint,
    RequirementQuestion,
)
from ..agents.supervisor import agent_supervisor
from ..agents.base import local_llm
from ..agents.requirement_agent import requirement_agent
from ..contract_graph.graph import contract_graph
from ..permissions.manager import permission_manager
from ..tools.git_tools import GitTool
from ..tools.shell_tools import ShellTool
from ..tools.mcp_client import mcp_gateway

logger = logging.getLogger("sugio_labs.api.routes")
router = APIRouter(prefix="/api/v1")
git_tool = GitTool()
shell_tool = ShellTool()


# ============================================================================
# 1. HEALTH & SYSTEM PROFILE
# ============================================================================

@router.get("/health")
async def health_check():
    """Returns backend service health status and Ollama availability."""
    ollama_ok = await local_llm.is_ollama_online()
    models = await local_llm.list_local_models() if ollama_ok else []
    return {
        "status": "healthy",
        "service": "Sugio Labs Backend",
        "version": "0.1.0",
        "ollama_online": ollama_ok,
        "local_models_detected": models,
    }

@router.get("/system/hardware")
async def get_hardware_info():
    """Returns detected hardware profile (RAM, CPU, GPU recommendation)."""
    return local_llm.get_hardware_profile()


# ============================================================================
# 2. REQUIREMENT INTERVIEW & BLUEPRINT
# ============================================================================

@router.get("/interview/questions")
async def list_interview_questions():
    """Lists all preset interview questions."""
    return requirement_agent.get_all_questions()

class PlanningChatPayload(BaseModel):
    message: str
    language: str = Field(default="en", description="en, ta, tanglish")

@router.post("/chat/planning")
async def chat_planning(payload: PlanningChatPayload):
    """
    Consolidated endpoint for requirement interview and generic chat during the planning phase.
    Routes user messages through the LangGraph planning workflow.
    """
    res = await agent_supervisor.invoke_planning_turn(payload.message, payload.language)
    return res

class BlueprintDecisionPayload(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT, EDIT")
    modifications: Optional[str] = Field(default=None, description="Requested edits if decision is EDIT")

@router.post("/blueprint/decision")
async def handle_blueprint_decision(payload: BlueprintDecisionPayload):
    """Handles explicit user approval of the generated Project Blueprint."""
    try:
        res = await agent_supervisor.handle_blueprint_decision(payload.decision, payload.modifications)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class ExecutionDecisionPayload(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT, EDIT")

@router.post("/execution/decision")
async def handle_execution_decision(payload: ExecutionDecisionPayload):
    """Handles explicit user approval of the generated Execution Plan."""
    try:
        res = await agent_supervisor.handle_execution_decision(payload.decision)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 3. CONTRACT GRAPH & IMPACT ANALYSIS
# ============================================================================

@router.get("/contract-graph")
async def get_contract_graph():
    """Returns current cross-layer Contract Graph data."""
    return contract_graph.export_graph()

@router.post("/contract-graph/sample")
async def reset_sample_graph():
    """Resets the Contract Graph to the reference Student Management System graph."""
    contract_graph.build_sample_graph()
    return {"status": "success", "graph": contract_graph.export_graph()}

class ImpactAnalysisRequest(BaseModel):
    target_entity: str = Field(..., description="Target node, table, field, or component name")
    change_description: str = Field(..., description="Human language description of the requested modification")

@router.post("/impact-analysis")
async def perform_impact_analysis(payload: ImpactAnalysisRequest):
    """Calculates blast radius and contract violations for a requested change."""
    res = await agent_supervisor.handle_change_request(payload.change_description)
    return res


# ============================================================================
# 4. HUMAN-IN-THE-LOOP PERMISSION GATEWAY
# ============================================================================

@router.get("/permissions/pending")
async def get_pending_permissions():
    """Retrieves all pending permission requests requiring user approval."""
    pending = permission_manager.get_pending_requests()
    return list(pending.values())

@router.post("/permissions/decision")
async def submit_permission_decision(decision: PermissionResponse):
    """Submits user decision (ALLOW_ONCE, ALLOW_FOR_PROJECT, REJECT)."""
    res = await agent_supervisor.submit_permission_decision(decision)
    return res


# ============================================================================
# 5. GIT SAFETY CHECKPOINTS & ROLLBACK
# ============================================================================

class CheckpointPayload(BaseModel):
    name: str
    description: str = ""

@router.get("/git/checkpoints")
async def list_checkpoints():
    """Lists all recorded Git checkpoints."""
    return git_tool.list_checkpoints()

@router.post("/git/checkpoint")
async def create_checkpoint(payload: CheckpointPayload):
    """Creates a safety snapshot checkpoint before modifying files."""
    cp = git_tool.create_checkpoint(payload.name, payload.description)
    return {"status": "created", "checkpoint": cp.to_dict()}

class RollbackPayload(BaseModel):
    checkpoint_id: str

@router.post("/git/rollback")
async def rollback_to_checkpoint(payload: RollbackPayload):
    """Rolls back the workspace sandbox to a specific checkpoint."""
    try:
        ok = git_tool.rollback_to_checkpoint(payload.checkpoint_id)
        return {"status": "success", "rolled_back_to": payload.checkpoint_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/git/diff")
async def get_git_diff():
    """Returns working directory diff."""
    return {"diff": git_tool.get_diff()}


# ============================================================================
# 6. SANDBOXED SHELL & MCP TOOLS
# ============================================================================

class ShellPayload(BaseModel):
    command: str
    timeout_seconds: int = 60

@router.post("/shell/execute")
async def run_shell_command(payload: ShellPayload):
    """Executes a command inside the project sandbox with permission checks."""
    try:
        res = await shell_tool.execute(payload.command, payload.timeout_seconds)
        return res
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/mcp/tools")
async def list_mcp_tools():
    """Returns available MCP tool definitions."""
    return mcp_gateway.get_tool_definitions()

class MCPExecutePayload(BaseModel):
    tool_name: str
    args: Dict[str, Any]

@router.post("/mcp/execute")
async def execute_mcp_tool(payload: MCPExecutePayload):
    """Executes an MCP tool with permission gating."""
    try:
        res = await mcp_gateway.execute_tool(payload.tool_name, payload.args)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# 7. SUPERVISOR SESSION & CHAT
# ============================================================================

@router.get("/session/state")
async def get_session_state():
    """Returns full supervisor session state, activity timeline, and active configs."""
    state = agent_supervisor.get_session_state()
    state["activity_logs"] = agent_supervisor.activity_logs
    state["checkpoints"] = git_tool.list_checkpoints()
    return state

# Deprecated original chat endpoint (now mapped to /chat/planning)
@router.post("/chat")
async def legacy_chat(payload: PlanningChatPayload):
    return await chat_planning(payload)
