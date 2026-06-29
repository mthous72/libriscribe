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


def _seed_env_if_needed() -> None:
    """On first run of a frozen build, seed the user's .env from the bundled
    .env.example so the in-app Settings page has a file to update. The installer
    can't do this: a per-machine (admin) install resolves %LOCALAPPDATA% to the
    admin's profile, not the user who later runs the app.
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        from libriscribe.utils.paths import (
            get_default_env_path,
            get_bundled_env_example,
        )

        env_path = get_default_env_path()
        if env_path.exists():
            return
        example = get_bundled_env_example()
        contents = example.read_text(encoding="utf-8") if example.exists() else ""
        env_path.write_text(contents, encoding="utf-8")
    except Exception:
        # Seeding is best-effort; the app falls back to built-in defaults and the
        # Settings page recreates the file when the user saves a key.
        pass


def main():
    _redirect_std_streams_if_needed()
    _seed_env_if_needed()

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
