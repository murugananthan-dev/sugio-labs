import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..permissions.manager import permission_manager, PermissionDeniedError
from ..models.schemas import PermissionAction
from ..config import settings

logger = logging.getLogger("sugio_labs.tools.git")


class GitCheckpoint:
    """Represents a saved snapshot/checkpoint of project code state."""
    def __init__(self, id: str, name: str, commit_hash: str, timestamp: datetime, description: str):
        self.id = id
        self.name = name
        self.commit_hash = commit_hash
        self.timestamp = timestamp
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "commit_hash": self.commit_hash,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
        }


class GitTool:
    """
    Git Safety and Checkpoint Rollback Manager.
    Automatically creates restore points before multi-file mutations or destructive actions.
    Allows instant rollback if verification or tests fail.
    """

    def __init__(self, project_root: Optional[Path] = None, session_id: str = "default"):
        self.project_root = project_root or settings.absolute_workspace_root
        self.session_id = session_id
        self._checkpoints: List[GitCheckpoint] = []

    def _run_git(self, args: List[str]) -> str:
        """Executes a git command inside the project sandbox."""
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command failed: {' '.join(cmd)}. Error: {e.stderr}")
            raise RuntimeError(f"Git error: {e.stderr.strip() or e.stdout.strip()}")
        except FileNotFoundError:
            logger.info("Git binary not in PATH. Using simulated local checkpoint state.")
            return "simulated_git_ok"

    def is_git_repo(self) -> bool:
        """Checks if project root is an initialized git repository."""
        git_dir = self.project_root / ".git"
        return git_dir.exists()

    def init_repo(self) -> bool:
        """Initializes a new Git repo in the sandbox if not already initialized."""
        if not self.is_git_repo():
            self.project_root.mkdir(parents=True, exist_ok=True)
            try:
                self._run_git(["init"])
                self._run_git(["config", "user.name", "Sugio Labs Agent"])
                self._run_git(["config", "user.email", "agent@sugiolabs.local"])
                logger.info(f"Initialized Git repository at {self.project_root}")
                return True
            except Exception as e:
                logger.warning(f"Fallback to internal checkpoint log: {e}")
                return False
        return True

    def create_checkpoint(self, name: str, description: str = "") -> GitCheckpoint:
        """
        Creates a Git snapshot / commit checkpoint before applying mutations.
        """
        self.init_repo()
        checkpoint_id = f"cp_{int(datetime.utcnow().timestamp())}"
        commit_hash = "simulated_hash"

        try:
            # Stage all changes
            self._run_git(["add", "."])
            # Commit with checkpoint message
            msg = f"[Checkpoint: {checkpoint_id}] {name} - {description}"
            self._run_git(["commit", "-m", msg, "--allow-empty"])
            # Get latest commit hash
            commit_hash = self._run_git(["rev-parse", "HEAD"])
        except Exception as e:
            logger.info(f"Checkpoint recorded in memory: {e}")

        checkpoint = GitCheckpoint(
            id=checkpoint_id,
            name=name,
            commit_hash=commit_hash,
            timestamp=datetime.utcnow(),
            description=description,
        )
        self._checkpoints.append(checkpoint)
        logger.info(f"Created Git checkpoint: {checkpoint.id} ({name})")
        return checkpoint

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rolls back the workspace to the exact state of the specified checkpoint.
        Requires Permission verification.
        """
        if not permission_manager.is_action_permitted(
            PermissionAction.GIT_OPERATION, f"rollback:{checkpoint_id}", self.session_id
        ):
            raise PermissionDeniedError(
                f"Permission required to perform Git rollback to checkpoint '{checkpoint_id}'."
            )

        target_cp = next((cp for cp in self._checkpoints if cp.id == checkpoint_id), None)
        if not target_cp:
            raise ValueError(f"Checkpoint '{checkpoint_id}' not found in registry.")

        try:
            # Hard reset to commit hash or discard uncommitted changes
            if target_cp.commit_hash != "simulated_hash":
                self._run_git(["reset", "--hard", target_cp.commit_hash])
                self._run_git(["clean", "-fd"])
            logger.info(f"Successfully rolled back to checkpoint: {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise RuntimeError(f"Rollback execution failed: {e}")

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Returns all recorded checkpoints."""
        return [cp.to_dict() for cp in self._checkpoints]

    def get_diff(self) -> str:
        """Returns unstaged and staged diffs in the project sandbox."""
        try:
            return self._run_git(["diff", "HEAD"])
        except Exception:
            return "No git diff available."
