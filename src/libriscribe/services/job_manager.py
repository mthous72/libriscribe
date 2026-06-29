"""Per-project job state and cancellation."""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class GenerationJob:
    project_name: str
    task: asyncio.Task | None = None
    status: str = "idle"  # idle|running|paused_for_review|completed|failed|cancelled
    current_stage: str | None = None
    current_chapter: int | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    review_threading_event: threading.Event = field(default_factory=threading.Event)
    review_decision: dict | None = None
    ws_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""


class JobManager:
    """Manages one active job per project."""

    def __init__(self):
        self._jobs: dict[str, GenerationJob] = {}

    def get_job(self, project_name: str) -> GenerationJob | None:
        return self._jobs.get(project_name)

    def create_job(self, project_name: str, task: asyncio.Task, ws_queue: asyncio.Queue) -> GenerationJob:
        # Cancel existing job if present
        existing = self._jobs.get(project_name)
        if existing and existing.task and not existing.task.done():
            existing.cancel_event.set()
            existing.task.cancel()

        job = GenerationJob(
            project_name=project_name,
            task=task,
            status="running",
            ws_queue=ws_queue,
        )
        self._jobs[project_name] = job
        return job

    def cancel_job(self, project_name: str) -> GenerationJob | None:
        job = self._jobs.get(project_name)
        if job and job.task and not job.task.done():
            job.cancel_event.set()
            job.review_threading_event.set()  # Unblock review waits
            job.task.cancel()
            job.status = "cancelled"
        return job

    def complete_job(self, project_name: str, status: str = "completed", message: str = "") -> None:
        job = self._jobs.get(project_name)
        if job:
            job.status = status
            job.message = message

    def submit_review_decision(self, project_name: str, decision: dict) -> GenerationJob | None:
        job = self._jobs.get(project_name)
        if job and job.status == "paused_for_review":
            job.review_decision = decision
            job.review_threading_event.set()
            job.status = "running"
        return job

    def to_status_dict(self, project_name: str) -> dict[str, Any]:
        job = self._jobs.get(project_name)
        if not job:
            return {
                "project_name": project_name,
                "status": "idle",
                "current_stage": None,
                "current_chapter": None,
                "started_at": None,
                "message": "",
            }
        return {
            "project_name": job.project_name,
            "status": job.status,
            "current_stage": job.current_stage,
            "current_chapter": job.current_chapter,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "message": job.message,
        }
