"""Structural gap-finder (B28, first slice) — deterministic, no LLM.

Scans a ``ProjectKnowledgeBase`` for structural gaps the author probably wants to fix:
dangling references (a name mentioned in a field but with no record), chapter numbers out
of range, still-open arcs/threads, and "thin" characters missing the fields the writing
pipeline consumes. Pure and side-effect-free so it's fast and unit-testable; the LLM
"referenced-but-undefined" and connective-tissue passes come in a later slice.

Each gap is a plain dict:
    {
      "id":          stable string (React key),
      "type":        dangling_reference | out_of_range_chapter | unresolved_thread |
                     unresolved_arc | thin_character | missing_voice,
      "severity":    warn | info,
      "entity_type": character | location | lore | arc | thread,
      "entity_name": the record the gap belongs to,
      "message":     one-line human description,
      "evidence":    where/why (e.g. the referencing field),
      "target":      {"type": <entity_type>, "name": <entity_name>}  # for click-to-open
    }
"""
from __future__ import annotations

from typing import Any

# Statuses that mean an arc/thread is finished (case-insensitive).
_RESOLVED_STATUSES = {"resolved", "closed", "complete", "completed", "done", "finished"}

# entity_type -> KB container attribute.
_STORES = {
    "character": "characters",
    "location": "locations",
    "lore": "lore_entries",
    "arc": "story_arcs",
    "thread": "narrative_threads",
}


def _chapter_ceiling(kb) -> int:
    """Highest valid chapter number (0 = unknown → skip range checks)."""
    nc = getattr(kb, "num_chapters", 0)
    if isinstance(nc, (tuple, list)):
        return max(nc) if nc else 0
    try:
        return int(nc)
    except (TypeError, ValueError):
        return 0


def _all_entity_names_lower(kb) -> set[str]:
    """Lowercased names of every entity across all lore stores (for reference resolution)."""
    names: set[str] = set()
    for attr in _STORES.values():
        for n in (getattr(kb, attr, {}) or {}):
            if str(n).strip():
                names.add(str(n).strip().lower())
    return names


def _gap(gaps: list[dict], *, type: str, severity: str, entity_type: str, entity_name: str,
         message: str, evidence: str = "", detail: str = "") -> None:
    gaps.append({
        "id": f"{type}:{entity_type}:{entity_name}:{detail}".rstrip(":"),
        "type": type,
        "severity": severity,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "message": message,
        "evidence": evidence,
        "target": {"type": entity_type, "name": entity_name},
    })


def _check_references(gaps: list[dict], kb, known: set[str]) -> None:
    """Names mentioned in relationship / involved / related fields with no matching record."""
    def scan(entity_type: str, name: str, field_label: str, refs: Any) -> None:
        for ref in refs or []:
            r = str(ref).strip()
            if r and r.lower() not in known:
                _gap(gaps, type="dangling_reference", severity="warn",
                     entity_type=entity_type, entity_name=name,
                     message=f"References \"{r}\", which has no lore record.",
                     evidence=f"{field_label}: {r}", detail=f"{field_label}={r.lower()}")

    for name, c in (kb.characters or {}).items():
        scan("character", name, "relationships", list((c.relationships or {}).keys()))
    for name, loc in (kb.locations or {}).items():
        scan("location", name, "associated_characters", loc.associated_characters)
    for name, e in (kb.lore_entries or {}).items():
        scan("lore", name, "related_entities", e.related_entities)
    for name, a in (kb.story_arcs or {}).items():
        scan("arc", name, "characters_involved", a.characters_involved)
    for name, t in (kb.narrative_threads or {}).items():
        scan("thread", name, "characters_involved", t.characters_involved)


def _check_chapter(gaps: list[dict], entity_type: str, name: str, field_label: str,
                   value: Any, ceiling: int) -> None:
    if value is None:
        return
    try:
        ch = int(value)
    except (TypeError, ValueError):
        return
    if ch < 1 or (ceiling and ch > ceiling):
        bound = f"1..{ceiling}" if ceiling else "≥ 1"
        _gap(gaps, type="out_of_range_chapter", severity="warn",
             entity_type=entity_type, entity_name=name,
             message=f"{field_label} is chapter {ch}, outside the story's range ({bound}).",
             evidence=f"{field_label}={ch}", detail=f"{field_label}={ch}")


def _check_chapters(gaps: list[dict], kb, ceiling: int) -> None:
    for name, loc in (kb.locations or {}).items():
        _check_chapter(gaps, "location", name, "first_appearance", loc.first_appearance, ceiling)
    for name, e in (kb.lore_entries or {}).items():
        _check_chapter(gaps, "lore", name, "first_appearance", e.first_appearance, ceiling)
    for name, a in (kb.story_arcs or {}).items():
        for ch in a.chapters_involved or []:
            _check_chapter(gaps, "arc", name, "chapters_involved", ch, ceiling)
        for m in a.milestones or []:
            _check_chapter(gaps, "arc", name, f"milestone '{m.name}' target_chapter", m.target_chapter, ceiling)
            _check_chapter(gaps, "arc", name, f"milestone '{m.name}' actual_chapter", m.actual_chapter, ceiling)
    for name, t in (kb.narrative_threads or {}).items():
        _check_chapter(gaps, "thread", name, "opened_chapter", t.opened_chapter, ceiling)
        _check_chapter(gaps, "thread", name, "target_resolution_chapter", t.target_resolution_chapter, ceiling)
        _check_chapter(gaps, "thread", name, "resolved_chapter", t.resolved_chapter, ceiling)


def _check_unresolved(gaps: list[dict], kb) -> None:
    for name, t in (kb.narrative_threads or {}).items():
        resolved = t.resolved_chapter is not None or str(t.status or "").strip().lower() in _RESOLVED_STATUSES
        if not resolved:
            _gap(gaps, type="unresolved_thread", severity="info",
                 entity_type="thread", entity_name=name,
                 message=f"Thread is still open (status: {t.status or 'open'}).",
                 evidence=f"opened_chapter={t.opened_chapter}, resolved_chapter={t.resolved_chapter}")
    for name, a in (kb.story_arcs or {}).items():
        resolved = str(a.status or "").strip().lower() in _RESOLVED_STATUSES or bool((a.resolution_notes or "").strip())
        if not resolved:
            _gap(gaps, type="unresolved_arc", severity="info",
                 entity_type="arc", entity_name=name,
                 message=f"Arc has no resolution yet (status: {a.status or 'active'}).",
                 evidence="no resolution_notes")


def _check_thin_characters(gaps: list[dict], kb) -> None:
    for name, c in (kb.characters or {}).items():
        missing = [f for f in ("motivations", "character_arc") if not str(getattr(c, f, "") or "").strip()]
        if missing:
            labels = " and ".join(m.replace("_", " ") for m in missing)
            _gap(gaps, type="thin_character", severity="warn",
                 entity_type="character", entity_name=name,
                 message=f"Missing {labels} — the writer leans on this.",
                 evidence=f"empty: {', '.join(missing)}", detail=",".join(missing))
        vp = getattr(c, "voice_profile", None)
        has_voice = bool(vp) and any(str(getattr(vp, f, "") or "").strip() or getattr(vp, "example_dialogue", None)
                                     for f in ("speech_patterns", "vocabulary_level", "verbal_tics", "avoids"))
        if not has_voice:
            _gap(gaps, type="missing_voice", severity="info",
                 entity_type="character", entity_name=name,
                 message="No Voice Profile yet — dialogue won't have a distinct voice.",
                 evidence="voice_profile empty", detail="voice")


def find_gaps(kb) -> dict:
    """Return structural gaps for a project KB, plus counts by severity."""
    gaps: list[dict] = []
    known = _all_entity_names_lower(kb)
    ceiling = _chapter_ceiling(kb)

    _check_references(gaps, kb, known)
    _check_chapters(gaps, kb, ceiling)
    _check_unresolved(gaps, kb)
    _check_thin_characters(gaps, kb)

    # Warnings first, then info; stable within a severity by insertion order.
    order = {"warn": 0, "info": 1}
    gaps.sort(key=lambda g: order.get(g["severity"], 2))
    counts = {
        "total": len(gaps),
        "warn": sum(1 for g in gaps if g["severity"] == "warn"),
        "info": sum(1 for g in gaps if g["severity"] == "info"),
    }
    return {"gaps": gaps, "counts": counts}
