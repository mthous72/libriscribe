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

from pathlib import Path
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


# ─── AI pass: referenced-but-undefined entities (B28 slice 2) ─────────────────
# Opt-in, LLM-backed: scan prose + lore free-text for named entities that have no KB record.
# Fanned out through the bounded parallel runner at the project's max_concurrency (B29).

_TEXT_CAP = 6000  # per-source char cap fed to the model (matches the other extract prompts)


def gather_source_texts(kb, project_dir) -> list[tuple[str, str]]:
    """(label, text) pairs to scan: chapter prose files + every lore free-text field."""
    texts: list[tuple[str, str]] = []

    pd = Path(project_dir) if project_dir else None
    if pd and pd.exists():
        best: dict[int, tuple[bool, str]] = {}  # chapter -> (is_revised, text); prefer revised
        for path in pd.glob("chapter_*.md"):
            fn = path.name
            if fn.endswith("_original.md"):
                continue
            try:
                ch = int(fn.split("_")[1].split(".")[0])
                t = path.read_text(encoding="utf-8")
            except (ValueError, IndexError, OSError):
                continue
            if not t.strip():
                continue
            revised = "revised" in fn
            prev = best.get(ch)
            if prev is None or (revised and not prev[0]):
                best[ch] = (revised, t)
        for ch in sorted(best):
            texts.append((f"Chapter {ch}", best[ch][1]))

    def blob(*parts: str) -> str:
        return "\n".join(p for p in (str(x or "") for x in parts) if p.strip())

    for name, c in (kb.characters or {}).items():
        b = blob(c.background, c.physical_description, c.personality_traits, c.motivations,
                 c.internal_conflicts, c.external_conflicts, c.character_arc)
        if b.strip():
            texts.append((f"character:{name}", b))
    for name, loc in (kb.locations or {}).items():
        b = blob(loc.description, loc.significance)
        if b.strip():
            texts.append((f"location:{name}", b))
    for name, e in (kb.lore_entries or {}).items():
        b = blob(e.description, e.significance)
        if b.strip():
            texts.append((f"lore:{name}", b))
    for name, a in (kb.story_arcs or {}).items():
        b = blob(a.description, a.resolution_notes)
        if b.strip():
            texts.append((f"arc:{name}", b))
    wb = getattr(kb, "worldbuilding", None)
    if wb:
        vals = [str(v) for v in wb.model_dump().values() if isinstance(v, str) and v.strip()]
        if vals:
            texts.append(("worldbuilding", "\n".join(vals)))
    return texts


def _extract_named_entities(client, genre: str, text: str) -> list[dict]:
    """One small NER pass over a passage → [{name, type}, ...] (empty on any failure)."""
    from libriscribe.services import lore_prompts
    from libriscribe.utils.file_utils import parse_llm_json

    prompt = lore_prompts.build_named_entity_prompt(genre, text)
    try:
        raw = client.generate_content_with_json_repair(
            prompt, max_tokens=800, temperature=0.1,
            system_prompt=lore_prompts.BASE_SYSTEM_PROMPT,
        )
    except Exception:
        return []
    data = parse_llm_json(raw)
    if isinstance(data, dict) and isinstance(data.get("entities"), list):
        return data["entities"]
    return []


def find_undefined_entities(client, kb, texts, max_workers: int,
                            on_progress=None, limit: int = 60) -> dict:
    """Referenced-but-undefined pass: NER over each source (in parallel), aggregate names not in
    the KB, rank by mention count. Returns gaps (type=undefined_entity) + scan metadata."""
    from libriscribe.utils.parallel import bounded_map

    if client is None or not texts:
        return {"gaps": [], "scanned": 0, "truncated": False}

    known = _all_entity_names_lower(kb)

    def _scan(pair: tuple[str, str]):
        label, text = pair
        return (label, _extract_named_entities(client, getattr(kb, "genre", ""), text[:_TEXT_CAP]))

    results = bounded_map(_scan, texts, max_workers, on_progress)

    agg: dict[str, dict] = {}
    for r in results:
        if not r:
            continue
        label, ents = r
        for ne in ents or []:
            nm = str((ne or {}).get("name", "")).strip()
            if len(nm) < 2 or nm.lower() in known:
                continue
            e = agg.get(nm.lower())
            if e is None:
                e = agg[nm.lower()] = {"name": nm, "type": str((ne or {}).get("type", "") or "").strip().lower(),
                                       "mentions": 0, "sources": []}
            e["mentions"] += 1
            if label not in e["sources"]:
                e["sources"].append(label)

    ranked = sorted(agg.values(), key=lambda x: (-x["mentions"], x["name"].lower()))
    truncated = len(ranked) > limit
    ranked = ranked[:limit]

    gaps = []
    for e in ranked:
        etype = e["type"] if e["type"] in ("character", "location", "lore", "arc") else "lore"
        srcs = ", ".join(e["sources"][:5]) + ("…" if len(e["sources"]) > 5 else "")
        gaps.append({
            "id": f"undefined_entity:{e['name'].lower()}",
            "type": "undefined_entity",
            "severity": "warn",
            "entity_type": etype,  # SUGGESTED type — the entity has no record yet
            "entity_name": e["name"],
            "message": f"Mentioned {e['mentions']}× but has no lore record (looks like a {etype}).",
            "evidence": f"in: {srcs}",
            "target": None,  # nothing to open — creating it comes with the Auto-mode sandbox (B27)
        })
    return {"gaps": gaps, "scanned": len(texts), "truncated": truncated}


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
