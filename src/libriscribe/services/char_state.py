"""Character-state + lightweight timeline tracking (B33).

Populates the previously-unused ``kb.character_states`` (per-chapter snapshots: emotional
state, newly-learned knowledge, location, physical state) and a new ``kb.timeline_events``
list from written chapter prose — one small structured pass per chapter, fanned out through
the bounded runner (B29). Feeds B31's "knows something too early" continuity check and
time-aware generation context.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from libriscribe.utils.file_utils import parse_llm_json

logger = logging.getLogger(__name__)


def _prompt(kb, chapter_number: int, text: str) -> str:
    known = ", ".join(kb.characters.keys()) or "(none recorded)"
    return (
        f"Read Chapter {chapter_number} of this {kb.genre} book and extract a per-character state "
        f"snapshot plus the chapter's key events. Known characters: {known}.\n\n"
        "Rules: only characters who actually appear or are directly affected; only facts stated in "
        "this chapter; 'knowledge' = NEW information the character LEARNS in this chapter (secrets, "
        "revelations) — each as a short sentence; 2-5 key events max, each one line.\n\n"
        "Respond with ONLY a JSON object of this shape:\n"
        "```json\n{\n"
        '  "states": [{"character_name": "<name>", "emotional_state": "<...>",\n'
        '              "knowledge": ["<learned this chapter>"], "location": "<where they end up>",\n'
        '              "physical_state": "<injuries/condition or empty>"}],\n'
        '  "events": [{"description": "<key event>", "characters_involved": ["<name>"]}]\n'
        "}\n```\n\n"
        f"CHAPTER {chapter_number} TEXT:\n{text[:24000]}"
    )


def extract_chapter_state(client, kb, chapter_number: int, text: str) -> dict:
    """One chapter's states + events (raw dict; empty on failure)."""
    try:
        raw = client.generate_content_with_json_repair(
            _prompt(kb, chapter_number, text), max_tokens=1500, temperature=0.2,
        )
        data = parse_llm_json(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.debug("char-state extraction failed for ch %s", chapter_number, exc_info=True)
        return {}


def track_states(client, kb, project_dir: Path, chapters: list[int] | None = None,
                 max_workers: int = 4) -> dict:
    """Extract states+timeline for the given chapters (default: all written), in parallel.
    Replaces each scanned chapter's previous snapshot/events (idempotent re-runs)."""
    from libriscribe.knowledge_base import CharacterState, TimelineEvent
    from libriscribe.utils.parallel import bounded_map

    project_dir = Path(project_dir)
    texts: dict[int, str] = {}
    for f in project_dir.glob("chapter_*.md"):
        if f.name.endswith("_original.md"):
            continue
        try:
            n = int(f.stem.split("_")[1])
        except (ValueError, IndexError):
            continue
        if chapters and n not in chapters:
            continue
        t = f.read_text(encoding="utf-8")
        if t.strip():
            # prefer the revised file when both exist
            if n not in texts or "revised" in f.name:
                texts[n] = t
    if not texts or client is None:
        return {"chapters_scanned": 0, "states": 0, "events": 0}

    nums = sorted(texts)
    results = bounded_map(lambda n: (n, extract_chapter_state(client, kb, n, texts[n])), nums, max_workers)

    states_added = 0
    events_added = 0
    for r in results:
        if not r:
            continue
        n, data = r
        # Replace this chapter's previous snapshots/events (idempotent).
        for char_name in list(kb.character_states.keys()):
            kb.character_states[char_name] = [
                s for s in kb.character_states[char_name] if s.chapter_number != n
            ]
        kb.timeline_events = [e for e in (kb.timeline_events or []) if e.chapter_number != n]

        for s in data.get("states", []) or []:
            cn = str((s or {}).get("character_name", "")).strip()
            if not cn:
                continue
            knowledge = s.get("knowledge") or []
            if isinstance(knowledge, str):
                knowledge = [knowledge]
            state = CharacterState(
                character_name=cn, chapter_number=n,
                emotional_state=str(s.get("emotional_state", "") or ""),
                knowledge=[str(k) for k in knowledge if str(k).strip()],
                physical_state=str(s.get("physical_state", "") or ""),
                notes=str(s.get("location", "") or ""),
            )
            kb.character_states.setdefault(cn, []).append(state)
            states_added += 1
        for e in data.get("events", []) or []:
            desc = str((e or {}).get("description", "")).strip()
            if not desc:
                continue
            kb.timeline_events.append(TimelineEvent(
                chapter_number=n, description=desc,
                characters_involved=[str(x) for x in (e.get("characters_involved") or []) if str(x).strip()],
            ))
            events_added += 1

    for cn in kb.character_states:
        kb.character_states[cn].sort(key=lambda s: s.chapter_number)
    kb.timeline_events.sort(key=lambda e: e.chapter_number)
    return {"chapters_scanned": len(nums), "states": states_added, "events": events_added}


def knowledge_timeline_block(kb) -> str:
    """'Who knows what, as of which chapter' — for B31's knows-too-early check. Empty if no states."""
    lines: list[str] = []
    for cn, states in (kb.character_states or {}).items():
        for s in states:
            for k in s.knowledge or []:
                lines.append(f"- Ch {s.chapter_number}: {cn} learns: {k}")
    if not lines:
        return ""
    lines.sort()
    return (
        "CHARACTER KNOWLEDGE TIMELINE (who learns what, when):\n" + "\n".join(lines) + "\n"
        "If a chapter shows a character ACTING ON or REFERRING TO information before the chapter "
        "where they learn it, report it as note_type \"knows_too_early\"."
    )
