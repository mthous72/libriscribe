# src/libriscribe/retrieval/search_service.py

from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from libriscribe.retrieval.models import SearchResult, CrossReferenceEntry, RetrievalConfig, mode_str


@runtime_checkable
class SearchService(Protocol):
    def search(
        self,
        query: str,
        *,
        mode: str,
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
        task_type: str | None = None,
    ) -> list[SearchResult]:
        """Performs a search over the index."""
        ...

    def search_cross_references(
        self,
        entity_name: str,
        *,
        entity_type: str | None = None,
    ) -> CrossReferenceEntry | None:
        """Looks up an entity in the cross-reference index."""
        ...


class NullSearchService:
    """A no-op search service used when retrieval is disabled or fails to initialize."""

    def search(
        self,
        query: str,
        *,
        mode: str,
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
        task_type: str | None = None,
    ) -> list[SearchResult]:
        return []

    def search_cross_references(
        self,
        entity_name: str,
        *,
        entity_type: str | None = None,
    ) -> CrossReferenceEntry | None:
        return None


def _merge_hybrid(keyword_results, semantic_results, top_k: int) -> list[SearchResult]:
    """Combine keyword + semantic hits: min-max normalize each list's scores to [0,1],
    sum per chunk (keeping the richer result object), and re-rank."""
    def normalized(results):
        if not results:
            return {}
        scores = [r.score for r in results]
        lo, hi = min(scores), max(scores)
        span = (hi - lo) or 1.0
        return {r.chunk_id: (r, (r.score - lo) / span) for r in results}

    kw = normalized(keyword_results)
    sem = normalized(semantic_results)
    merged: dict[str, SearchResult] = {}
    for chunk_id in set(kw) | set(sem):
        base = (sem[chunk_id][0] if chunk_id in sem else kw[chunk_id][0]).model_copy(deep=True)
        ks = kw.get(chunk_id, (None, 0.0))[1]
        ss = sem.get(chunk_id, (None, 0.0))[1]
        base.score = ks + ss
        base.score_breakdown = {"keyword_norm": ks, "semantic_norm": ss}
        merged[chunk_id] = base
    ranked = sorted(merged.values(), key=lambda r: r.score, reverse=True)
    return ranked[:top_k]


class SearchServiceImpl:
    """Core local search engine orchestrating keyword, semantic, and cross-reference queries."""

    def __init__(self, project_dir: Path, config: RetrievalConfig):
        self.project_dir = project_dir
        self.config = config

        # Delayed imports to avoid loading index manager during module import phase
        from libriscribe.retrieval.index_manager import IndexManager
        from libriscribe.retrieval.embedder import build_embedder
        from libriscribe.knowledge_base import ProjectKnowledgeBase

        # Let's read from the project_data.json if present
        project_data_path = project_dir / "project_data.json"
        if project_data_path.exists():
            kb = ProjectKnowledgeBase.load_from_file(str(project_data_path))
        else:
            kb = ProjectKnowledgeBase(project_name=project_dir.name)

        # Best-effort embedder (only used for semantic/hybrid modes); None -> keyword only.
        self.embedder = None
        if mode_str(config.mode) in ("semantic", "hybrid"):
            try:
                from libriscribe.settings import Settings
                self.embedder = build_embedder(Settings())
            except Exception:
                self.embedder = None

        self.index_manager = IndexManager(kb, project_dir, config, embedder=self.embedder)
        self.index_manager.load_indexes()

    def _effective_mode(self, requested: str | None) -> str:
        """The project's configured mode wins for semantic/hybrid; otherwise honor the
        requested mode (callers historically pass 'keyword')."""
        cfg = mode_str(self.config.mode)
        if cfg in ("semantic", "hybrid"):
            return cfg
        return (requested or cfg or "keyword").lower()

    def _semantic_ready(self) -> bool:
        return self.embedder is not None and self.index_manager.semantic_index.is_ready(self.embedder)

    def search(
        self,
        query: str,
        *,
        mode: str,
        top_k: int = 6,
        filters: dict[str, Any] | None = None,
        task_type: str | None = None,
    ) -> list[SearchResult]:
        """Search via keyword, semantic, or hybrid — resolved from the project's retrieval
        config. Semantic/hybrid silently fall back to keyword if no embedder/index is ready."""
        keyword = self.index_manager.keyword_index

        effective = self._effective_mode(mode)
        if effective in ("semantic", "hybrid") and not self._semantic_ready():
            effective = "keyword"

        if effective == "semantic":
            return self.index_manager.semantic_index.search(query, self.embedder, top_k=top_k, filters=filters)

        if effective == "hybrid":
            kw = keyword.search(query, top_k=max(top_k * 2, top_k), filters=filters)
            sem = self.index_manager.semantic_index.search(query, self.embedder, top_k=max(top_k * 2, top_k), filters=filters)
            return _merge_hybrid(kw, sem, top_k)

        return keyword.search(query, top_k=top_k, filters=filters)

    def search_cross_references(
        self,
        entity_name: str,
        *,
        entity_type: str | None = None,
    ) -> CrossReferenceEntry | None:
        """Looks up cross-reference entry of an entity."""
        entry = self.index_manager.xref_index.lookup(entity_name)
        if entry and entity_type:
            if entry.entity_type != entity_type:
                return None
        return entry
