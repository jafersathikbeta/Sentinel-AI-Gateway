"""PyWebView + Uvicorn desktop launcher for Sentinel AI Gateway."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview

# Ensure project root is on sys.path for `core` / `src` imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def start_server() -> None:
    uvicorn.run(
        "src.api:app",
        host=HOST,
        port=PORT,
        log_level="info",
        reload=False,
    )


def wait_for_server(timeout: float = 30.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> None:
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    if not wait_for_server():
        print(f"Failed to start server at {URL}", file=sys.stderr)
        sys.exit(1)

    print(f"Sentinel AI Gateway is built and running at {URL}")
    window = webview.create_window(
        "Sentinel AI Gateway",
        URL,
        width=1280,
        height=800,
        min_size=(960, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
