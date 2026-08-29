import os
from pathlib import Path
from typing import Dict, Any

from ..models.schemas import WorkspaceMode, ProjectWorkspace, ProjectScanResult, PermissionAction
from ..permissions.manager import permission_manager, SandboxSecurityError

class WorkspaceManager:
    """Handles workspace creation, importing, and stack detection."""
    
    async def import_project(self, target_path: str, session_id: str) -> ProjectScanResult:
        """Imports an existing project folder safely."""
        target_dir = Path(target_path).resolve()
        
        if not target_dir.exists() or not target_dir.is_dir():
            raise ValueError(f"Target path {target_path} is not a valid directory.")
            
        # Temporarily bypass the standard sandbox check by asking permission on the absolute path
        # Once allowed, this path becomes the NEW sandbox for this project.
        perm_req = await permission_manager.request_permission(
            action=PermissionAction.READ_FILE,
            target=str(target_dir),
            details={"description": "Importing existing project workspace."},
            risk_level="high",
            project_id=session_id
        )
        
        # If the request was newly created, it won't be permitted yet
        if not permission_manager.is_action_permitted(PermissionAction.READ_FILE, str(target_dir), session_id):
            raise PermissionError(f"Permission required to import {target_dir}. Request ID: {perm_req.id}")
            
        return self._scan_project(target_dir)
        
    async def create_project(self, project_name: str, parent_path: str, session_id: str) -> ProjectWorkspace:
        """Creates a new project folder safely."""
        parent_dir = Path(parent_path).resolve()
        target_dir = parent_dir / project_name
        
        if not parent_dir.exists() or not parent_dir.is_dir():
            raise ValueError(f"Parent path {parent_path} is not a valid directory.")
            
        if target_dir.exists():
            raise ValueError(f"Cannot create project: {target_dir} already exists.")
            
        # Request permission to write the new folder
        perm_req = await permission_manager.request_permission(
            action=PermissionAction.WRITE_FILE,
            target=str(target_dir),
            details={"description": f"Creating new project '{project_name}'."},
            risk_level="high",
            project_id=session_id
        )
        
        if not permission_manager.is_action_permitted(PermissionAction.WRITE_FILE, str(target_dir), session_id):
            raise PermissionError(f"Permission required to create project at {target_dir}. Request ID: {perm_req.id}")
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        return ProjectWorkspace(
            project_id=session_id,
            project_name=project_name,
            root_path=str(target_dir),
            mode=WorkspaceMode.CREATE_NEW,
            detected_stack={},
            git_enabled=False,
            status="active"
        )
        
    def _scan_project(self, root: Path) -> ProjectScanResult:
        """Scans the directory to detect languages and stack."""
        ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "coverage"}
        important_files = []
        ignored_dirs = []
        
        has_frontend = False
        has_backend = False
        git_enabled = (root / ".git").exists()
        
        languages = set()
        frameworks = set()
        
        for item in root.iterdir():
            if item.name in ignored:
                ignored_dirs.append(item.name)
                continue
                
            if item.is_file():
                if item.name == "package.json":
                    languages.add("JavaScript/TypeScript")
                    frameworks.add("Node.js")
                    has_frontend = True
                    important_files.append(item.name)
                elif item.name == "pyproject.toml" or item.name == "requirements.txt":
                    languages.add("Python")
                    has_backend = True
                    important_files.append(item.name)
                elif item.name == "pom.xml":
                    languages.add("Java")
                    frameworks.add("Maven")
                    has_backend = True
                    important_files.append(item.name)
                elif item.name == "Cargo.toml":
                    languages.add("Rust")
                    has_backend = True
                    important_files.append(item.name)
                elif item.name == "go.mod":
                    languages.add("Go")
                    has_backend = True
                    important_files.append(item.name)
                    
        return ProjectScanResult(
            project_name=root.name,
            root_path=str(root),
            detected_languages=list(languages),
            detected_frameworks=list(frameworks),
            frontend_detected=has_frontend,
            backend_detected=has_backend,
            git_status="enabled" if git_enabled else "disabled",
            important_files=important_files,
            ignored_directories=ignored_dirs,
            warnings=[]
        )

workspace_manager = WorkspaceManager()
