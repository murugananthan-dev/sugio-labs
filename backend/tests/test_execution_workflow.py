import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.agents.supervisor import agent_supervisor
from app.models.schemas import RequirementSpec, ProjectBlueprint, ExecutionPlan, ExecutionStep, ExecutionStatus
from app.permissions.manager import permission_manager, PermissionAction

client = TestClient(app)

@pytest.fixture
def mock_planner():
    with patch("app.agents.supervisor.execution_planner.process") as mock_ep, \
         patch("app.api.routes.agent_supervisor.log_activity"):
         
        # Reset state
        agent_supervisor.planning_state = {
            "session_id": "test-session",
            "messages": [],
            "detected_language": "en",
            "requirements": RequirementSpec(),
            "requirements_complete": True,
            "current_question": None,
            "blueprint": ProjectBlueprint(
                project_name="TestApp", objective="Test", user_roles=[], features=[],
                functional_requirements=[], non_functional_requirements=[], selected_stack={},
                architecture_summary="", frontend_modules=[], backend_modules=[],
                api_endpoints=[], db_schema=[], folder_structure=[], testing_strategy="",
                development_steps=[], risks=[]
            ),
            "approval_status": "WAITING_FOR_APPROVAL",
            "execution_plan": None,
            "execution_approval_status": "NONE",
            "current_step_index": 0,
            "execution_results": [],
            "git_checkpoint_id": None,
            "errors": []
        }
         
        yield mock_ep

def test_blueprint_approval_generates_execution_plan(mock_planner):
    def ep_side_effect(state):
        state["execution_plan"] = ExecutionPlan(
            blueprint_context="Test",
            ordered_steps=[],
            validation_strategy="None"
        )
        state["execution_approval_status"] = "WAITING_FOR_EXECUTION_APPROVAL"
        return state
    mock_planner.side_effect = ep_side_effect
    
    with patch("app.agents.supervisor.contract_graph.build_sample_graph"):
        response = client.post("/api/v1/blueprint/decision", json={"decision": "APPROVE"})
        
        assert response.status_code == 200
        assert agent_supervisor.planning_state["approval_status"] == "APPROVED"
        assert agent_supervisor.planning_state["execution_approval_status"] == "WAITING_FOR_EXECUTION_APPROVAL"
        assert mock_planner.called

def test_execution_approval_gate_blocks(mock_planner):
    # Set to WAITING_FOR_EXECUTION_APPROVAL
    agent_supervisor.planning_state["execution_approval_status"] = "WAITING_FOR_EXECUTION_APPROVAL"
    
    response = client.post("/api/v1/execution/decision", json={"decision": "REJECT"})
    assert response.status_code == 200
    assert agent_supervisor.planning_state["execution_approval_status"] == "REJECTED"

@pytest.mark.asyncio
async def test_execution_approve_triggers_checkpoint_and_coding():
    agent_supervisor.planning_state["execution_approval_status"] = "WAITING_FOR_EXECUTION_APPROVAL"
    
    step1 = ExecutionStep(
        id="step1", title="Setup DB", description="db",
        files_to_modify=["db.py"], commands=["pytest db.py"],
    )
    
    agent_supervisor.planning_state["execution_plan"] = ExecutionPlan(
        blueprint_context="Test",
        ordered_steps=[step1],
        validation_strategy="None"
    )
    
    # Pre-grant permission for testing
    permission_manager._project_permissions[agent_supervisor.planning_state["session_id"]] = {f"{PermissionAction.WRITE_FILE.value}:db.py"}
    
    with patch("app.agents.supervisor.AgentSupervisor.log_activity"), \
         patch("app.tools.git_tools.GitTool.create_checkpoint") as mock_git, \
         patch("app.agents.coding_agent.local_llm.is_ollama_online", new=AsyncMock(return_value=True)), \
         patch("app.agents.coding_agent.local_llm.generate", new=AsyncMock(return_value="[]")), \
         patch("app.tools.shell_tools.ShellTool.execute", new_callable=AsyncMock) as mock_shell:
         
        mock_git.return_value = MagicMock(id="checkpoint-123")
        mock_shell.return_value = {"exit_code": 0, "stdout": "ok", "stderr": "", "success": True}
        
        response = client.post("/api/v1/execution/decision", json={"decision": "APPROVE"})
        
        assert response.status_code == 200
        assert agent_supervisor.planning_state["execution_approval_status"] == "APPROVED"
        assert agent_supervisor.planning_state["git_checkpoint_id"] == "checkpoint-123"
        assert agent_supervisor.planning_state["current_step_index"] == 1
        assert len(agent_supervisor.planning_state["execution_results"]) == 1
        assert agent_supervisor.planning_state["execution_results"][0].success is True
        assert mock_git.called
        assert mock_shell.called
