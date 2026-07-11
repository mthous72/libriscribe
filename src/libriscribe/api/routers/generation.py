"""Start/cancel/resume generation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from libriscribe.api.schemas.generation import StartGenerationRequest, ResumeRequest, JobStatus, RegenerateOutlineRequest, ResetRequest
from libriscribe.api.dependencies import get_job_manager, get_generation_service

router = APIRouter(prefix="/api/projects", tags=["generation"])


@router.post("/{name}/generate", response_model=JobStatus)
async def start_generation(name: str, req: StartGenerationRequest | None = None):
    req = req or StartGenerationRequest()
    svc = get_generation_service()
    jm = get_job_manager()

    # B45: characters/worldbuilding are no longer pipeline stages.
    if req.start_from_stage in ("characters", "worldbuilding"):
        raise HTTPException(
            status_code=400,
            detail=(f"'{req.start_from_stage}' is not a pipeline stage anymore — character and "
                    f"world work lives in the lorebook. For batch generation use "
                    f"POST /api/projects/{name}/tools/{req.start_from_stage}."))

    # Check if already running
    existing = jm.get_job(name)
    if existing and existing.status == "running":
        raise HTTPException(status_code=409, detail="Generation already in progress")
    # One AI task per project: refuse while a batch op (deep scan, wizard, ...) holds the slot.
    from libriscribe.services import task_lock
    if task_lock.current(name):
        raise HTTPException(status_code=409, detail=task_lock.busy_detail(name))

    job = await svc.start_generation(
        name,
        start_from_stage=req.start_from_stage or ("chapters" if req.chapter else ""),
        streaming=req.streaming,
        mode=req.mode,
        chapter=req.chapter,
    )
    return jm.to_status_dict(name)


@router.post("/{name}/tools/{stage}", response_model=JobStatus)
async def run_batch_tool(name: str, stage: str):
    """B45: opt-in batch generation for the demoted stages — 'characters' (cast w/ voice
    profiles; collisions stage to the sandbox per B42) and 'worldbuilding' (fill-empty-only;
    conflicts stage to the sandbox). Runs as a normal job: streaming + cancel work."""
    from libriscribe.services.generation_service import TOOL_STAGES
    if stage not in TOOL_STAGES:
        raise HTTPException(status_code=400, detail=f"Unknown tool '{stage}' — expected one of {list(TOOL_STAGES)}")
    svc = get_generation_service()
    jm = get_job_manager()
    existing = jm.get_job(name)
    if existing and existing.status == "running":
        raise HTTPException(status_code=409, detail="Generation already in progress")
    from libriscribe.services import task_lock
    if task_lock.current(name):
        raise HTTPException(status_code=409, detail=task_lock.busy_detail(name))
    await svc.run_single_stage(name, stage)
    return jm.to_status_dict(name)


@router.post("/{name}/generate/reset")
def reset_generation(name: str, req: ResetRequest):
    """Reset generation back to a stage (Phase 1 / B30): snapshots the project first, then
    clears that stage + everything downstream so the step flow re-gates there."""
    from libriscribe.services import project_service

    jm = get_job_manager()
    existing = jm.get_job(name)
    if existing and existing.status == "running":
        raise HTTPException(status_code=409, detail="Cancel the running generation before resetting")
    try:
        return project_service.reset_to_stage(name, req.to_stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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


@router.post("/{name}/develop-outline")
def develop_outline(name: str):
    """Continue the outline from where it currently is — ADDITIVE, never overwrites.

    Placeholder chapters ('summary to be developed') get a summary + scenes; chapters
    with a real summary but no scenes get scenes only; developed chapters are untouched.
    The intent-shaped counterpart to regenerate-outline (whose lock-then-regen model
    read as overwrite-by-default)."""
    from libriscribe.services.project_service import load_kb, save_kb, create_llm_client
    from libriscribe.agents.outliner import OutlinerAgent

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    buckets = OutlinerAgent.classify_development(kb)
    if not buckets["summarize"] and not buckets["scene"]:
        raise HTTPException(status_code=400, detail="The outline is already fully developed.")

    outliner = OutlinerAgent(create_llm_client(kb))
    if buckets["summarize"]:
        outliner.execute_partial(
            kb,
            locked_chapters=buckets["done"] + buckets["scene"],
            regenerate_chapters=buckets["summarize"],
        )
    for n in buckets["scene"]:
        outliner.generate_scene_outline(kb, kb.chapters[n])
    save_kb(name, kb)

    return {
        "developed": buckets["summarize"],
        "scenes_added": buckets["scene"],
        "untouched": buckets["done"],
        "chapters": [
            {"chapter_number": ch.chapter_number, "title": ch.title,
             "summary": ch.summary, "scene_count": len(ch.scenes)}
            for ch in (kb.chapters[n] for n in sorted(kb.chapters))
        ],
    }


@router.post("/{name}/chapters/{n}/develop-scenes")
def develop_scenes(name: str, n: int):
    """B45: (re)generate the scene outline for ONE chapter — validate-retry-keep-valid,
    same primitive develop-outline uses, scoped to a single chapter."""
    from libriscribe.services.project_service import load_kb, save_kb, create_llm_client
    from libriscribe.services import task_lock
    from libriscribe.agents.outliner import OutlinerAgent

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = kb.get_chapter(n)
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter {n} is not in the outline")
    if not (chapter.summary or "").strip():
        raise HTTPException(status_code=422,
                            detail=f"Chapter {n} has no summary yet — write one first (scenes are derived from it).")

    if not task_lock.acquire(name, f"Scene outline: Chapter {n}"):
        raise HTTPException(status_code=409, detail=task_lock.busy_detail(name))
    try:
        OutlinerAgent(create_llm_client(kb)).generate_scene_outline(kb, chapter)
        save_kb(name, kb)
    finally:
        task_lock.release(name)
    return {"chapter_number": n,
            "scenes": [s.model_dump() for s in sorted(chapter.scenes, key=lambda s: s.scene_number)]}


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
