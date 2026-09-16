"""Sugio Labs cross-platform desktop launcher.

Starts the local FastAPI engine on an ephemeral localhost port and opens the
bundled React application inside a native pywebview window. The same launcher
is packaged separately for Windows, macOS, and Linux.
"""

from __future__ import annotations

import platform
import socket
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


def main() -> None:
    # Force creation of writable per-user runtime directories before opening UI.
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.absolute_workspace_root.mkdir(parents=True, exist_ok=True)

    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = BackendServer(port)
    server.start()

    if not wait_until_ready(base_url):
        server.stop()
        raise RuntimeError("Sugio Labs local engine could not start.")

    system = platform.system()
    title = "Sugio Labs"
    if system not in {"Windows", "Darwin", "Linux"}:
        title = f"Sugio Labs ({system})"

    webview.create_window(
        title,
        base_url,
        width=1440,
        height=900,
        min_size=(1050, 680),
        resizable=True,
        text_select=True,
        confirm_close=False,
    )

    try:
        # pywebview selects the native renderer for each platform:
        # WebView2 on Windows, WKWebView on macOS, and Qt/GTK on Linux.
        webview.start(debug=False, private_mode=False)
    finally:
        server.stop()
        server.join(timeout=5)


if __name__ == "__main__":
    main()
