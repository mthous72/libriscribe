"""LibriScribe web server.

Responsibilities (Spec #1):
- Single instance: if LibriScribe is already running on a candidate port, just open
  the browser there and exit instead of starting a duplicate.
- Port fallback: bind the first free port in 8000..8010.
- System tray (frozen builds): run uvicorn on a background thread and a tray icon on
  the main thread, with Open / Quit actions and a clean shutdown.
- Web Quit: POST /api/shutdown triggers the same clean shutdown.
- Unsaved-changes guard: the tray Quit warns (native dialog) when the UI reports
  unsaved changes; the web Quit button does its own confirm before calling shutdown.
"""
from __future__ import annotations

import ctypes
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PORT_CANDIDATES = list(range(8000, 8011))  # 8000..8010 inclusive


def _redirect_std_streams_if_needed() -> None:
    """Ensure sys.stdout/sys.stderr are real streams.

    In a windowed PyInstaller build (console=False) there is no console, so
    sys.stdout and sys.stderr are None, which breaks libraries that touch them.
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
        pass


# ─── Single-instance port selection ──────────────────────────────────────────


def _probe_health(port: int, timeout: float = 0.4) -> str | None:
    """Probe a port's /api/health.

    Returns "libriscribe" if a LibriScribe instance answers, "" if something else
    answers, or None if nothing is listening / the probe fails.
    """
    url = f"http://{HOST}:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("app") == "libriscribe":
                return "libriscribe"
            return ""
    except Exception:
        return None


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def _choose_port() -> tuple[int | None, int | None]:
    """Walk the candidate ports.

    Returns (bind_port, existing_port):
      - existing_port set -> a LibriScribe instance is already running there.
      - bind_port set     -> the first free port we should bind.
      - (None, None)      -> no existing instance and no free port in range.
    """
    for port in PORT_CANDIDATES:
        sig = _probe_health(port)
        if sig == "libriscribe":
            return (None, port)
        if sig is None and _port_is_free(port):
            return (port, None)
        # else: occupied by a non-LibriScribe service -> try the next candidate
    return (None, None)


# ─── Browser / dialogs ───────────────────────────────────────────────────────


def _open_browser(port: int) -> None:
    webbrowser.open(f"http://{HOST}:{port}")


def _update_splash(text: str) -> None:
    """Update the PyInstaller startup splash text (no-op when not frozen)."""
    try:
        import pyi_splash  # injected at runtime by the PyInstaller splash

        pyi_splash.update_text(text)
    except Exception:
        pass


def _close_splash() -> None:
    try:
        import pyi_splash

        pyi_splash.close()
    except Exception:
        pass


def _open_browser_when_ready(port: int) -> None:
    _update_splash("Loading the web server…")
    ready = False
    for _ in range(120):  # up to ~60s
        if _probe_health(port) == "libriscribe":
            ready = True
            break
        time.sleep(0.5)
    if ready:
        _update_splash("Ready — opening your browser…")
    # Always dismiss the splash before opening the browser (even on timeout).
    _close_splash()
    _open_browser(port)


def _message_box(text: str, title: str, flags: int) -> int:
    """Best-effort native message box (Windows only). Returns the button code."""
    if sys.platform == "win32":
        return ctypes.windll.user32.MessageBoxW(0, text, title, flags)
    return 0


def _confirm_quit_if_dirty() -> bool:
    """Return True if it is OK to quit.

    Tray Quit path: when the UI has reported unsaved changes, prompt (best-effort
    native dialog on Windows). Non-Windows falls through as "OK to quit".
    """
    from libriscribe import runtime

    if not runtime.get_ui_state().get("dirty"):
        return True
    # MB_YESNO (0x4) | MB_ICONWARNING (0x30) = 0x34 ; IDYES = 6
    result = _message_box(
        "You have unsaved changes in LibriScribe.\n\n"
        "Quit anyway? Unsaved work will be lost.",
        "LibriScribe — Unsaved Changes",
        0x34,
    )
    if sys.platform != "win32":
        return True
    return result == 6


# ─── Tray + shutdown ─────────────────────────────────────────────────────────


def _tray_icon_image():
    from PIL import Image

    from libriscribe.utils.paths import get_base_dir

    ico = get_base_dir() / "installer" / "libriscribe.ico"
    try:
        if ico.exists():
            return Image.open(str(ico))
    except Exception:
        pass
    # Fallback: a solid indigo square so the tray always has an icon.
    return Image.new("RGB", (64, 64), (79, 70, 229))


def _build_tray(port: int):
    import pystray

    def on_open(icon, item):
        _open_browser(port)

    def on_quit(icon, item):
        if not _confirm_quit_if_dirty():
            return
        from libriscribe import runtime

        runtime.request_shutdown()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open LibriScribe", on_open, default=True),
        pystray.MenuItem("Quit LibriScribe", on_quit),
    )
    return pystray.Icon("libriscribe", _tray_icon_image(), "LibriScribe", menu)


def _start_shutdown_watcher(server: "uvicorn.Server", icon) -> None:
    """Stop the server (and tray) when a shutdown is requested via /api/shutdown."""
    from libriscribe import runtime

    def _watch() -> None:
        runtime.shutdown_event.wait()
        server.should_exit = True
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass

    threading.Thread(target=_watch, daemon=True).start()


def serve_embedded(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the ASGI app in-process for an embedded host (e.g. Android/Chaquopy).

    This is the mobile/embedded counterpart to ``main()``: no system tray, no
    browser launch, no single-instance port probing, and it pins uvicorn to the
    pure-Python asyncio loop + h11/websockets so it doesn't need uvloop/httptools
    (which aren't available on all embedded platforms). It blocks the calling
    thread until the process is torn down, so callers run it on a worker thread.

    The host is expected to have already set ``LIBRISCRIBE_BASE_DIR`` (bundled
    assets: frontend/dist, prompts) and ``LIBRISCRIBE_DATA_DIR`` (writable
    projects/.env) — see ``libriscribe.utils.paths``.
    """
    _redirect_std_streams_if_needed()
    _seed_env_if_needed()

    config = uvicorn.Config(
        "libriscribe.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
        log_config=None,
        loop="asyncio",
        http="h11",
        ws="websockets",
    )
    uvicorn.Server(config).run()


def main() -> None:
    _redirect_std_streams_if_needed()
    _seed_env_if_needed()

    bind_port, existing_port = _choose_port()

    # Already running -> surface that instance instead of starting a duplicate.
    if existing_port is not None:
        _open_browser(existing_port)
        return

    if bind_port is None:
        msg = (
            f"LibriScribe could not find a free port in "
            f"{PORT_CANDIDATES[0]}-{PORT_CANDIDATES[-1]}."
        )
        _message_box(msg, "LibriScribe", 0x10)  # MB_ICONERROR
        print(msg, file=sys.stderr)
        return

    config = uvicorn.Config(
        "libriscribe.api.app:create_app",
        factory=True,
        host=HOST,
        port=bind_port,
        reload=False,
        log_config=None,  # no colorized formatter (windowed builds have no tty)
    )
    server = uvicorn.Server(config)

    use_tray = getattr(sys, "frozen", False) or os.environ.get("LIBRISCRIBE_TRAY") == "1"

    # Open the browser once the server is accepting requests.
    threading.Thread(
        target=_open_browser_when_ready, args=(bind_port,), daemon=True
    ).start()

    if not use_tray:
        # Dev / CLI: run on the main thread so Ctrl+C works; still honor /api/shutdown.
        _start_shutdown_watcher(server, icon=None)
        server.run()
        return

    # Frozen GUI: server on a background thread, tray on the main thread.
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    icon = _build_tray(bind_port)
    _start_shutdown_watcher(server, icon)
    icon.run()  # blocks until Quit

    server.should_exit = True
    server_thread.join(timeout=10)


if __name__ == "__main__":
    main()
