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
        f"below; when you propose something NEW (not already in the lore), say so clearly.\n\n"
        f"BE CONCISE. This is a back-and-forth chat, not an essay. Default to a few sentences "
        f"or a short, scannable list (3-5 bullets max). Lead with the ideas themselves — no "
        f"long preamble, no restating the question, no exhaustive coverage, no closing "
        f"summaries or disclaimers. Offer a handful of focused options, not everything "
        f"possible. If the author wants more depth on one of them, they will ask.\n\n"
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
    focus_type: str | None = None  # character | location | lore | arc
    focus_name: str | None = None


_FOCUS_STORE = {
    "character": "characters",
    "location": "locations",
    "lore": "lore_entries",
    "arc": "story_arcs",
}


def _get_focus_entity(kb, focus_type: str, focus_name: str):
    attr = _FOCUS_STORE.get(focus_type)
    if not attr:
        return None, focus_name
    store = getattr(kb, attr, {}) or {}
    if focus_name in store:
        return store[focus_name], focus_name
    for key, val in store.items():  # case-insensitive fallback
        if key.lower() == (focus_name or "").lower():
            return val, key
    return None, focus_name


_BRIEF_SOURCES = [
    ("Character", "characters", ("role", "background")),
    ("Location", "locations", ("description",)),
    ("Lore", "lore_entries", ("description",)),
    ("Arc", "story_arcs", ("description",)),
]


def _entity_brief(kb, ename: str):
    """A one-line 'Type Name: desc' summary for any entity, by name (case-insensitive)."""
    target = (ename or "").lower()
    for label, attr, descfields in _BRIEF_SOURCES:
        for key, ent in (getattr(kb, attr, {}) or {}).items():
            if key.lower() == target:
                desc = " ".join(str(getattr(ent, f, "") or "") for f in descfields).strip()
                return f"{label} {key}: {desc}".strip()
    return None


def _focus_context(kb, name: str, focus_type: str, focus_name: str, message: str):
    """Return (resolved_name, entity_record, surrounding_lore) for a focused entity.

    Surrounding lore = the entity's cross-referenced companions/connections, the arcs it
    is involved in, and the world lore — gathered as READ-ONLY background for developing
    the focused entity (the prompt forbids modifying those other records).
    """
    from libriscribe.services.context_builder import TokenBudget

    entity, resolved = _get_focus_entity(kb, focus_type, focus_name)
    if entity is None:
        return None

    budget = TokenBudget(2600)
    lines = [f"{focus_type.title()} '{resolved}':"]
    for k, v in entity.model_dump().items():
        if k == "name" or v in (None, "", [], {}):
            continue
        if isinstance(v, (list, dict)):
            v = json.dumps(v, default=str)
        text = str(v)
        lines.append(f"  - {k}: {text[:400] + '...' if len(text) > 400 else text}")
    record = budget.consume("\n".join(lines))

    surrounding: list[str] = []
    seen = {resolved.lower()}

    def add(line: str):
        if not line or budget.exhausted():
            return
        clipped = budget.consume(line)
        if clipped:
            surrounding.append(f"- {clipped}")

    svc = None
    try:
        from libriscribe.retrieval.search_service import SearchServiceImpl
        from libriscribe.retrieval.models import RetrievalConfig

        project_dir = get_projects_dir() / name
        config = kb.retrieval if kb.retrieval and kb.retrieval.enabled else RetrievalConfig(enabled=True, mode="keyword")
        svc = SearchServiceImpl(project_dir, config)
    except Exception:
        svc = None

    # 1) Cross-referenced companions / connected entities (e.g. Manen, Cee).
    if svc is not None:
        try:
            xref = svc.search_cross_references(resolved)
            for rn in (getattr(xref, "related_entities", None) or []):
                if rn.lower() in seen:
                    continue
                brief = _entity_brief(kb, rn)
                if brief:
                    add(brief)
                    seen.add(rn.lower())
                if budget.exhausted():
                    break
        except Exception:
            pass

    # 2) Arcs the focused entity is involved in.
    if focus_type != "arc":
        for an, arc in (kb.story_arcs or {}).items():
            if budget.exhausted():
                break
            involved = [str(x).lower() for x in (getattr(arc, "characters_involved", None) or [])]
            if resolved.lower() in involved and an.lower() not in seen:
                add(f"Arc {an}: {getattr(arc, 'description', '')}")
                seen.add(an.lower())

    # 3) World lore (compact).
    if kb.worldbuilding and not budget.exhausted():
        wb = [f"{k}: {v}" for k, v in kb.worldbuilding.model_dump().items() if isinstance(v, str) and v.strip()]
        if wb:
            add("World — " + " | ".join(wb))

    # 4) Keyword-search supplement seeded by the entity + the question.
    if svc is not None and not budget.exhausted():
        try:
            for r in svc.search(f"{resolved} {message}", mode="keyword", top_k=4):
                if budget.exhausted():
                    break
                text = (getattr(r, "text", "") or "").strip()
                if text:
                    add(text)
        except Exception:
            pass

    return resolved, record, "\n".join(surrounding)


def _focus_system_prompt(kb, focus_type: str, focus_name: str, record: str, surrounding: str) -> str:
    return (
        f"You are a worldbuilding partner for the book '{kb.title}' ({kb.genre}). The author is "
        f"developing the {focus_type} '{focus_name}' and wants to deepen it using the surrounding "
        f"world as context.\n\n"
        f"Use the SURROUNDING LORE below as background to inform and enrich '{focus_name}' — draw "
        f"on the world, arcs, and connected characters to ground your ideas and keep them "
        f"consistent. But keep EVERY suggestion about '{focus_name}' itself: do NOT develop, "
        f"rewrite, or brainstorm the other entities, and do NOT discuss how changes to "
        f"'{focus_name}' would affect them. They are fixed reference, not the subject.\n\n"
        f"BE CONCISE: a few focused suggestions or a short list (3-5 max) — no preamble, no "
        f"exhaustive coverage. If the author wants depth on one, they'll ask.\n\n"
        f"=== {focus_type.title()} being developed: {focus_name} ===\n{record or '(empty)'}\n\n"
        f"=== Surrounding lore (read-only context) ===\n{surrounding or '(none)'}\n=== end ==="
    )


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

    focus = None
    if body.focus_type and body.focus_name:
        focus = _focus_context(kb, name, body.focus_type, body.focus_name, body.message)
    if focus:
        resolved, record, related = focus
        system_prompt = _focus_system_prompt(kb, body.focus_type, resolved, record, related)
    else:
        context = _build_lore_context(name, kb, body.message)
        system_prompt = _system_prompt(kb, context)

    conversation = _build_conversation(history)
    client = _client_for(kb)

    def generate():
        chunks: list[str] = []
        try:
            for chunk in client.generate_content_streaming(
                conversation, max_tokens=700, temperature=0.8, system_prompt=system_prompt
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
