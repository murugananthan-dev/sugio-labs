import pytest
from unittest.mock import patch, MagicMock
from app.agents.supervisor import AgentSupervisor
from app.models.schemas import PermissionResponse, PermissionDecision, RequirementSpec, ProjectBlueprint

@pytest.mark.asyncio
async def test_supervisor_interview_flow():
    supervisor = AgentSupervisor()
    
    # Mock planning graph to skip LLM calls
    with patch("app.agents.supervisor.planning_graph.invoke") as mock_invoke:
        # Turn 1
        mock_invoke.return_value = {
            "session_id": supervisor.active_session_id,
            "messages": [],
            "detected_language": "en",
            "requirements": RequirementSpec(),
            "requirements_complete": False,
            "current_question": "What is the project?",
            "blueprint": None,
            "approval_status": "NONE",
            "errors": []
        }
        res1 = await supervisor.invoke_planning_turn("Hello", "en")
        assert res1["status"] == "planning"
        assert res1["current_question"] == "What is the project?"
        
        # Turn 2: requirements complete, blueprint generated
        bp = ProjectBlueprint(
            project_name="TestApp", objective="Test", user_roles=[], features=[],
            functional_requirements=[], non_functional_requirements=[], selected_stack={},
            architecture_summary="", frontend_modules=[], backend_modules=[],
            api_endpoints=[], db_schema=[], folder_structure=[], testing_strategy="",
            development_steps=[], risks=[]
        )
        mock_invoke.return_value = {
            "session_id": supervisor.active_session_id,
            "messages": [],
            "detected_language": "en",
            "requirements": RequirementSpec(),
            "requirements_complete": True,
            "current_question": None,
            "blueprint": bp,
            "approval_status": "WAITING_FOR_APPROVAL",
            "errors": []
        }
        res2 = await supervisor.invoke_planning_turn("Student app", "en")
        assert res2["requirements_complete"] is True
        assert res2["approval_status"] == "WAITING_FOR_APPROVAL"
        
        # Approve Blueprint
        with patch("app.agents.supervisor.contract_graph.build_sample_graph") as mock_cg, \
             patch.object(supervisor, "log_activity"):
            approved_res = await supervisor.handle_blueprint_decision("APPROVE")
            assert approved_res["status"] == "success"
            assert approved_res["approval_status"] == "APPROVED"
            assert mock_cg.called

@pytest.mark.asyncio
async def test_supervisor_change_request_and_permission():
    supervisor = AgentSupervisor()
    # Handle change request
    change_res = await supervisor.handle_change_request("Add emergency contact phone number to student profile")
    assert "impact_report" in change_res
    assert "permission_request" in change_res

    perm_id = change_res["permission_request"]["id"]

    # Submit user approval
    decision = PermissionResponse(
        request_id=perm_id,
        decision=PermissionDecision.ALLOW_ONCE,
    )
    perm_res = await supervisor.submit_permission_decision(decision)
    assert perm_res["granted"] is True
