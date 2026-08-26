import pytest
from pathlib import Path
from app.tools.git_tools import GitTool
from app.permissions.manager import permission_manager
from app.models.schemas import PermissionAction, PermissionDecision, PermissionResponse


def test_git_checkpoint_creation(tmp_path: Path):
    sandbox = tmp_path / "test_sandbox"
    sandbox.mkdir()

    tool = GitTool(project_root=sandbox, session_id="test_session")
    cp = tool.create_checkpoint("Initial state", "Base code before student feature")

    assert cp.id.startswith("cp_")
    assert cp.name == "Initial state"
    assert len(tool.list_checkpoints()) == 1


@pytest.mark.asyncio
async def test_git_rollback_permission_flow(tmp_path: Path):
    sandbox = tmp_path / "test_sandbox"
    sandbox.mkdir()

    tool = GitTool(project_root=sandbox, session_id="test_session")
    cp = tool.create_checkpoint("Pre-migration", "Snapshot before modifying schema")

    # Grant permission for rollback
    key = f"rollback:{cp.id}"
    req = await permission_manager.request_permission(
        action=PermissionAction.GIT_OPERATION,
        target=key,
        project_id="test_session",
    )
    permission_manager.handle_user_decision(
        PermissionResponse(
            request_id=req.id,
            decision=PermissionDecision.ALLOW_ONCE,
        )
    )

    # Execute rollback
    ok = tool.rollback_to_checkpoint(cp.id)
    assert ok is True
