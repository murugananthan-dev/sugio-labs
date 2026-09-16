import os
import platform
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    """Return a writable per-user data directory on every desktop platform."""
    override = os.getenv("SUGIO_DATA_DIR")
    if override:
        return Path(override).expanduser()

    system = platform.system()
    home = Path.home()

    if system == "Windows":
        root = Path(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or home)
        return root / "Sugio Labs"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Sugio Labs"

    root = Path(os.getenv("XDG_DATA_HOME") or (home / ".local" / "share"))
    return root / "sugio-labs"


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

    # Desktop/local storage. Environment variables can override every path.
    data_dir: Path = Field(default_factory=_default_data_dir)
    database_url: str = Field(default="")
    workspace_root: str = Field(default="")

    # Source/resource root; writable files must not be stored here in packaged apps.
    base_dir: Path = Path(__file__).resolve().parent.parent

    # Security
    strict_permissions: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        self.data_dir = self.data_dir.expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if not self.database_url:
            db_path = (self.data_dir / "sugio_labs.db").as_posix()
            self.database_url = f"sqlite:///{db_path}"

        if not self.workspace_root:
            self.workspace_root = str(self.data_dir / "workspaces")

    @property
    def absolute_workspace_root(self) -> Path:
        """Return the writable workspace root used by local project tools."""
        root = Path(self.workspace_root).expanduser()
        if not root.is_absolute():
            root = (self.data_dir / root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root


settings = Settings()
