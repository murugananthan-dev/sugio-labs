"""
test_phase7.py
==============================
20 tests covering Phase 7 — Workspace Import + Live Execution Progress + FIX / RETRY Flow.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.workspace.manager import workspace_manager
from app.permissions.manager import PermissionManager, PermissionAction, permission_manager, SandboxSecurityError, PermissionDeniedError
from app.models.schemas import WorkspaceMode, ProjectWorkspace, ProjectScanResult, ExecutionPlan, ExecutionStep, ExecutionStatus
from app.agents.supervisor import AgentSupervisor, WSMessage, WSMessageType

# --- 1-8: WORKSPACE IMPORT / CREATE ---

@pytest.mark.asyncio
async def test_t01_imported_workspace_requires_explicit_permission(tmp_path):
    """1. imported workspace requires explicit permission"""
    session_id = "sess_01"
    target_path = tmp_path / "existing_project"
    target_path.mkdir()
    
    # Mock permission manager to deny by default
    with patch.object(permission_manager, 'request_permission', return_value=MagicMock(id="req_123")) as mock_req:
        with patch.object(permission_manager, 'is_action_permitted', return_value=False):
            with pytest.raises(PermissionError, match="Permission required"):
                await workspace_manager.import_project(str(target_path), session_id)
            mock_req.assert_called_once()

@pytest.mark.asyncio
async def test_t02_import_is_read_only(tmp_path):
    """2. import is read-only"""
    session_id = "sess_02"
    target_path = tmp_path / "existing_project"
    target_path.mkdir()
    
    # Allow read, but we verify import_project only requests READ_FILE
    with patch.object(permission_manager, 'request_permission', return_value=MagicMock(id="req_123")) as mock_req:
        with patch.object(permission_manager, 'is_action_permitted', return_value=True):
            await workspace_manager.import_project(str(target_path), session_id)
            # Should have requested READ_FILE, not WRITE_FILE
            assert mock_req.call_args[1]["action"] == PermissionAction.READ_FILE

@pytest.mark.asyncio
async def test_t03_invalid_path_rejected(tmp_path):
    """3. invalid/nonexistent path rejected"""
    session_id = "sess_03"
    non_existent = tmp_path / "does_not_exist"
    
    with pytest.raises(ValueError, match="is not a valid directory"):
        await workspace_manager.import_project(str(non_existent), session_id)

@pytest.mark.asyncio
async def test_t04_path_traversal_outside_workspace_rejected(tmp_path):
    """4. path traversal outside workspace rejected"""
    from app.tools.fs import FSTool
    session_id = "sess_04"
    workspace_root = tmp_path / "sandbox"
    workspace_root.mkdir()
    
    fs_tool = FSTool(project_root=workspace_root, session_id=session_id)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret")
    
    with pytest.raises(SandboxSecurityError, match="Security Sandbox Violation"):
        await fs_tool.read_file(str(outside_file))

@pytest.mark.asyncio
async def test_t05_generated_directories_ignored(tmp_path):
    """5. generated directories ignored"""
    session_id = "sess_05"
    target_path = tmp_path / "my_proj"
    target_path.mkdir()
    (target_path / "node_modules").mkdir()
    (target_path / "dist").mkdir()
    (target_path / "package.json").write_text("{}")
    
    with patch.object(permission_manager, 'is_action_permitted', return_value=True):
        res = await workspace_manager.import_project(str(target_path), session_id)
        assert "node_modules" in res.ignored_directories
        assert "dist" in res.ignored_directories

@pytest.mark.asyncio
async def test_t06_deterministic_stack_detection(tmp_path):
    """6. deterministic stack detection"""
    session_id = "sess_06"
    target_path = tmp_path / "my_proj"
    target_path.mkdir()
    (target_path / "package.json").write_text("{}")
    (target_path / "pyproject.toml").write_text("")
    
    with patch.object(permission_manager, 'is_action_permitted', return_value=True):
        res = await workspace_manager.import_project(str(target_path), session_id)
        assert res.frontend_detected
        assert res.backend_detected
        assert "Python" in res.detected_languages
        assert "JavaScript/TypeScript" in res.detected_languages

@pytest.mark.asyncio
async def test_t07_git_detection(tmp_path):
    """7. Git detection"""
    session_id = "sess_07"
    target_path = tmp_path / "my_proj"
    target_path.mkdir()
    (target_path / ".git").mkdir()
    
    with patch.object(permission_manager, 'is_action_permitted', return_value=True):
        res = await workspace_manager.import_project(str(target_path), session_id)
        assert res.git_status == "enabled"

@pytest.mark.asyncio
async def test_t08_create_new_collision_blocked(tmp_path):
    """8. CREATE_NEW collision blocked"""
    session_id = "sess_08"
    parent_path = tmp_path / "projects"
    parent_path.mkdir()
    (parent_path / "existing_app").mkdir()
    
    with pytest.raises(ValueError, match="already exists"):
        await workspace_manager.create_project("existing_app", str(parent_path), session_id)

# --- 9-14: LIVE WS EVENTS ---

@pytest.fixture
def mock_ws_broadcast():
    return AsyncMock()

@pytest.fixture
def mock_supervisor(mock_ws_broadcast):
    sup = AgentSupervisor()
    sup.active_session_id = "sess_ws"
    sup._ws_broadcast = mock_ws_broadcast
    
    # Setup dummy plan
    plan = ExecutionPlan(
        blueprint_context="ctx",
        ordered_steps=[
            ExecutionStep(id="s1", title="Step 1", description="", files_to_read=[], files_to_modify=[], commands=[], dependencies=[], risk_level="low", requires_permission=False, status=ExecutionStatus.PENDING)
        ],
        overall_risk="low",
        estimated_affected_files=1,
        validation_strategy="none"
    )
    sup.planning_state = {
        "session_id": "sess_ws",
        "messages": [],
        "requirements_complete": False,
        "current_question": None,
        "blueprint": None,
        "approval_status": "NONE",
        "execution_plan": plan,
        "execution_approval_status": "WAITING_FOR_EXECUTION_APPROVAL",
        "current_step_index": 0,
        "execution_results": [],
        "git_checkpoint_id": "cp_1",
        "workspace": None
    }
    return sup

@pytest.mark.asyncio
async def test_t09_t10_t11_t13_execution_started_step_started_validation_completed_events(mock_supervisor, mock_ws_broadcast):
    """9, 10, 11, 13: execution_started, step_started, validation_started, step_completed, execution_completed"""
    # Mock nodes to pass instantly
    with patch("app.agents.supervisor.git_checkpoint_node", AsyncMock(return_value=mock_supervisor.planning_state)):
        with patch("app.agents.supervisor.coding_agent_node", AsyncMock(return_value=mock_supervisor.planning_state)):
            # Validation node adds success result
            async def mock_val(state):
                state["execution_results"] = [{"step_id": "s1", "success": True, "output": "ok"}]
                state["current_step_index"] = 1
                return state
            with patch("app.agents.supervisor.validation_node", mock_val):
                await mock_supervisor.handle_execution_decision("APPROVE")
    
    broadcast_types = [call[0][0].type.value for call in mock_ws_broadcast.call_args_list]
    assert WSMessageType.EXECUTION_STARTED.value in broadcast_types
    assert WSMessageType.STEP_STARTED.value in broadcast_types
    assert WSMessageType.VALIDATION_STARTED.value in broadcast_types
    assert WSMessageType.STEP_COMPLETED.value in broadcast_types
    assert WSMessageType.EXECUTION_COMPLETED.value in broadcast_types

@pytest.mark.asyncio
async def test_t12_execution_failed_emitted(mock_supervisor, mock_ws_broadcast):
    """12. execution_failed emitted"""
    # Force validation to fail
    with patch("app.agents.supervisor.git_checkpoint_node", AsyncMock(return_value=mock_supervisor.planning_state)):
        with patch("app.agents.supervisor.coding_agent_node", AsyncMock(return_value=mock_supervisor.planning_state)):
            async def mock_val(state):
                state["execution_results"] = [{"step_id": "s1", "success": False, "error": "failed"}]
                state["execution_plan"].ordered_steps[0].status = ExecutionStatus.FAILED
                state["execution_plan"].ordered_steps[0].result_details = "failed"
                return state
            
            with patch("app.agents.supervisor.validation_node", mock_val):
                res = await mock_supervisor.handle_execution_decision("APPROVE")
    
    assert res["status"] == "failed"
    broadcast_types = [call[0][0].type.value for call in mock_ws_broadcast.call_args_list]
    assert WSMessageType.EXECUTION_FAILED.value in broadcast_types

@pytest.mark.asyncio
async def test_t14_permission_required_emitted(mock_supervisor, mock_ws_broadcast):
    """14. permission_required emitted where applicable (by Activity log actually, but via WS manager).
    The Activity log is tested elsewhere, but we ensure PermissionManager emits WS events."""
    from app.api.websocket import ws_manager
    with patch.object(ws_manager, "broadcast_permission_request", new_callable=AsyncMock) as mock_broadcast:
        permission_manager.register_broadcast_callback(mock_broadcast)
        await permission_manager.request_permission(PermissionAction.WRITE_FILE, "foo", dict(), "low", mock_supervisor.active_session_id)
        mock_broadcast.assert_called_once()
        # Since we just mocked broadcast_permission_request, it would be called with the permission request object.
        req = mock_broadcast.call_args[0][0]
        assert req.target == "foo"

# --- 15-20: RECOVERY FLOWS ---

@pytest.mark.asyncio
async def test_t15_retry_does_not_rerun_completed_steps(mock_supervisor):
    """15. RETRY does not rerun completed steps"""
    plan = mock_supervisor.planning_state["execution_plan"]
    plan.ordered_steps.append(ExecutionStep(id="s2", title="Step 2", description="", files_to_read=[], files_to_modify=[], commands=[], dependencies=[], risk_level="low", requires_permission=False, status=ExecutionStatus.FAILED))
    mock_supervisor.planning_state["current_step_index"] = 1
    mock_supervisor.planning_state["execution_results"] = [{"step_id": "s1", "success": True}]
    
    # Call RETRY
    with patch("app.agents.supervisor.git_checkpoint_node", AsyncMock(return_value=mock_supervisor.planning_state)):
        with patch("app.agents.supervisor.coding_agent_node", AsyncMock(return_value=mock_supervisor.planning_state)):
            async def mock_val(state):
                return state
            with patch("app.agents.supervisor.validation_node", mock_val):
                await mock_supervisor.handle_execution_decision("RETRY")
                
                assert plan.ordered_steps[1].status == ExecutionStatus.PENDING

@pytest.mark.asyncio
async def test_t16_fix_creates_corrective_work_and_requires_fresh_approval(mock_supervisor):
    """16. FIX creates corrective work and requires fresh approval"""
    mock_supervisor.planning_state["messages"] = []
    
    with patch("app.agents.supervisor.execution_planner_node", return_value=mock_supervisor.planning_state) as mock_planner:
        await mock_supervisor.handle_execution_decision("FIX", modifications="fix the syntax error")
        
        # Planner should be re-run
        mock_planner.assert_called_once()
        # Message should be appended
        assert len(mock_supervisor.planning_state["messages"]) == 1
        assert "fix the syntax error" in mock_supervisor.planning_state["messages"][0].content
        # Status should be WAITING
        assert mock_supervisor.planning_state["execution_approval_status"] == "WAITING_FOR_EXECUTION_APPROVAL"

@pytest.mark.asyncio
async def test_t17_rollback_remains_permission_gated(mock_supervisor):
    """17. ROLLBACK remains permission-gated"""
    from app.tools.git_tools import GitTool
    mock_supervisor.planning_state["workspace"] = ProjectWorkspace(project_id="s", project_name="p", root_path="/test", mode=WorkspaceMode.CREATE_NEW, detected_stack={}, git_enabled=True, status="active")
    
    with patch.object(GitTool, 'rollback_to_checkpoint') as mock_rollback:
        # Mock permission manager to raise error if not permitted
        mock_rollback.side_effect = PermissionError("Permission denied")
        with pytest.raises(ValueError, match="Rollback failed: Permission denied"):
            await mock_supervisor.handle_execution_decision("ROLLBACK")

@pytest.mark.asyncio
async def test_t18_session_recovery_preserves_workspace_and_execution_state(mock_supervisor):
    """18. session recovery preserves workspace + execution state (via routes check or Supervisor instance)"""
    ws = ProjectWorkspace(project_id="s", project_name="p", root_path="/test", mode=WorkspaceMode.CREATE_NEW, detected_stack={}, git_enabled=True, status="active")
    mock_supervisor.planning_state["workspace"] = ws
    mock_supervisor.planning_state["current_step_index"] = 2
    
    state = mock_supervisor.get_session_state()
    assert state["workspace"]["root_path"] == "/test"
    assert state["current_step_index"] == 2
    assert state["has_execution_plan"] == True

@pytest.mark.asyncio
async def test_t19_imported_workspace_permission_is_not_silently_restored(tmp_path):
    """19. imported workspace permission is not silently restored.
    If the sandbox is not explicitly approved, tools should block it.
    (This is intrinsic to PermissionManager being ephemeral in memory)"""
    from app.tools.fs import FSTool
    session_id = "sess_19"
    workspace_root = tmp_path / "sandbox"
    workspace_root.mkdir()
    target_file = workspace_root / "test.txt"
    target_file.write_text("hello")
    
    # Start fresh manager
    fresh_pm = PermissionManager()
    with patch('app.tools.fs.permission_manager', fresh_pm):
        fs_tool = FSTool(project_root=workspace_root, session_id=session_id)
        # We don't have permission!
        with pytest.raises(PermissionDeniedError):
            await fs_tool.read_file(str(target_file))

@pytest.mark.asyncio
async def test_t20_ollama_offline_fix_flow_fails_safely(mock_supervisor):
    """20. Ollama-offline FIX flow fails safely"""
    # Make execution_planner_node throw an exception
    with patch("app.agents.supervisor.execution_planner_node", side_effect=ConnectionError("Ollama offline")):
        with pytest.raises(ConnectionError, match="Ollama offline"):
            await mock_supervisor.handle_execution_decision("FIX", modifications="fix this")
