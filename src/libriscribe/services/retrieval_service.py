"""Shared retrieval orchestration helpers.

Centralizes three patterns that were duplicated across routers: resolving a project's
retrieval config (with an enabled default), constructing a SearchService for a project, and
rebuilding the index (keyword + semantic when an embedder is configured).
"""
from __future__ import annotations

from pathlib import Path

from libriscribe.retrieval.models import RetrievalConfig


def get_retrieval_config(kb, mode: str = "keyword") -> RetrievalConfig:
    """The project's retrieval config, or an enabled default in the given mode."""
    if kb.retrieval and kb.retrieval.enabled:
        return kb.retrieval
    return RetrievalConfig(enabled=True, mode=mode)


def search_service_for(project_dir: Path, kb, mode: str = "keyword"):
    """Construct a SearchServiceImpl for a project using its retrieval config."""
    from libriscribe.retrieval.search_service import SearchServiceImpl

    return SearchServiceImpl(project_dir, get_retrieval_config(kb, mode))


def rebuild_project_index(kb, project_dir: Path) -> None:
    """Rebuild the retrieval index so config/reference changes take effect. Best-effort:
    the keyword index always rebuilds; semantic embedding failures are handled internally."""
    from libriscribe.retrieval.index_manager import IndexManager
    from libriscribe.retrieval.embedder import build_embedder
    from libriscribe.settings import Settings

    cfg = kb.retrieval or RetrievalConfig()
    IndexManager(kb, project_dir, cfg, embedder=build_embedder(Settings())).rebuild_index()
