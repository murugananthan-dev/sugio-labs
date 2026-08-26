import os
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..permissions.manager import permission_manager, PermissionDeniedError, SandboxSecurityError
from ..models.schemas import PermissionAction
from ..config import settings

logger = logging.getLogger("sugio_labs.tools.shell")

# Disallowed dangerous commands/patterns that cannot be executed
BLOCKED_PATTERNS = [
    "format ",
    "rmdir /s",
    "del /f /s /q c:",
    "rm -rf /",
    "shutdown",
    "mkfs",
    ":(){ :|:& };:",
    "net user",
    "diskpart",
]


class ShellTool:
    """
    Sandboxed Shell Command Execution Tool for Sugio Labs.
    Executes build, test, and package manager commands inside the project sandbox with strict permission checks.
    """

    def __init__(self, project_root: Optional[Path] = None, session_id: str = "default"):
        self.project_root = project_root or settings.absolute_workspace_root
        self.session_id = session_id

    def _sanitize_command(self, command: str):
        """Checks command against security blacklist."""
        cmd_lower = command.lower().strip()
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                raise SandboxSecurityError(
                    f"Security Block: Command contains forbidden pattern '{pattern}'."
                )

    async def execute(
        self,
        command: str,
        timeout_seconds: int = 60,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a shell command inside the project sandbox.
        Requires Permission verification.
        """
        self._sanitize_command(command)

        # Check permission
        if not permission_manager.is_action_permitted(
            PermissionAction.EXECUTE_COMMAND, command, self.session_id
        ):
            # Prompt user in permission store
            await permission_manager.request_permission(
                action=PermissionAction.EXECUTE_COMMAND,
                target=command,
                details={"cwd": str(self.project_root), "timeout": timeout_seconds},
                risk_level="high" if any(k in command for k in ["delete", "drop", "clean", "reset"]) else "medium",
                project_id=self.session_id,
            )
            raise PermissionDeniedError(
                f"Permission required to execute command: '{command}'. Please approve in UI."
            )

        start_time = time.time()
        self.project_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        try:
            process = subprocess.run(
                command,
                cwd=str(self.project_root),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"Executed command '{command}' in {elapsed}s (exit {process.returncode})")

            return {
                "command": command,
                "exit_code": process.returncode,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "elapsed_seconds": elapsed,
                "success": process.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout_seconds}s: {command}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "elapsed_seconds": timeout_seconds,
                "success": False,
            }
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return {
                "command": command,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "elapsed_seconds": round(time.time() - start_time, 2),
                "success": False,
            }
