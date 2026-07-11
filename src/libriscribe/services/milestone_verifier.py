"""B45 Slice 4: grade whether written prose actually delivered arc milestones.

Replaces the old fake completion (ProjectManagerAgent flipped a milestone to 'completed'
purely because a chapter with the matching number existed). One utility-model call per
chapter grades the 1-3 milestones targeting it; results land as MilestoneProposal on each
milestone — the USER accepts/rejects, and can flip any status manually anytime.

Trust guard for small local models: an evidence quote that is not actually a substring of
the prose (normalized) downgrades the verdict to 'uncertain'.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_PROSE_WORDS = 3000


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[‘’]", "'", text)
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def _evidence_in_prose(evidence: str, prose: str) -> bool:
    ev = _normalize(evidence)
    return bool(ev) and len(ev) >= 12 and ev in _normalize(prose)


def targeted_milestones(kb, chapter_number: int) -> list[tuple[str, int, object]]:
    """(arc_name, index, milestone) for every milestone targeting this chapter."""
    out = []
    for arc_name, arc in (kb.story_arcs or {}).items():
        for i, m in enumerate(arc.milestones or []):
            if m.target_chapter == chapter_number:
                out.append((arc_name, i, m))
    return out


def verify_chapter(client, kb, project_dir: Path, chapter_number: int) -> list[dict]:
    """Grade every milestone targeting `chapter_number` against that chapter's prose and
    persist a MilestoneProposal on each (in-memory — caller saves the KB). Returns a list of
    {arc, index, name, proposed_status, evidence, reasoning} for the UI."""
    from libriscribe.knowledge_base import MilestoneProposal
    from libriscribe.utils.file_utils import resolve_chapter_path, read_markdown_file, parse_llm_json

    targets = targeted_milestones(kb, chapter_number)
    if not targets:
        return []

    path = resolve_chapter_path(project_dir, chapter_number)
    if not path.exists():
        raise ValueError(f"Chapter {chapter_number} has no prose to grade yet.")
    prose = read_markdown_file(str(path))
    words = prose.split()
    if len(words) > _MAX_PROSE_WORDS:
        # Head + tail beats head-only: resolutions usually land near a chapter's end.
        half = _MAX_PROSE_WORDS // 2
        prose_for_llm = " ".join(words[:half]) + "\n[...middle omitted...]\n" + " ".join(words[-half:])
    else:
        prose_for_llm = prose

    milestone_block = "\n".join(
        f'- id: {i} | name: "{m.name}" | planned beat: {m.description or "(no description)"}'
        for i, (_, _, m) in enumerate(targets)
    )
    prompt = (
        f"You are auditing Chapter {chapter_number} of the {kb.genre} book '{kb.title}'.\n"
        f"For each PLANNED MILESTONE below, judge whether the chapter's prose ACTUALLY "
        f"delivers that story beat — not merely mentions or foreshadows it.\n\n"
        f"PLANNED MILESTONES:\n{milestone_block}\n\n"
        f"CHAPTER PROSE:\n{prose_for_llm}\n\n"
        "Return ONLY a JSON array, one object per milestone:\n"
        '[{"id": 0, "delivered": true|false, "evidence": "<EXACT short quote from the prose '
        'that shows the beat happening, or empty string>", "reasoning": "<one sentence>"}]\n'
        "Be strict: if the beat is only set up or partially reached, delivered = false."
    )

    response = client.generate_content_with_json_repair(prompt, max_tokens=1500, temperature=0.2)
    verdicts = parse_llm_json(response) if response else None
    by_id = {}
    if isinstance(verdicts, list):
        for v in verdicts:
            if isinstance(v, dict) and isinstance(v.get("id"), int):
                by_id[v["id"]] = v

    now = datetime.now(timezone.utc).isoformat()
    results = []
    for i, (arc_name, idx, m) in enumerate(targets):
        v = by_id.get(i)
        if v is None:
            proposed, evidence, reasoning = "uncertain", "", "The model returned no verdict for this milestone."
        else:
            evidence = str(v.get("evidence") or "")
            reasoning = str(v.get("reasoning") or "")
            delivered = bool(v.get("delivered"))
            if delivered and not _evidence_in_prose(evidence, prose):
                proposed = "uncertain"
                reasoning = (reasoning + " " if reasoning else "") + \
                    "(Downgraded: the cited evidence is not an actual quote from the prose.)"
            else:
                proposed = "completed" if delivered else "not_completed"
        m.proposal = MilestoneProposal(
            proposed_status=proposed, evidence=evidence, reasoning=reasoning,
            chapter=chapter_number, created_at=now,
        )
        results.append({
            "arc": arc_name, "index": idx, "name": m.name,
            "proposed_status": proposed, "evidence": evidence, "reasoning": reasoning,
        })
    return results
