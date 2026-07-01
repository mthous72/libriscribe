"""Reference material endpoints (B19) — upload / list / delete external source documents.

Uploaded references are extracted, stored under the project's ``references/`` folder, and the
retrieval index is rebuilt so they become searchable (as a distinct ``reference`` source that
never enters the lorebook). Grounding of brainstorm/generation in references happens in the
chat router and context builder.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File

from libriscribe.services import project_service, reference_service

router = APIRouter(prefix="/api/projects", tags=["references"])


def _reindex(name: str, kb) -> None:
    """Rebuild the retrieval index so reference changes take effect."""
    from libriscribe.retrieval.models import RetrievalConfig
    from libriscribe.retrieval.embedder import build_embedder
    from libriscribe.retrieval.index_manager import IndexManager
    from libriscribe.settings import Settings

    project_dir = project_service.get_projects_dir() / name
    cfg = kb.retrieval or RetrievalConfig()
    try:
        IndexManager(kb, project_dir, cfg, embedder=build_embedder(Settings())).rebuild_index()
    except Exception:
        pass  # keyword index always rebuilds; semantic failures handled internally


@router.get("/{name}/references")
def list_refs(name: str):
    kb = project_service.load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return reference_service.list_references(project_service.get_projects_dir() / name)


@router.post("/{name}/references")
async def upload_ref(name: str, file: UploadFile = File(...)):
    kb = project_service.load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    project_dir = project_service.get_projects_dir() / name
    try:
        entry = reference_service.add_reference(project_dir, file.filename or "reference.txt", raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _reindex(name, kb)
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
