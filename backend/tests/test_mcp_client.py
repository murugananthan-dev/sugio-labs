import pytest
from pathlib import Path
from app.tools.mcp_client import MCPToolGateway
from app.permissions.manager import permission_manager
from app.models.schemas import PermissionAction, PermissionDecision, PermissionResponse


def test_mcp_tool_definitions():
    gateway = MCPToolGateway()
    defs = gateway.get_tool_definitions()
    names = [d["name"] for d in defs]

    assert "fs_read_file" in names
    assert "fs_write_file" in names
    assert "git_create_checkpoint" in names
    assert "git_rollback" in names
    assert "shell_execute" in names


@pytest.mark.asyncio
async def test_mcp_fs_write_and_read(tmp_path: Path):
    gateway = MCPToolGateway(project_root=tmp_path, session_id="test_mcp_session")
    target_rel = "app/models/sample.py"
    target_abs = str((tmp_path / target_rel).resolve())
    content = "print('Hello MCP')"

    # Pre-approve write & read permissions
    req_write = await permission_manager.request_permission(
        action=PermissionAction.WRITE_FILE,
        target=target_abs,
        project_id="test_mcp_session",
    )
    permission_manager.handle_user_decision(
        PermissionResponse(
            request_id=req_write.id,
            decision=PermissionDecision.ALLOW_FOR_PROJECT,
        )
    )

    req_read = await permission_manager.request_permission(
        action=PermissionAction.READ_FILE,
        target=target_abs,
        project_id="test_mcp_session",
    )
    permission_manager.handle_user_decision(
        PermissionResponse(
            request_id=req_read.id,
            decision=PermissionDecision.ALLOW_FOR_PROJECT,
        )
    )

    # Write file via MCP
    write_res = await gateway.execute_tool(
        "fs_write_file", {"file_path": target_rel, "content": content}
    )
    assert write_res["success"] is True

    # Read file via MCP
    read_res = await gateway.execute_tool("fs_read_file", {"file_path": target_rel})
    assert read_res["success"] is True
    assert read_res["content"] == content
