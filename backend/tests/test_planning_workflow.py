import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.agents.supervisor import agent_supervisor
from app.models.schemas import RequirementSpec, ProjectBlueprint

client = TestClient(app)

@pytest.fixture
def mock_agents():
    with patch("app.agents.supervisor.requirement_agent.process") as mock_req, \
         patch("app.agents.supervisor.blueprint_agent.process") as mock_bp, \
         patch("app.api.routes.agent_supervisor.log_activity"):
         
        # Make the supervisor reset its state for each test
        agent_supervisor.planning_state = {
            "session_id": "test-session",
            "messages": [],
            "detected_language": "en",
            "requirements": RequirementSpec(),
            "requirements_complete": False,
            "current_question": None,
            "blueprint": None,
            "approval_status": "NONE",
            "errors": []
        }
         
        yield mock_req, mock_bp

def test_requirement_agent_asks_question(mock_agents):
    mock_req, mock_bp = mock_agents
    
    def req_side_effect(state):
        state["requirements_complete"] = False
        state["current_question"] = "What database?"
        return state
    mock_req.side_effect = req_side_effect
    
    response = client.post("/api/v1/chat/planning", json={"message": "I need an app", "language": "en"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "planning"
    assert data["requirements_complete"] is False
    assert data["current_question"] == "What database?"
    assert not mock_bp.called

def test_requirement_completion_routing(mock_agents):
    mock_req, mock_bp = mock_agents
    
    def req_side_effect(state):
        state["requirements_complete"] = True
        return state
    mock_req.side_effect = req_side_effect
    
    def bp_side_effect(state):
        bp = ProjectBlueprint(
            project_name="TestApp", objective="Test", user_roles=[], features=[],
            functional_requirements=[], non_functional_requirements=[], selected_stack={},
            architecture_summary="", frontend_modules=[], backend_modules=[],
            api_endpoints=[], db_schema=[], folder_structure=[], testing_strategy="",
            development_steps=[], risks=[]
        )
        state["blueprint"] = bp
        state["approval_status"] = "WAITING_FOR_APPROVAL"
        return state
    mock_bp.side_effect = bp_side_effect
    
    response = client.post("/api/v1/chat/planning", json={"message": "Database is Postgres", "language": "en"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["requirements_complete"] is True
    assert data["approval_status"] == "WAITING_FOR_APPROVAL"
    assert "blueprint" in data
    assert data["blueprint"]["project_name"] == "TestApp"
    assert mock_bp.called

def test_approval_gate_blocks_execution(mock_agents):
    mock_req, mock_bp = mock_agents
    
    # Pre-set state to WAITING_FOR_APPROVAL
    agent_supervisor.planning_state["approval_status"] = "WAITING_FOR_APPROVAL"
    
    response = client.post("/api/v1/chat/planning", json={"message": "Do more stuff", "language": "en"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert "Waiting for explicit user approval" in data["message"]
    
def test_approve_behavior():
    agent_supervisor.planning_state["approval_status"] = "WAITING_FOR_APPROVAL"
    bp = ProjectBlueprint(
        project_name="TestApp", objective="Test", user_roles=[], features=[],
        functional_requirements=[], non_functional_requirements=[], selected_stack={},
        architecture_summary="", frontend_modules=[], backend_modules=[],
        api_endpoints=[], db_schema=[], folder_structure=[], testing_strategy="",
        development_steps=[], risks=[]
    )
    agent_supervisor.planning_state["blueprint"] = bp
    
    with patch("app.agents.supervisor.contract_graph.build_sample_graph") as mock_cg, \
         patch("app.agents.supervisor.AgentSupervisor.log_activity"):
        response = client.post("/api/v1/blueprint/decision", json={"decision": "APPROVE"})
        
        assert response.status_code == 200
        assert agent_supervisor.planning_state["approval_status"] == "APPROVED"
        assert agent_supervisor.planning_state["blueprint"].approved is True
        assert mock_cg.called

def test_reject_behavior():
    agent_supervisor.planning_state["approval_status"] = "WAITING_FOR_APPROVAL"
    
    with patch("app.agents.supervisor.AgentSupervisor.log_activity"):
        response = client.post("/api/v1/blueprint/decision", json={"decision": "REJECT"})
        
        assert response.status_code == 200
        assert agent_supervisor.planning_state["approval_status"] == "REJECTED"

def test_edit_behavior():
    agent_supervisor.planning_state["approval_status"] = "WAITING_FOR_APPROVAL"
    agent_supervisor.planning_state["blueprint"] = "some_blueprint"
    
    with patch("app.agents.supervisor.AgentSupervisor.log_activity"):
        response = client.post("/api/v1/blueprint/decision", json={"decision": "EDIT", "modifications": "Use SQLite"})
        
        assert response.status_code == 200
        assert agent_supervisor.planning_state["approval_status"] == "EDIT"
        assert agent_supervisor.planning_state["requirements_complete"] is False
        assert agent_supervisor.planning_state["blueprint"] is None
        # Last message should contain the edit request
        last_msg = agent_supervisor.planning_state["messages"][-1].content
        assert "Use SQLite" in last_msg
