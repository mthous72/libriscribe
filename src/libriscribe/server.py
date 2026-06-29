"""LibriScribe web server — launches uvicorn and opens browser."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


def _redirect_std_streams_if_needed() -> None:
    """Ensure sys.stdout/sys.stderr are real streams.

    In a windowed PyInstaller build (console=False) there is no console, so
    sys.stdout and sys.stderr are None. uvicorn's colorized log formatter calls
    sys.stdout.isatty() during startup, which raises AttributeError on None.
    Point the missing streams at a log file in a user-writable location
    (Program Files is read-only for standard users), falling back to os.devnull.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return

    stream = None
    try:
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        log_dir = Path(base) / "LibriScribe"
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = open(log_dir / "libriscribe.log", "a", buffering=1, encoding="utf-8")
    except Exception:
        try:
            stream = open(os.devnull, "w")
        except Exception:
            stream = None

    if stream is not None:
        if sys.stdout is None:
            sys.stdout = stream
        if sys.stderr is None:
            sys.stderr = stream


def main():
    _redirect_std_streams_if_needed()

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
