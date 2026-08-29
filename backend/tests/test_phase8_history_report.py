import pytest
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.agents.supervisor import AgentSupervisor
from app.models.schemas import ExecutionPlan, ExecutionStep, ExecutionStatus, ProjectWorkspace, ProjectBlueprint

HISTORY_FILE = Path(__file__).parent.parent / "history.json"

@pytest.fixture(autouse=True)
def clean_history():
    if HISTORY_FILE.exists():
        os.remove(HISTORY_FILE)
    yield
    if HISTORY_FILE.exists():
        os.remove(HISTORY_FILE)

@pytest.mark.asyncio
async def test_supervisor_generates_final_report_on_success():
    supervisor = AgentSupervisor()
    supervisor.planning_state["workspace"] = ProjectWorkspace(
        project_id="test-123",
        project_name="Test Project",
        root_path="/tmp",
        mode="CREATE_NEW"
    )
    supervisor.planning_state["blueprint"] = ProjectBlueprint(
        project_name="Test",
        objective="Test Requirement",
        architecture_summary="Test Blueprint",
        user_roles=[],
        features=[],
        functional_requirements=[],
        non_functional_requirements=[],
        selected_stack={"frontend": "", "backend": "", "database": ""},
        frontend_modules=[],
        backend_modules=[],
        api_endpoints=[],
        db_schema=[],
        folder_structure=[],
        testing_strategy="",
        development_steps=[],
        risks=[]
    )
    
    plan = ExecutionPlan(
        blueprint_context="Test Blueprint Context",
        validation_strategy="npm test",
        ordered_steps=[
            ExecutionStep(
                id="step-1",
                title="Create file",
                description="Make file",
                files_to_modify=["src/test.ts"],
                tools_to_use=[],
                risk_level="low"
            )
        ]
    )
    plan.ordered_steps[0].status = ExecutionStatus.COMPLETED
    supervisor.planning_state["execution_plan"] = plan
    
    report = supervisor._generate_final_report("COMPLETED")
    
    assert report.status == "COMPLETED"
    assert report.project_name == "Test Project"
    assert "src/test.ts" in report.modified_files
    assert report.validation_commands == ["npm test"]
    assert report.requirement_summary == "Test Requirement"

@pytest.mark.asyncio
async def test_supervisor_saves_session_history():
    supervisor = AgentSupervisor()
    supervisor.planning_state["workspace"] = ProjectWorkspace(
        project_id="history-123",
        project_name="History Project",
        root_path="/tmp/history",
        mode="IMPORT_EXISTING"
    )
    
    supervisor._save_session_history("COMPLETED")
    
    assert HISTORY_FILE.exists()
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
        
    assert len(history) == 1
    assert history[0]["project_name"] == "History Project"
    assert history[0]["status"] == "COMPLETED"
    assert history[0]["session_id"] == supervisor.active_session_id

@pytest.mark.asyncio
async def test_get_session_history_endpoint():
    from app.api.routes import get_session_history
    
    # Save a fake history
    fake_history = [{"session_id": "123", "timestamp": "2024-01-01T00:00:00Z"}]
    with open(HISTORY_FILE, "w") as f:
        json.dump(fake_history, f)
        
    res = await get_session_history()
    assert len(res) == 1
    assert res[0]["session_id"] == "123"

@pytest.mark.asyncio
async def test_supervisor_generates_final_report_on_failure():
    supervisor = AgentSupervisor()
    plan = ExecutionPlan(
        blueprint_context="Test Blueprint Context",
        validation_strategy="npm test",
        ordered_steps=[
            ExecutionStep(
                id="step-1",
                title="Create file",
                description="Make file",
                files_to_modify=["src/test.ts"],
                tools_to_use=[],
                risk_level="low"
            )
        ]
    )
    plan.ordered_steps[0].status = ExecutionStatus.FAILED
    supervisor.planning_state["execution_plan"] = plan
    
    report = supervisor._generate_final_report("FAILED")
    
    assert report.status == "FAILED"
    # Even on failure, it shouldn't contain raw source contents. It only contains file paths.
    assert "src/test.ts" not in report.modified_files # it failed, so it shouldn't be listed as modified
    assert report.validation_commands == ["npm test"]

@pytest.mark.asyncio
async def test_corrupted_history_fails_safely():
    supervisor = AgentSupervisor()
    supervisor.planning_state["workspace"] = ProjectWorkspace(
        project_id="history-123",
        project_name="History Project",
        root_path="/tmp/history",
        mode="IMPORT_EXISTING"
    )
    
    with open(HISTORY_FILE, "w") as f:
        f.write("invalid json data here!!!")
        
    # Should not raise exception
    supervisor._save_session_history("COMPLETED")
    
    # Should have overwritten or started fresh
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
    assert len(history) == 1
    assert history[0]["project_name"] == "History Project"

@pytest.mark.asyncio
async def test_student_phone_number_scenario_includes_contract_graph_consistency():
    supervisor = AgentSupervisor()
    supervisor.planning_state["workspace"] = ProjectWorkspace(
        project_id="history-123",
        project_name="Student App",
        root_path="/tmp/history",
        mode="IMPORT_EXISTING"
    )
    plan = ExecutionPlan(
        blueprint_context="Add phone number to Student",
        validation_strategy="npm test",
        ordered_steps=[]
    )
    supervisor.planning_state["execution_plan"] = plan
    
    report = supervisor._generate_final_report("COMPLETED")
    assert report.status == "COMPLETED"
    assert hasattr(report, "consistency_result")
    assert report.blueprint_summary == ""
    assert report.requirement_summary == ""

@pytest.mark.asyncio
async def test_report_excludes_secrets_and_source_contents():
    supervisor = AgentSupervisor()
    report = supervisor._generate_final_report("COMPLETED")
    
    dump = report.model_dump(mode="json")
    # Verify no source code fields exist in the schema
    assert "source_code" not in dump
    assert "secrets" not in dump
    assert "environment_variables" not in dump

