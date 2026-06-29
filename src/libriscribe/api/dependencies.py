"""Shared dependency injection for FastAPI."""
from __future__ import annotations

from functools import lru_cache

from libriscribe.services.job_manager import JobManager
from libriscribe.services.generation_service import GenerationService
from libriscribe.settings import Settings


@lru_cache()
def get_settings() -> Settings:
    return Settings()


_job_manager: JobManager | None = None
_generation_service: GenerationService | None = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def get_generation_service() -> GenerationService:
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService(get_job_manager())
    return _generation_service
