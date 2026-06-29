"""Process-level runtime controls shared between the API layer and server.py.

Holds the shutdown signal and the lightweight UI state (the dirty flag) that both
the system-tray Quit action and the web Quit button consult before stopping the
server. Kept deliberately tiny and dependency-free so both layers can import it.
"""
from __future__ import annotations

import threading
from typing import Any

# Set by an HTTP shutdown request (POST /api/shutdown) or the tray Quit action;
# watched by server.py, which stops the uvicorn server when it fires.
shutdown_event = threading.Event()

_lock = threading.Lock()
_ui_state: dict[str, Any] = {
    "dirty": False,
    "active_generation": False,
}


def set_ui_state(
    *, dirty: bool | None = None, active_generation: bool | None = None
) -> dict[str, Any]:
    """Update and return the in-memory UI state. Only provided fields change."""
    with _lock:
        if dirty is not None:
            _ui_state["dirty"] = bool(dirty)
        if active_generation is not None:
            _ui_state["active_generation"] = bool(active_generation)
        return dict(_ui_state)


def get_ui_state() -> dict[str, Any]:
    with _lock:
        return dict(_ui_state)


def request_shutdown() -> None:
    """Signal the server to shut down cleanly."""
    shutdown_event.set()
