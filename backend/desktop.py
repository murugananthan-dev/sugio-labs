"""Sugio Labs Windows desktop launcher.

The application is packaged as a self-contained Windows executable. It starts
its bundled FastAPI engine on an ephemeral localhost port and opens the bundled
React application inside a native window. Runtime data is stored in the
current Windows user's local application-data directory rather than beside the
executable, so the same EXE can be copied to multiple Windows PCs.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.error
import urllib.request

import uvicorn
import webview

from app.config import settings
from app.main import app


class BackendServer(threading.Thread):
    def __init__(self, port: int) -> None:
        super().__init__(daemon=True)
        self.port = port
        self.server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        )

    def run(self) -> None:
        self.server.run()

    def stop(self) -> None:
        self.server.should_exit = True


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_until_ready(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return response.status < 500
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.15)
    return False


def run_self_test(base_url: str) -> int:
    """Verify that the packaged backend and bundled frontend are operational."""
    try:
        with urllib.request.urlopen(f"{base_url}/api/v1/health", timeout=5.0) as response:
            if response.status != 200:
                return 2
            payload = response.read().decode("utf-8", errors="replace")
            if "online" not in payload.lower() and "healthy" not in payload.lower():
                return 3

        with urllib.request.urlopen(base_url, timeout=5.0) as response:
            html = response.read(4096).decode("utf-8", errors="replace").lower()
            if response.status != 200 or "<!doctype html" not in html:
                return 4
    except Exception:
        return 5
    return 0


def main() -> int:
    # Create writable per-user runtime directories before opening the UI.
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.absolute_workspace_root.mkdir(parents=True, exist_ok=True)

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = BackendServer(port)
    server.start()

    if not wait_until_ready(base_url):
        server.stop()
        server.join(timeout=5)
        return 10

    if "--self-test" in sys.argv:
        try:
            return run_self_test(base_url)
        finally:
            server.stop()
            server.join(timeout=5)

    webview.create_window(
        "Sugio Labs",
        base_url,
        width=1440,
        height=900,
        min_size=(1050, 680),
        resizable=True,
        text_select=True,
        confirm_close=False,
    )

    try:
        # Modern Windows uses the Edge Chromium / WebView2 renderer.
        webview.start(debug=False, private_mode=False)
    finally:
        server.stop()
        server.join(timeout=5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
