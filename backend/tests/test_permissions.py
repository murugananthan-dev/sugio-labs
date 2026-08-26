import pytest
from pathlib import Path
from app.permissions.manager import PermissionManager, SandboxSecurityError
from app.models.schemas import (
    PermissionAction,
    PermissionDecision,
    PermissionResponse,
)


@pytest.mark.asyncio
async def test_sandbox_validation(tmp_path: Path):
    mgr = PermissionManager()
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    # Valid inside sandbox
    valid_file = sandbox / "app" / "main.py"
    resolved = mgr.validate_path("app/main.py", project_root=sandbox)
    assert resolved == valid_file.resolve()

    # Invalid path traversal
    with pytest.raises(SandboxSecurityError):
        mgr.validate_path("../../../etc/passwd", project_root=sandbox)


@pytest.mark.asyncio
async def test_permission_flow(tmp_path: Path):
    mgr = PermissionManager()
    target = "app/models/student.py"

    # Initially not permitted
    assert not mgr.is_action_permitted(PermissionAction.WRITE_FILE, target, "test_proj")

    # Request permission
    req = await mgr.request_permission(
        action=PermissionAction.WRITE_FILE,
        target=target,
        project_id="test_proj",
    )
    assert req.id in mgr.get_pending_requests()

    # Approve for project
    decision = PermissionResponse(
        request_id=req.id,
        decision=PermissionDecision.ALLOW_FOR_PROJECT,
    )
    granted = mgr.handle_user_decision(decision)
    assert granted is True
    assert req.id not in mgr.get_pending_requests()

    # Now it should be permitted persistently for the project
    assert mgr.is_action_permitted(PermissionAction.WRITE_FILE, target, "test_proj")


@pytest.mark.asyncio
async def test_permission_rejection():
    mgr = PermissionManager()
    target = "dangerous_script.sh"

    req = await mgr.request_permission(
        action=PermissionAction.EXECUTE_COMMAND,
        target=target,
        project_id="test_proj",
    )
    assert req.id in mgr.get_pending_requests()

    decision = PermissionResponse(
        request_id=req.id,
        decision=PermissionDecision.REJECT,
        reason="Security violation",
    )
    granted = mgr.handle_user_decision(decision)
    assert granted is False
    assert not mgr.is_action_permitted(PermissionAction.EXECUTE_COMMAND, target, "test_proj")
