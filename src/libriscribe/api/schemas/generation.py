from __future__ import annotations

from pydantic import BaseModel, Field


class StartGenerationRequest(BaseModel):
    start_from_stage: str = ""
    streaming: bool = True


class ResumeRequest(BaseModel):
    proceed: bool = True
    apply_ai_style: bool = False


class RegenerateOutlineRequest(BaseModel):
    locked_chapters: list[int] = Field(default_factory=list)
    regenerate_chapters: list[int] = Field(default_factory=list)


class JobStatus(BaseModel):
    project_name: str
    status: str = "idle"
    current_stage: str | None = None
    current_chapter: int | None = None
    started_at: str | None = None
    message: str = ""
