import uuid
import logging
from pathlib import Path
from typing import Dict, Optional, Set, Any, Callable, Awaitable
from ..models.schemas import (
    PermissionAction,
    PermissionDecision,
    PermissionRequest,
    PermissionResponse,
)
from ..config import settings

logger = logging.getLogger("sugio_labs.permissions")

class SandboxSecurityError(Exception):
    """Raised when an operation attempts to access paths outside the project sandbox."""
    pass

class PermissionDeniedError(Exception):
    """Raised when user rejects an action or permission is not granted."""
    pass

class PermissionManager:
    """
    Zero-Trust Human-in-the-Loop Permission Manager.
    Sits between AI reasoning / MCP tool requests and actual system execution.
    """
    def __init__(self):
        # Maps project_id -> set of granted (action, target) tuples for the project lifetime
        self._project_permissions: Dict[str, Set[str]] = {}
        # Pending requests awaiting user decision: request_id -> (request, async_future/callback)
        self._pending_requests: Dict[str, PermissionRequest] = {}
        # Callback to broadcast permission requests to connected WebSockets
        self._broadcast_callback: Optional[Callable[[PermissionRequest], Awaitable[None]]] = None

    def register_broadcast_callback(self, callback: Callable[[PermissionRequest], Awaitable[None]]):
        """Registers WebSocket broadcast callback for real-time UI prompts."""
        self._broadcast_callback = callback

    def validate_path(self, target_path: str, project_root: Optional[Path] = None) -> Path:
        """
        Validates that target_path is strictly within the allowed project sandbox root.
        Prevents directory traversal attacks (e.g., ../../etc/passwd or Windows system files).
        """
        sandbox = project_root.resolve() if project_root else settings.absolute_workspace_root
        target = Path(target_path)
        
        # If relative, resolve relative to sandbox
        if not target.is_absolute():
            resolved = (sandbox / target).resolve()
        else:
            resolved = target.resolve()

        # Check if resolved path starts with the sandbox root
        try:
            resolved.relative_to(sandbox)
        except ValueError:
            raise SandboxSecurityError(
                f"Security Sandbox Violation: Path '{target_path}' is outside the authorized project root '{sandbox}'."
            )
        return resolved

    def _permission_key(self, action: PermissionAction, target: str) -> str:
        return f"{action.value}:{target.lower().strip()}"

    def is_action_permitted(
        self,
        action: PermissionAction,
        target: str,
        project_id: Optional[str] = "default",
    ) -> bool:
        """Checks if the action on target has already been granted 'allow_for_project'."""
        if not settings.strict_permissions:
            return True
            
        key = self._permission_key(action, target)
        if project_id and project_id in self._project_permissions:
            if key in self._project_permissions[project_id] or f"{action.value}:*" in self._project_permissions[project_id]:
                return True
        return False

    async def request_permission(
        self,
        action: PermissionAction,
        target: str,
        details: Optional[Dict[str, Any]] = None,
        risk_level: str = "medium",
        project_id: Optional[str] = "default",
    ) -> PermissionRequest:
        """
        Creates a permission request. If already approved for project, returns immediately.
        Otherwise, registers the pending request and notifies the UI.
        """
        req_id = str(uuid.uuid4())
        req = PermissionRequest(
            id=req_id,
            action=action,
            target=target,
            details=details or {},
            risk_level=risk_level,
            session_id=project_id,
        )

        # If already permitted for project, mark it
        if self.is_action_permitted(action, target, project_id):
            logger.info(f"Action '{action}' on '{target}' is pre-approved for project '{project_id}'.")
            return req

        self._pending_requests[req_id] = req
        logger.info(f"Created pending permission request {req_id} for {action} on {target}.")

        if self._broadcast_callback:
            try:
                await self._broadcast_callback(req)
            except Exception as e:
                logger.error(f"Failed to broadcast permission request: {e}")

        return req

    def handle_user_decision(self, response: PermissionResponse) -> bool:
        """
        Processes user decision from UI:
        - ALLOW_ONCE: Removes from pending, allows single execution
        - ALLOW_FOR_PROJECT: Saves to project permission store, allows execution
        - REJECT: Rejects and raises PermissionDeniedError
        """
        req = self._pending_requests.pop(response.request_id, None)
        if not req:
            logger.warning(f"Permission request {response.request_id} not found or expired.")
            return False

        if response.decision == PermissionDecision.ALLOW_FOR_PROJECT:
            proj_id = req.session_id or "default"
            if proj_id not in self._project_permissions:
                self._project_permissions[proj_id] = set()
            key = self._permission_key(req.action, req.target)
            self._project_permissions[proj_id].add(key)
            logger.info(f"Granted persistent project permission: {key} for project {proj_id}")
            return True

        elif response.decision == PermissionDecision.ALLOW_ONCE:
            logger.info(f"Granted single-use permission for request {req.id}")
            return True

        else: # REJECT
            logger.warning(f"User rejected permission request {req.id}. Reason: {response.reason}")
            return False

    def clear_project_permissions(self, project_id: str):
        """Clears all cached permissions for a project session."""
        if project_id in self._project_permissions:
            del self._project_permissions[project_id]

    def get_pending_requests(self) -> Dict[str, PermissionRequest]:
        return self._pending_requests

permission_manager = PermissionManager()
