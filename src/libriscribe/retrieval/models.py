from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RetrievalMode(str, Enum):
    DISABLED = "disabled"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class RetrievalBackend(str, Enum):
    LOCAL = "local"
    CHROMA = "chroma"
    MONGODB = "mongodb"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class EmbeddingProviderType(str, Enum):
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    OPENAI = "openai"


class RetrievalConfig(BaseModel):
    enabled: bool = False
    mode: RetrievalMode = RetrievalMode.DISABLED
    backend: RetrievalBackend = RetrievalBackend.LOCAL
    auto_index: bool = True
    top_k: int = 6
    max_context_tokens: int = 1800
    embedding_provider: EmbeddingProviderType = EmbeddingProviderType.SENTENCE_TRANSFORMERS
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: int = 120
    include_chapter_text: bool = True
    include_chapter_summaries: bool = True
    include_outline: bool = True
    include_characters: bool = True
    include_worldbuilding: bool = True
    include_cross_references: bool = True
    projects_subdir: str = ".libriscribe_retrieval"


class RetrievalDocument(BaseModel):
    document_id: str
    project_name: str
    source_type: str
    title: str
    text: str
    source_path: str | None = None
    chapter_number: int | None = None
    scene_number: int | None = None
    entity_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    updated_at: str
    hash: str


class RetrievalChunk(BaseModel):
    chunk_id: str
    document_id: str
    project_name: str
    text: str
    source_type: str
    chunk_index: int
    chapter_number: int | None = None
    scene_number: int | None = None
    entity_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    token_estimate: int = 0
    hash: str


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    source_type: str
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    chapter_number: int | None = None
    scene_number: int | None = None
    entity_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class CrossReferenceEntry(BaseModel):
    entity_name: str
    entity_type: str
    referenced_in_chunks: list[str] = Field(default_factory=list)
    referenced_in_chapters: list[int] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)


class RetrievalContextPack(BaseModel):
    task_type: str
    project_context: str
    query: str | None = None
    selected_results: list[SearchResult] = Field(default_factory=list)
    continuity_notes: list[str] = Field(default_factory=list)
    character_state_notes: list[str] = Field(default_factory=list)
    unresolved_threads: list[str] = Field(default_factory=list)
    token_estimate: int = 0


# ─── Shared helpers (used by both the keyword and semantic indexes) ────────────

def mode_str(mode: Any) -> str:
    """Normalize a RetrievalMode (enum or string) to a lowercase string."""
    return getattr(mode, "value", str(mode)).lower()


def matches_filters(chunk: "RetrievalChunk", filters: dict[str, Any] | None) -> bool:
    """Apply metadata filters to a chunk. Supported keys: source_type, exclude_source_type,
    chapter_number, characters. Single value or list accepted where it makes sense."""
    if not filters:
        return True

    if "source_type" in filters:
        allowed = filters["source_type"]
        if isinstance(allowed, list):
            if chunk.source_type not in allowed:
                return False
        elif chunk.source_type != allowed:
            return False

    if "exclude_source_type" in filters:
        excluded = filters["exclude_source_type"]
        if isinstance(excluded, list):
            if chunk.source_type in excluded:
                return False
        elif chunk.source_type == excluded:
            return False

    if "chapter_number" in filters:
        if chunk.chapter_number != filters["chapter_number"]:
            return False

    if "characters" in filters:
        req = filters["characters"]
        if isinstance(req, list):
            if not any(rc in chunk.characters for rc in req):
                return False
        elif req not in chunk.characters:
            return False

    return True


def chunk_to_result(chunk: "RetrievalChunk", score: float, score_type: str = "keyword") -> SearchResult:
    """Build a SearchResult from a chunk + score (shared by both index backends)."""
    return SearchResult(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        text=chunk.text,
        source_type=chunk.source_type,
        score=score,
        score_breakdown={f"{score_type}_score": score},
        chapter_number=chunk.chapter_number,
        scene_number=chunk.scene_number,
        entity_name=chunk.entity_name,
        tags=chunk.tags,
        characters=chunk.characters,
        locations=chunk.locations,
        themes=chunk.themes,
    )
