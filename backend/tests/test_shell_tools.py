import pytest
from pathlib import Path
from app.tools.shell_tools import ShellTool, SandboxSecurityError
from app.permissions.manager import permission_manager, PermissionDeniedError
from app.models.schemas import PermissionAction, PermissionDecision, PermissionResponse


@pytest.mark.asyncio
async def test_shell_blocked_command(tmp_path: Path):
    tool = ShellTool(project_root=tmp_path, session_id="test_session")
    with pytest.raises(SandboxSecurityError):
        await tool.execute("format c:")


@pytest.mark.asyncio
async def test_shell_permission_gated_execution(tmp_path: Path):
    tool = ShellTool(project_root=tmp_path, session_id="test_session")
    cmd = "echo Hello Sugio Labs"

    # Initially raises PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        await tool.execute(cmd)

    # Approve permission
    reqs = permission_manager.get_pending_requests()
    assert len(reqs) > 0
    req_id = list(reqs.keys())[-1]

    permission_manager.handle_user_decision(
        PermissionResponse(
            request_id=req_id,
            decision=PermissionDecision.ALLOW_FOR_PROJECT,
        )
    )

    # Execute now succeeds
    res = await tool.execute(cmd)
    assert res["success"] is True
    assert "Hello Sugio Labs" in res["stdout"]
