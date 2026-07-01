"""OpenAI-compatible embeddings for semantic retrieval (B17).

One code path serves either a **cloud** provider (OpenAI `text-embedding-3-small`) or a
**local** server (LM Studio / Ollama / llama.cpp via `base_url`), so embeddings can be fully
offline and private. If no embedder is configured or the endpoint is unreachable, callers
fall back to keyword search — semantic retrieval never hard-fails.

The `signature` string identifies the embedding space (provider + base_url + model). It is
persisted with the vector index so a config change (different model/endpoint) is detected and
the stale semantic index is ignored until it is rebuilt.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class EmbedderError(RuntimeError):
    """Raised when an embedding request fails (network, auth, bad model, …)."""


@runtime_checkable
class Embedder(Protocol):
    signature: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAICompatibleEmbedder:
    """Embeds via any OpenAI-compatible `/v1/embeddings` endpoint (cloud or local)."""

    def __init__(self, api_key: str, base_url: str | None, model: str, batch_size: int = 64):
        self.model = model
        self.base_url = base_url or ""
        self.batch_size = batch_size
        self._api_key = api_key or "not-needed"
        self.signature = f"openai-compat|{self.base_url or 'cloud'}|{model}"
        self._client = None

    def _client_or_build(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except Exception as exc:  # pragma: no cover - openai is a hard dep of the app
                raise EmbedderError(f"openai SDK unavailable: {exc}") from exc
            kwargs = {"api_key": self._api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._client_or_build()
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t if (t and t.strip()) else " " for t in texts[i:i + self.batch_size]]
            try:
                resp = client.embeddings.create(model=self.model, input=batch)
            except Exception as exc:
                raise EmbedderError(str(exc)) from exc
            # SDK returns items in input order; be defensive and sort by index if present.
            data = list(resp.data)
            try:
                data.sort(key=lambda d: getattr(d, "index", 0))
            except Exception:
                pass
            out.extend([list(d.embedding) for d in data])
        return out


# Embedding model to assume for a local server when the config still holds the legacy
# sentence-transformers default (which is not a server model name).
_LEGACY_ST_DEFAULT = "all-minilm-l6-v2"
_LOCAL_FALLBACK_MODEL = "nomic-embed-text"


def build_embedder(settings) -> Embedder | None:
    """Construct an embedder from Settings, or None if none is configured.

    Driven by `settings.retrieval_embedding_provider`:
    - "openai" / "openai-compatible" / "cloud" -> OpenAI cloud embeddings (needs openai_api_key)
    - "local" / "lmstudio" / "ollama"          -> local OpenAI-compatible server (base_url)
    Anything else (incl. the legacy "sentence-transformers") -> None (keyword only).
    """
    provider = (getattr(settings, "retrieval_embedding_provider", "") or "").strip().lower()

    if provider in ("openai", "openai-compatible", "cloud"):
        key = getattr(settings, "openai_api_key", "") or ""
        if not key:
            return None
        model = getattr(settings, "openai_embedding_model", "") or "text-embedding-3-small"
        return OpenAICompatibleEmbedder(key, None, model)

    if provider in ("local", "lmstudio", "ollama", "openai_local"):
        from libriscribe.utils.model_routing import normalize_openai_base_url

        base = normalize_openai_base_url(getattr(settings, "local_base_url", "") or "")
        if not base:
            return None
        model = (getattr(settings, "retrieval_embedding_model", "") or "").strip()
        if not model or model.lower() == _LEGACY_ST_DEFAULT:
            model = getattr(settings, "local_model", "") or _LOCAL_FALLBACK_MODEL
        key = getattr(settings, "local_api_key", "") or "not-needed"
        return OpenAICompatibleEmbedder(key, base, model)

    return None
