import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..permissions.manager import permission_manager, SandboxSecurityError, PermissionDeniedError
from ..models.schemas import PermissionAction
from ..config import settings

logger = logging.getLogger("sugio_labs.tools.fs")


class FSTool:
    """
    Permission-Gated, Sandbox-Confined Filesystem Tool for Sugio Labs.
    Ensures no AI operation accesses files outside the workspace root without explicit user approval.
    """

    def __init__(self, project_root: Optional[Path] = None, session_id: str = "default"):
        self.project_root = project_root or settings.absolute_workspace_root
        self.session_id = session_id

    def _check_permission(self, action: PermissionAction, target: str, details: Optional[Dict[str, Any]] = None):
        """Verifies if the action on target is permitted, or raises PermissionDeniedError."""
        if not permission_manager.is_action_permitted(action, target, self.session_id):
            raise PermissionDeniedError(
                f"Permission required for action '{action.value}' on '{target}'. Please approve in UI."
            )

    def read_file(self, file_path: str) -> str:
        """Reads contents of a file within the project sandbox."""
        resolved = permission_manager.validate_path(file_path, self.project_root)
        self._check_permission(PermissionAction.READ_FILE, str(resolved))

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")
        if not resolved.is_file():
            raise IsADirectoryError(f"Target is a directory, not a file: {resolved}")

        return resolved.read_text(encoding="utf-8")

    def write_file(self, file_path: str, content: str, overwrite: bool = True) -> str:
        """Writes content to a file within the project sandbox."""
        resolved = permission_manager.validate_path(file_path, self.project_root)
        self._check_permission(
            PermissionAction.WRITE_FILE,
            str(resolved),
            details={"content_preview": content[:200], "length": len(content), "overwrite": overwrite},
        )

        resolved.parent.mkdir(parents=True, exist_ok=True)
        if resolved.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite is False: {resolved}")

        resolved.write_text(content, encoding="utf-8")
        logger.info(f"Successfully wrote {len(content)} bytes to {resolved}")
        return str(resolved)

    def delete_file(self, file_path: str) -> bool:
        """Deletes a file or directory within the project sandbox."""
        resolved = permission_manager.validate_path(file_path, self.project_root)
        self._check_permission(PermissionAction.DELETE_FILE, str(resolved))

        if not resolved.exists():
            return False

        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()

        logger.info(f"Successfully deleted {resolved}")
        return True

    def list_dir(self, dir_path: str = "") -> List[Dict[str, Any]]:
        """Lists files and directories inside a sandbox folder."""
        resolved = permission_manager.validate_path(dir_path or ".", self.project_root)
        self._check_permission(PermissionAction.READ_FILE, str(resolved))

        if not resolved.exists() or not resolved.is_dir():
            return []

        entries = []
        for item in resolved.iterdir():
            entries.append({
                "name": item.name,
                "path": str(item.relative_to(self.project_root)),
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else 0,
            })
        return sorted(entries, key=lambda x: (not x["is_dir"], x["name"].lower()))
