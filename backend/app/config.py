import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """Application settings and configuration."""
    app_name: str = Field(default="Sugio Labs")
    debug: bool = Field(default=True)
    port: int = Field(default=8000)
    host: str = Field(default="127.0.0.1")

    # Ollama Local AI Settings
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    default_model: str = Field(default="llama3:8b")
    fallback_model: str = Field(default="qwen2.5-coder:7b")
    offline_mode: bool = Field(default=True)

    # Database
    database_url: str = Field(default="sqlite:///./data/sugio_labs.db")

    # Storage and Sandbox Path
    base_dir: Path = Path(__file__).resolve().parent.parent
    workspace_root: str = Field(default="./projects_sandbox")

    # Security
    strict_permissions: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def absolute_workspace_root(self) -> Path:
        """Returns the absolute resolved path for the workspace root."""
        root = Path(self.workspace_root)
        if not root.is_absolute():
            root = (self.base_dir / root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

settings = Settings()
