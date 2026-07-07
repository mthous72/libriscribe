"""Story-seeding wizard endpoints (B38) — Q&A intake → elaborate answers → sandbox."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from libriscribe.services.project_service import load_kb, save_kb, create_utility_client

router = APIRouter(prefix="/api/projects", tags=["wizard"])


class QuestionsUpdate(BaseModel):
    questions: dict[str, str]  # question -> answer ('' = unanswered)


@router.get("/{name}/wizard/questions")
def get_questions(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"questions": kb.dynamic_questions or {}}


@router.post("/{name}/wizard/questions")
def generate_questions(name: str):
    """LLM-authors intake questions tailored to THIS project (genre/premise + existing lore),
    stores them in dynamic_questions (preserving existing answers)."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    from libriscribe.services import story_wizard

    questions = story_wizard.generate_questions(create_utility_client(kb), kb)
    save_kb(name, kb)
    return {"questions": questions}


@router.put("/{name}/wizard/questions")
def save_questions(name: str, body: QuestionsUpdate):
    """Save the author's edits/answers (add/remove/reword questions freely)."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    kb.dynamic_questions = {str(q).strip(): str(a) for q, a in body.questions.items() if str(q).strip()}
    save_kb(name, kb)
    return {"questions": kb.dynamic_questions}


@router.post("/{name}/wizard/elaborate")
def elaborate(name: str):
    """Elaborate the author's answers into typed lore candidates, staged in the sandbox
    (B27A) for cherry-pick. The answers are authoritative — the model only fills in detail."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if not any(str(a).strip() for a in (kb.dynamic_questions or {}).values()):
        raise HTTPException(status_code=400, detail="Answer at least one question first.")
    from libriscribe.services import story_wizard
    from libriscribe.utils import parallel

    run = story_wizard.elaborate(
        create_utility_client(kb), kb, name, max_workers=parallel.resolve_max_workers(kb),
    )
    if run is None:
        raise HTTPException(status_code=400, detail="The answers produced no lore candidates.")
    return run
