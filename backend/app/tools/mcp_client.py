import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path

from .fs import FSTool
from .git_tools import GitTool
from .shell_tools import ShellTool
from ..permissions.manager import permission_manager
from ..models.schemas import PermissionAction
from ..config import settings

logger = logging.getLogger("sugio_labs.tools.mcp")


class MCPToolGateway:
    """
    Standardized MCP Tool Gateway for Sugio Labs.
    Exposes sandboxed, permission-gated tools to AI agents and supervisor routines.
    """

    def __init__(self, project_root: Optional[Path] = None, session_id: str = "default"):
        self.project_root = project_root or settings.absolute_workspace_root
        self.session_id = session_id

        self.fs_tool = FSTool(project_root=self.project_root, session_id=self.session_id)
        self.git_tool = GitTool(project_root=self.project_root, session_id=self.session_id)
        self.shell_tool = ShellTool(project_root=self.project_root, session_id=self.session_id)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool signatures."""
        return [
            {
                "name": "fs_read_file",
                "description": "Reads contents of a file inside the project sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Relative path to file within sandbox"}
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "fs_write_file",
                "description": "Writes or overwrites a file inside the project sandbox. Gated by user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Relative path to file"},
                        "content": {"type": "string", "description": "File content"},
                        "overwrite": {"type": "boolean", "default": True},
                    },
                    "required": ["file_path", "content"],
                },
            },
            {
                "name": "git_create_checkpoint",
                "description": "Creates a Git snapshot checkpoint before applying changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Checkpoint label e.g. Pre-migration snapshot"},
                        "description": {"type": "string", "description": "Explanation of changes about to be applied"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "git_rollback",
                "description": "Reverts sandbox files to a previously saved checkpoint. Gated by user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {"type": "string", "description": "ID of checkpoint to restore"}
                    },
                    "required": ["checkpoint_id"],
                },
            },
            {
                "name": "shell_execute",
                "description": "Executes a shell command (pytest, npm test, etc.) inside the sandbox. Gated by user permission.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command string"},
                        "timeout_seconds": {"type": "integer", "default": 60},
                    },
                    "required": ["command"],
                },
            },
        ]

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches and executes an MCP tool call with permission enforcement.
        """
        logger.info(f"Invoking MCP tool '{tool_name}' with args: {list(args.keys())}")

        if tool_name == "fs_read_file":
            content = self.fs_tool.read_file(args["file_path"])
            return {"success": True, "content": content}

        elif tool_name == "fs_write_file":
            res_path = self.fs_tool.write_file(
                args["file_path"], args["content"], args.get("overwrite", True)
            )
            return {"success": True, "written_file": res_path}

        elif tool_name == "git_create_checkpoint":
            cp = self.git_tool.create_checkpoint(args["name"], args.get("description", ""))
            return {"success": True, "checkpoint": cp.to_dict()}

        elif tool_name == "git_rollback":
            ok = self.git_tool.rollback_to_checkpoint(args["checkpoint_id"])
            return {"success": ok, "checkpoint_id": args["checkpoint_id"]}

        elif tool_name == "shell_execute":
            res = await self.shell_tool.execute(
                args["command"], args.get("timeout_seconds", 60)
            )
            return res

        else:
            raise ValueError(f"Unknown MCP tool: '{tool_name}'")


mcp_gateway = MCPToolGateway()
