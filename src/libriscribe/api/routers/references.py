"""Reference material endpoints (B19) — upload / list / delete external source documents.

Uploaded references are extracted, stored under the project's ``references/`` folder, and the
retrieval index is rebuilt so they become searchable (as a distinct ``reference`` source that
never enters the lorebook). Grounding of brainstorm/generation in references happens in the
chat router and context builder.
"""
from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException, UploadFile, File

from libriscribe.services import project_service, reference_service

router = APIRouter(prefix="/api/projects", tags=["references"])
logger = logging.getLogger(__name__)


def _reindex(name: str, kb) -> None:
    """Rebuild the retrieval index so reference changes take effect."""
    from libriscribe.services.retrieval_service import rebuild_project_index

    project_dir = project_service.get_projects_dir() / name
    try:
        rebuild_project_index(kb, project_dir)
    except Exception:
        logger.warning("Reference reindex failed for %s", name, exc_info=True)


def _process_and_reindex(name: str, project_dir, ref_id: str, filename: str, raw: bytes) -> None:
    """Background worker: extract text (with OCR) then rebuild the index if it succeeded."""
    if reference_service.finalize(project_dir, ref_id, filename, raw):
        kb = project_service.load_kb(name)
        if kb:
            _reindex(name, kb)


@router.get("/{name}/references")
def list_refs(name: str):
    kb = project_service.load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    status = {"ocr_available": reference_service.ocr_available()}
    return {"references": reference_service.list_references(project_service.get_projects_dir() / name), **status}


@router.post("/{name}/references")
async def upload_ref(name: str, file: UploadFile = File(...)):
    kb = project_service.load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    project_dir = project_service.get_projects_dir() / name
    filename = file.filename or "reference.txt"
    # Register immediately, then extract (possibly slow OCR) in the background so the upload
    # request returns right away. The References tab polls until status flips to ready/error.
    entry = reference_service.register_pending(project_dir, filename, raw)
    threading.Thread(
        target=_process_and_reindex,
        args=(name, project_dir, entry["id"], filename, raw),
        daemon=True,
    ).start()
    return entry


@router.delete("/{name}/references/{ref_id}", status_code=204)
def delete_ref(name: str, ref_id: str):
    kb = project_service.load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    project_dir = project_service.get_projects_dir() / name
    if not reference_service.delete_reference(project_dir, ref_id):
        raise HTTPException(status_code=404, detail="Reference not found")
    _reindex(name, kb)
