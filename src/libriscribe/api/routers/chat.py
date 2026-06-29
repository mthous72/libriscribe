"""Brainstorm chat (B9) — a lore-aware LLM co-writer per project.

- GET    /api/projects/{name}/chat        -> conversation history
- DELETE /api/projects/{name}/chat        -> clear history
- POST   /api/projects/{name}/chat        -> stream an LLM reply (text/plain)
- POST   /api/projects/{name}/chat/apply  -> turn an idea into a draft lore entry

Reuses the project's LLM provider/model, the retrieval index for RAG context, and the
existing lore models / KB save path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from libriscribe.knowledge_base import Character, Location, LoreEntry, StoryArc
from libriscribe.services.project_service import get_projects_dir, load_kb, save_kb
from libriscribe.utils.llm_client import LLMClient

router = APIRouter(prefix="/api/projects", tags=["chat"])


# ─── Persistence ──────────────────────────────────────────────────────────────

def _chat_path(name: str):
    return get_projects_dir() / name / "chat_history.json"


def _load_chat(name: str) -> list[dict]:
    path = _chat_path(name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_chat(name: str, messages: list[dict]) -> None:
    path = _chat_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, indent=2), encoding="utf-8")


def _append(name: str, role: str, content: str) -> list[dict]:
    messages = _load_chat(name)
    messages.append({"role": role, "content": content, "ts": datetime.now(timezone.utc).isoformat()})
    _save_chat(name, messages)
    return messages


# ─── RAG context ──────────────────────────────────────────────────────────────

def _build_lore_context(name: str, kb, query: str, max_tokens: int = 1800) -> str:
    """Assemble a token-bounded block of established lore relevant to `query`.

    Prefer the retrieval index; fall back to a compact dump of KB entities.
    """
    from libriscribe.services.context_builder import TokenBudget

    budget = TokenBudget(max_tokens)
    parts: list[str] = []
    project_dir = get_projects_dir() / name

    try:
        from libriscribe.retrieval.search_service import SearchServiceImpl
        from libriscribe.retrieval.models import RetrievalConfig

        config = kb.retrieval if kb.retrieval and kb.retrieval.enabled else RetrievalConfig(enabled=True, mode="keyword")
        svc = SearchServiceImpl(project_dir, config)
        for r in svc.search(query, mode="keyword", top_k=6):
            text = (getattr(r, "text", "") or "").strip()
            if not text:
                continue
            clipped = budget.consume(text)
            if clipped:
                parts.append(f"- {clipped}")
            if budget.exhausted():
                break
    except Exception:
        pass

    # Supplement / fallback with KB entities.
    def add(label: str, value: str):
        if budget.exhausted() or not value:
            return
        clipped = budget.consume(f"{label}: {value}".strip())
        if clipped:
            parts.append(f"- {clipped}")

    if not parts:
        for c in list(kb.characters.values())[:25]:
            add(f"Character {c.name}", f"{getattr(c, 'role', '')} {getattr(c, 'background', '')}".strip())
        for loc in list(kb.locations.values())[:25]:
            add(f"Location {loc.name}", getattr(loc, "description", ""))
        for e in list(kb.lore_entries.values())[:25]:
            add(f"Lore {e.name}", getattr(e, "description", ""))
        for arc in list(kb.story_arcs.values())[:25]:
            add(f"Arc {arc.name}", getattr(arc, "description", ""))

    return "\n".join(parts)


def _system_prompt(kb, context: str) -> str:
    return (
        f"You are a creative worldbuilding and brainstorming partner for the book "
        f"'{kb.title}' ({kb.genre}). Help the author explore ideas, plan story arcs, and "
        f"research before anything is finalized. Stay consistent with the established lore "
        f"below. When you propose something NEW (not already in the lore), say so clearly so "
        f"the author can decide whether to add it.\n\n"
        f"=== Established lore ===\n{context or '(none yet)'}\n=== end lore ==="
    )


def _build_conversation(history: list[dict], limit: int = 12) -> str:
    convo = ""
    for m in history[-limit:]:
        speaker = "Author" if m.get("role") == "user" else "Assistant"
        convo += f"{speaker}: {m.get('content', '')}\n\n"
    convo += "Assistant:"
    return convo


def _client_for(kb) -> LLMClient:
    client = LLMClient(kb.llm_provider)
    if kb.model:
        client.set_model(kb.model)
    return client


# ─── Endpoints ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@router.get("/{name}/chat")
def get_chat(name: str):
    if not load_kb(name):
        raise HTTPException(status_code=404, detail="Project not found")
    return _load_chat(name)


@router.delete("/{name}/chat", status_code=204)
def clear_chat(name: str):
    if not load_kb(name):
        raise HTTPException(status_code=404, detail="Project not found")
    _save_chat(name, [])


@router.post("/{name}/chat")
def chat(name: str, body: ChatRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    history = _append(name, "user", body.message)
    context = _build_lore_context(name, kb, body.message)
    system_prompt = _system_prompt(kb, context)
    conversation = _build_conversation(history)
    client = _client_for(kb)

    def generate():
        chunks: list[str] = []
        try:
            for chunk in client.generate_content_streaming(
                conversation, max_tokens=1500, temperature=0.8, system_prompt=system_prompt
            ):
                chunks.append(chunk)
                yield chunk
        except Exception as exc:  # noqa: BLE001 — surface the error in-stream
            msg = f"\n\n[Error: {exc}]"
            chunks.append(msg)
            yield msg
        _append(name, "assistant", "".join(chunks))

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


# ─── Apply an idea to lore ────────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    text: str
    target_type: str  # character | location | lore | arc
    entity_name: str
    smart: bool = False


_SMART_FIELDS = {
    "character": ["role", "physical_description", "personality_traits", "background", "motivations", "character_arc"],
    "location": ["description", "significance"],
    "lore": ["entry_type", "description", "significance"],
    "arc": ["arc_type", "description", "resolution_notes"],
}


def _extract_fields(kb, target_type: str, text: str) -> dict:
    """Use the LLM to parse an idea into typed fields for a lore entity."""
    fields = _SMART_FIELDS.get(target_type, ["description"])
    prompt = (
        f"Extract a {target_type} for a {kb.genre} book from the idea below. "
        f"Return ONLY a JSON object with these string keys: {', '.join(fields)}. "
        f"Use empty strings for anything not implied. Idea:\n\n{text}"
    )
    try:
        raw = _client_for(kb).generate_content_with_json_repair(prompt, max_tokens=800, temperature=0.4)
        data = json.loads(raw)
        return {k: (str(v) if v is not None else "") for k, v in data.items() if k in fields}
    except Exception:
        return {}


@router.post("/{name}/chat/apply")
def apply_to_lore(name: str, body: ApplyRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    target = body.target_type
    entity_name = body.entity_name.strip()
    if not entity_name:
        raise HTTPException(status_code=400, detail="entity_name is required")
    if target not in _SMART_FIELDS:
        raise HTTPException(status_code=400, detail="unsupported target_type")

    fields = _extract_fields(kb, target, body.text) if body.smart else {}
    # Draft fallback: put the raw text where it best fits.
    if not fields:
        fields = {"background": body.text} if target == "character" else {"description": body.text}

    def build(model_cls, store: dict):
        allowed = {k: v for k, v in fields.items() if k in model_cls.model_fields}
        try:
            entity = model_cls(name=entity_name, **allowed)
        except Exception:
            # Never fail an apply — fall back to a minimal entity.
            key = "background" if model_cls is Character else "description"
            entity = model_cls(name=entity_name, **{key: body.text})
        store[entity_name] = entity
        return entity

    if target == "character":
        entity = build(Character, kb.characters)
    elif target == "location":
        entity = build(Location, kb.locations)
    elif target == "lore":
        entity = build(LoreEntry, kb.lore_entries)
    else:  # arc
        entity = build(StoryArc, kb.story_arcs)

    save_kb(name, kb)
    return {"target_type": target, "name": entity_name, "entity": entity.model_dump()}
