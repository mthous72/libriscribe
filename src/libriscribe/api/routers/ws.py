"""WebSocket endpoint for real-time generation events."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from libriscribe.api.dependencies import get_job_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{project_name}")
async def websocket_endpoint(websocket: WebSocket, project_name: str):
    await websocket.accept()

    jm = get_job_manager()

    # Send connected message
    await websocket.send_json({
        "type": "connected",
        "project": project_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "current_status": "idle",
            "current_stage": None,
        },
    })

    # Start tasks to read from job queue and client messages
    read_task = asyncio.create_task(_read_client_messages(websocket, project_name, jm))
    write_task = asyncio.create_task(_write_events(websocket, project_name, jm))

    try:
        done, pending = await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pass


async def _read_client_messages(websocket: WebSocket, project_name: str, jm):
    """Reads messages from the client and handles actions."""
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            action = msg.get("action", "")

            if action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "project": project_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {},
                })

            elif action == "review_decision":
                decision = {
                    "proceed": msg.get("proceed", True),
                    "apply_ai_style": msg.get("apply_ai_style", False),
                }
                jm.submit_review_decision(project_name, decision)

            elif action == "cancel":
                jm.cancel_job(project_name)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS read error for {project_name}: {e}")


async def _write_events(websocket: WebSocket, project_name: str, jm):
    """Reads events from the job queue and sends them to the client."""
    try:
        while True:
            job = jm.get_job(project_name)
            if job:
                try:
                    msg = await asyncio.wait_for(job.ws_queue.get(), timeout=1.0)
                    await websocket.send_json(msg)
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS write error for {project_name}: {e}")
