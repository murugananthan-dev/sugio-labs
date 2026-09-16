"""Run Sugio Labs backend and frontend together for local development."""

from __future__ import annotations

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def require(command: str, install_hint: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Missing '{command}'. {install_hint}")


def main() -> int:
    require("uv", "Install uv from https://docs.astral.sh/uv/.")
    require("npm", "Install Node.js 18+ (Node 20 recommended).")

    backend = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT / "backend",
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1"],
        cwd=ROOT / "frontend",
    )
    processes = [backend, frontend]

    def stop(*_args) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.time() + 4
        for process in processes:
            while process.poll() is None and time.time() < deadline:
                time.sleep(0.1)
            if process.poll() is None:
                process.kill()

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)

    print("\nSugio Labs is starting:")
    print("  App:     http://127.0.0.1:5173")
    print("  API:     http://127.0.0.1:8000")
    print("  API docs http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to stop both services.\n")

    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    finally:
        stop()

    failed = [process.returncode for process in processes if process.returncode not in (0, -signal.SIGTERM if hasattr(signal, "SIGTERM") else 0)]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
