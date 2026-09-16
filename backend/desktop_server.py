"""Sugio Labs desktop engine sidecar.

This entry point is packaged into a hidden Windows executable and launched by
the Electron desktop shell. It serves the bundled React UI, REST API, and
WebSocket endpoint locally on 127.0.0.1 only.
"""

from __future__ import annotations

import argparse

import uvicorn

from app.config import settings
from app.main import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.absolute_workspace_root.mkdir(parents=True, exist_ok=True)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
