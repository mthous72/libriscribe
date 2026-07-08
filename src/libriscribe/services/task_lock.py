"""Per-project AI task lock — one heavy LLM task per project at a time.

Guardrail: batch operations (deep scan, wizard elaboration, state extraction, revision) and
generation each fan out up to `max_concurrency` calls. Without a lock, two started from
different pages would stack (2×4 calls into LM Studio's 4 slots) and could interleave
load_kb→save_kb writes (last-writer-wins data loss). Endpoints acquire this lock and return
409 with the running task's name when busy — the work in flight is never disturbed.

In-process only (matches the single-server deployment).
"""
from __future__ import annotations

import threading

_guard = threading.Lock()
_active: dict[str, str] = {}   # project_name -> human-readable task name


def acquire(project: str, task: str) -> bool:
    """Try to claim the project's AI slot. False (and untouched) if another task holds it."""
    with _guard:
        if project in _active:
            return False
        _active[project] = task
        return True


def release(project: str) -> None:
    with _guard:
        _active.pop(project, None)


def current(project: str) -> str | None:
    """The task currently holding the project's slot, if any."""
    with _guard:
        return _active.get(project)


def busy_detail(project: str) -> str:
    task = current(project) or "another AI task"
    return (f"'{task}' is still running for this project — wait for it to finish "
            "(or cancel it) before starting another AI task.")
