"""Pipeline orchestration — runs the generation pipeline in a background thread."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from libriscribe.agents.project_manager import ProjectManagerAgent
from libriscribe.services.job_manager import JobManager, GenerationJob
from libriscribe.services.streaming_bridge import build_event_callback
from libriscribe.workflow_state import inspect_project_progress
from libriscribe.services.project_service import get_projects_dir

logger = logging.getLogger(__name__)

STAGE_ORDER = ["concept", "outline", "characters", "worldbuilding", "chapters", "formatting"]


class GenerationService:
    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    async def start_generation(
        self,
        project_name: str,
        start_from_stage: str = "",
        streaming: bool = True,
        ws_queue: asyncio.Queue | None = None,
    ) -> GenerationJob:
        loop = asyncio.get_running_loop()
        queue = ws_queue or asyncio.Queue()
        callback = build_event_callback(project_name, queue, loop)

        task = asyncio.create_task(
            self._run_pipeline(project_name, start_from_stage, streaming, queue, callback, loop)
        )
        job = self.job_manager.create_job(project_name, task, queue)
        return job

    async def _run_pipeline(
        self,
        project_name: str,
        start_from_stage: str,
        streaming: bool,
        ws_queue: asyncio.Queue,
        callback,
        loop: asyncio.AbstractEventLoop,
    ):
        try:
            pm = ProjectManagerAgent(event_callback=callback)

            # Load project
            await asyncio.to_thread(pm.load_project_data, project_name)

            # Determine LLM provider
            kb = pm.project_knowledge_base
            if not kb:
                self.job_manager.complete_job(project_name, "failed", "No project data found")
                return

            provider = kb.llm_provider or "openai"
            model = kb.model or None
            await asyncio.to_thread(pm.initialize_llm_client, provider, model)

            # Wire the threading event for human review
            job = self.job_manager.get_job(project_name)
            if job:
                pm.review_threading_event = job.review_threading_event

            # Determine which stages to run
            project_dir = get_projects_dir() / project_name
            progress = inspect_project_progress(project_dir, kb)
            stages_to_run = self._compute_stages(progress, start_from_stage, kb)

            for stage in stages_to_run:
                # Check cancellation
                if job and job.cancel_event.is_set():
                    self.job_manager.complete_job(project_name, "cancelled")
                    return

                if job:
                    job.current_stage = stage

                await self._run_stage(pm, stage, kb, streaming, job)

            self.job_manager.complete_job(project_name, "completed", "Generation complete")

            # Emit completion event
            callback("generation_complete", {
                "stages_completed": stages_to_run,
                "total_cost": 0,
            })

        except asyncio.CancelledError:
            self.job_manager.complete_job(project_name, "cancelled")
        except Exception as e:
            logger.exception(f"Pipeline error for {project_name}: {e}")
            self.job_manager.complete_job(project_name, "failed", str(e))
            callback("error", {"stage": "pipeline", "message": str(e), "recoverable": False})

    def _compute_stages(self, progress, start_from_stage: str, kb) -> list[str]:
        """Figures out which stages need to run."""
        if start_from_stage and start_from_stage in STAGE_ORDER:
            idx = STAGE_ORDER.index(start_from_stage)
            return STAGE_ORDER[idx:]

        stages = []
        if not progress.concept_complete:
            stages.append("concept")
        if not progress.outline_complete:
            stages.append("outline")
        if progress.characters_required and not progress.characters_complete:
            stages.append("characters")
        if progress.worldbuilding_required and not progress.worldbuilding_complete:
            stages.append("worldbuilding")
        if progress.missing_chapters:
            stages.append("chapters")
        if not progress.manuscript_exists:
            stages.append("formatting")
        return stages

    async def _run_stage(self, pm: ProjectManagerAgent, stage: str, kb, streaming: bool, job: GenerationJob | None):
        if stage == "concept":
            await asyncio.to_thread(pm.generate_concept)
        elif stage == "outline":
            await asyncio.to_thread(pm.generate_outline)
        elif stage == "characters":
            await asyncio.to_thread(pm.generate_characters)
        elif stage == "worldbuilding":
            await asyncio.to_thread(pm.generate_worldbuilding)
        elif stage == "chapters":
            await self._run_chapters(pm, kb, streaming, job)
        elif stage == "formatting":
            project_dir = pm.project_dir
            if project_dir:
                output_path = str(project_dir / "manuscript.md")
                await asyncio.to_thread(pm.format_book, output_path)

    async def _run_chapters(self, pm: ProjectManagerAgent, kb, streaming: bool, job: GenerationJob | None):
        total_chapters = kb.num_chapters
        if isinstance(total_chapters, tuple):
            total_chapters = total_chapters[1]
        if not isinstance(total_chapters, int) or total_chapters < 1:
            total_chapters = 1

        for chapter_num in range(1, total_chapters + 1):
            if job and job.cancel_event.is_set():
                return

            if pm.does_chapter_exist(chapter_num):
                continue

            if job:
                job.current_chapter = chapter_num

            # During human review, the PM's write_and_review_chapter will block
            # on review_threading_event internally. We update job status via callback.
            if kb.review_preference == "Human":
                # The PM will emit human_review_required and block
                # We update job status when we detect the event
                original_callback = pm.event_callback

                def review_aware_callback(event_type, payload, _orig=original_callback, _job=job):
                    if event_type == "human_review_required" and _job:
                        _job.status = "paused_for_review"
                    _orig(event_type, payload)

                pm.event_callback = review_aware_callback
                # Also ensure the review decision flows back
                def _sync_review_decision():
                    if job:
                        pm.review_decision = job.review_decision

                pm.review_threading_event = job.review_threading_event if job else pm.review_threading_event

            await asyncio.to_thread(pm.write_and_review_chapter, chapter_num, streaming)
