from __future__ import annotations

from pydantic import BaseModel, Field


class StartGenerationRequest(BaseModel):
    start_from_stage: str = ""
    streaming: bool = True
    mode: str = ""  # '' = use the project's generation_mode; 'step' | 'auto' override
    chapter: int | None = None  # write THIS chapter (even if it exists = regenerate); step-oriented


class ResetRequest(BaseModel):
    to_stage: str  # concept | outline | characters | worldbuilding | chapters | formatting


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
