"""Entity interconnection (B25) — navigable, bidirectional links between lore records.

Reads the existing name-based relational fields (`Character.relationships`,
`Location.associated_characters`, `LoreEntry.related_entities`,
`StoryArc.characters_involved`, `NarrativeThread.characters_involved`) and resolves them into
navigable links, in BOTH directions:

- **outgoing** — records this entity points at (from its own relational fields).
- **incoming** — records that point at this entity (found by scanning everyone else's fields).

Links are stored free-form by name (matching the merge-by-name model), so a name with no matching
record is returned with ``resolved: False`` — the UI shows it as an "unlinked" chip and the
gap-finder already flags it. Pure/side-effect-free; the read model B27's sandbox reuses.
"""
from __future__ import annotations

# entity_type -> KB container attribute.
_STORES = {
    "character": "characters",
    "location": "locations",
    "lore": "lore_entries",
    "arc": "story_arcs",
    "thread": "narrative_threads",
}

# entity_type -> (relational field, verb describing the link).
_LINK_FIELD = {
    "character": ("relationships", "knows"),
    "location": ("associated_characters", "features"),
    "lore": ("related_entities", "relates to"),
    "arc": ("characters_involved", "involves"),
    "thread": ("characters_involved", "involves"),
}


def _all_names(kb) -> dict[str, tuple[str, str]]:
    """lowercased name -> (entity_type, canonical name) across every store."""
    m: dict[str, tuple[str, str]] = {}
    for etype, attr in _STORES.items():
        for n in (getattr(kb, attr, {}) or {}):
            key = str(n).strip().lower()
            if key:
                m.setdefault(key, (etype, n))
    return m


def _refs_of(entity, entity_type) -> list[tuple[str, str]]:
    """(referenced_name, detail) pairs from an entity's relational field."""
    field, _verb = _LINK_FIELD.get(entity_type, ("", ""))
    val = getattr(entity, field, None) if field else None
    out: list[tuple[str, str]] = []
    if isinstance(val, dict):  # Character.relationships: name -> description
        for k, v in val.items():
            if str(k).strip():
                out.append((str(k).strip(), str(v or "")))
    elif isinstance(val, list):
        for x in val:
            if str(x).strip():
                out.append((str(x).strip(), ""))
    return out


def _verb(entity_type: str) -> str:
    return _LINK_FIELD.get(entity_type, ("", "links to"))[1]


def _canonical(store: dict, name: str) -> str | None:
    target = str(name).strip().lower()
    return next((k for k in store if str(k).strip().lower() == target), None)


def entity_connections(kb, entity_type: str, name: str) -> dict:
    """Return {outgoing, incoming} navigable links for one entity (empty if it doesn't exist)."""
    store = getattr(kb, _STORES.get(entity_type, ""), {}) or {}
    canon = _canonical(store, name)
    if canon is None:
        return {"outgoing": [], "incoming": [], "found": False}

    entity = store[canon]
    known = _all_names(kb)
    target_low = canon.lower()

    # Outgoing — what this entity points at.
    outgoing = []
    seen_out: set[tuple[str, str]] = set()
    for ref, detail in _refs_of(entity, entity_type):
        resolved = known.get(ref.lower())
        rtype, rname = (resolved[0], resolved[1]) if resolved else ("", ref)
        key = (rtype, rname.lower())
        if key in seen_out:
            continue
        seen_out.add(key)
        outgoing.append({
            "type": rtype, "name": rname, "relation": _verb(entity_type),
            "detail": detail, "resolved": bool(resolved),
        })

    # Incoming — who points at this entity (scan everyone else's relational fields).
    incoming = []
    for etype, attr in _STORES.items():
        for other_name, other in (getattr(kb, attr, {}) or {}).items():
            if etype == entity_type and str(other_name).lower() == target_low:
                continue  # skip self
            for ref, detail in _refs_of(other, etype):
                if ref.lower() == target_low:
                    incoming.append({
                        "type": etype, "name": other_name, "relation": _verb(etype), "detail": detail,
                    })
                    break  # one link per source entity

    return {"outgoing": outgoing, "incoming": incoming, "found": True}


# Which field an entity's outgoing links live in (for adding a suggestion to the right place).
PRIMARY_LINK_FIELD = {
    "character": "relationships",
    "location": "associated_characters",
    "lore": "related_entities",
    "arc": "characters_involved",
    "thread": "characters_involved",
}


def suggest_connections(kb, project_dir, entity_type: str, name: str) -> dict:
    """Auto-suggest links from cross-reference co-occurrence: entities that appear alongside this
    one across chapters but aren't already linked. Empty when there's no prose/xref index yet."""
    store = getattr(kb, _STORES.get(entity_type, ""), {}) or {}
    canon = _canonical(store, name)
    if canon is None:
        return {"suggestions": []}

    conns = entity_connections(kb, entity_type, canon)
    already = {o["name"].lower() for o in conns["outgoing"]}
    already.add(canon.lower())
    known = _all_names(kb)

    suggestions = []
    seen: set[str] = set()
    try:
        from libriscribe.services.retrieval_service import search_service_for
        svc = search_service_for(project_dir, kb)
        xref = svc.search_cross_references(canon)
        for rn in (getattr(xref, "related_entities", None) or []):
            low = str(rn).strip().lower()
            resolved = known.get(low)
            if not resolved or low in already or low in seen:
                continue
            seen.add(low)
            suggestions.append({"type": resolved[0], "name": resolved[1]})
    except Exception:
        pass
    return {"suggestions": suggestions}
