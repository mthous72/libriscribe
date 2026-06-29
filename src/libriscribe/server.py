"""LibriScribe web server — launches uvicorn and opens browser."""
from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn


def main():
    host = "127.0.0.1"
    port = 8000

    # Auto-open browser after a short delay
    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        "libriscribe.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
