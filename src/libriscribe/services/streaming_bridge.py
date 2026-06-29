"""Bridge between sync Iterator[str] and asyncio.Queue."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any


def build_event_callback(project_name: str, ws_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Creates a thread-safe callback that pushes events to the WS queue."""

    def callback(event_type: str, payload: Any) -> None:
        msg = {
            "type": event_type,
            "project": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload if isinstance(payload, dict) else {"message": str(payload)},
        }
        loop.call_soon_threadsafe(ws_queue.put_nowait, msg)

    return callback
