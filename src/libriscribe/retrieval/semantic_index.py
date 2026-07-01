"""Semantic (embeddings) vector index for retrieval (B17).

Stores a unit-normalized embedding per chunk and ranks by cosine similarity. Kept in-process
and persisted to disk as JSON — no external vector DB, consistent with the project's local-
first design. Uses numpy for the similarity matmul when available and falls back to pure
Python otherwise (project-scale corpora are small: a book + a few references).

The stored `signature` records which embedding space produced the vectors; if it no longer
matches the active embedder (model/endpoint changed), the index is treated as not-ready and
callers fall back to keyword until it is rebuilt.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

from libriscribe.retrieval.models import RetrievalChunk, SearchResult, matches_filters, chunk_to_result

try:
    import numpy as _np
    _HAS_NUMPY = True
except Exception:  # pragma: no cover - numpy may be absent
    _np = None
    _HAS_NUMPY = False


def _searchable_text(chunk: RetrievalChunk) -> str:
    """Text to embed for a chunk. Lightly prepend the entity name for grounding."""
    if chunk.entity_name:
        return f"{chunk.entity_name}: {chunk.text}"
    return chunk.text


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class SemanticIndex:
    """Cosine-similarity vector index over chunk embeddings."""

    def __init__(self):
        self.chunks_map: Dict[str, RetrievalChunk] = {}
        self.ids: List[str] = []
        self.vectors: List[List[float]] = []  # unit-normalized
        self.signature: str = ""
        self._matrix = None  # numpy matrix when available

    # ── build / persistence ───────────────────────────────────────────────
    def build(self, chunks: List[RetrievalChunk], embedder) -> None:
        """Embed all chunks. Raises EmbedderError on embedding failure (caller decides)."""
        ids: List[str] = []
        texts: List[str] = []
        self.chunks_map = {}
        for c in chunks:
            self.chunks_map[c.chunk_id] = c
            ids.append(c.chunk_id)
            texts.append(_searchable_text(c))
        raw = embedder.embed(texts) if texts else []
        self.ids = ids
        self.vectors = [_normalize(v) for v in raw]
        self.signature = getattr(embedder, "signature", "")
        self._build_matrix()

    def _build_matrix(self) -> None:
        if _HAS_NUMPY and self.vectors:
            self._matrix = _np.array(self.vectors, dtype="float32")
        else:
            self._matrix = None

    def save_to_file(self, file_path: Path) -> None:
        data = {
            "signature": self.signature,
            "ids": self.ids,
            "vectors": self.vectors,
            "chunks": [self.chunks_map[i].model_dump(mode="json") for i in self.ids if i in self.chunks_map],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load_from_file(self, file_path: Path) -> None:
        if not Path(file_path).exists():
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        self.signature = data.get("signature", "")
        self.ids = list(data.get("ids", []))
        self.vectors = [list(v) for v in data.get("vectors", [])]
        self.chunks_map = {c["chunk_id"]: RetrievalChunk.model_validate(c) for c in data.get("chunks", [])}
        self._build_matrix()

    # ── query ─────────────────────────────────────────────────────────────
    def is_ready(self, embedder=None) -> bool:
        if not self.ids or not self.vectors:
            return False
        if embedder is not None and self.signature and getattr(embedder, "signature", "") != self.signature:
            return False
        return True

    def _scores(self, qn: List[float]) -> List[float]:
        if _HAS_NUMPY and self._matrix is not None:
            q = _np.array(qn, dtype="float32")
            return (self._matrix @ q).tolist()
        return [sum(a * b for a, b in zip(vec, qn)) for vec in self.vectors]

    def search(self, query: str, embedder, top_k: int = 6, filters: Dict[str, Any] | None = None) -> List[SearchResult]:
        if not self.is_ready(embedder):
            return []
        try:
            qv = embedder.embed([query])
        except Exception:
            return []
        if not qv:
            return []
        qn = _normalize(qv[0])
        scores = self._scores(qn)
        order = sorted(range(len(self.ids)), key=lambda i: scores[i], reverse=True)
        results: List[SearchResult] = []
        for i in order:
            chunk = self.chunks_map.get(self.ids[i])
            if not chunk or not matches_filters(chunk, filters):
                continue
            results.append(chunk_to_result(chunk, float(scores[i]), "semantic"))
            if len(results) >= top_k:
                break
        return results
