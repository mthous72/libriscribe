"""Start/cancel/resume generation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from libriscribe.api.schemas.generation import StartGenerationRequest, ResumeRequest, JobStatus, RegenerateOutlineRequest
from libriscribe.api.dependencies import get_job_manager, get_generation_service

router = APIRouter(prefix="/api/projects", tags=["generation"])


@router.post("/{name}/generate", response_model=JobStatus)
async def start_generation(name: str, req: StartGenerationRequest | None = None):
    req = req or StartGenerationRequest()
    svc = get_generation_service()
    jm = get_job_manager()

    # Check if already running
    existing = jm.get_job(name)
    if existing and existing.status == "running":
        raise HTTPException(status_code=409, detail="Generation already in progress")

    job = await svc.start_generation(
        name,
        start_from_stage=req.start_from_stage,
        streaming=req.streaming,
    )
    return jm.to_status_dict(name)


@router.post("/{name}/generate/cancel", response_model=JobStatus)
def cancel_generation(name: str):
    jm = get_job_manager()
    job = jm.cancel_job(name)
    if not job:
        raise HTTPException(status_code=404, detail="No active job for this project")
    return jm.to_status_dict(name)


@router.post("/{name}/generate/resume", response_model=JobStatus)
def resume_generation(name: str, req: ResumeRequest):
    jm = get_job_manager()
    job = jm.get_job(name)
    if not job or job.status != "paused_for_review":
        raise HTTPException(status_code=409, detail="No paused job to resume")

    decision = {"proceed": req.proceed, "apply_ai_style": req.apply_ai_style}
    jm.submit_review_decision(name, decision)
    return jm.to_status_dict(name)


@router.get("/{name}/jobs/current", response_model=JobStatus)
def get_current_job(name: str):
    jm = get_job_manager()
    return jm.to_status_dict(name)


@router.post("/{name}/regenerate-outline")
def regenerate_outline(name: str, req: RegenerateOutlineRequest):
    """Regenerates specific chapters' outlines while keeping others locked."""
    from libriscribe.services.project_service import load_kb, save_kb, create_llm_client
    from libriscribe.agents.outliner import OutlinerAgent

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    if not req.regenerate_chapters:
        raise HTTPException(status_code=400, detail="No chapters specified for regeneration")

    llm_client = create_llm_client(kb)

    outliner = OutlinerAgent(llm_client)
    outliner.execute_partial(kb, req.locked_chapters, req.regenerate_chapters)
    save_kb(name, kb)

    # Return updated outline info
    chapters_data = []
    for ch_num in sorted(kb.chapters.keys()):
        ch = kb.chapters[ch_num]
        chapters_data.append({
            "chapter_number": ch.chapter_number,
            "title": ch.title,
            "summary": ch.summary,
            "scene_count": len(ch.scenes),
        })
    return {"chapters": chapters_data}
