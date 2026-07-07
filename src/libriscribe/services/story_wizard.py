"""Guided story-seeding wizard (B38) — gather the author's specifics, elaborate into lore.

NOT an invention engine (locked): the author's answers are authoritative. The wizard
(1) has the LLM author project-tailored questions (stored in the KB's ``dynamic_questions``
    as {question: answer}, answers start empty; user edits/answers/regenerates),
(2) elaborates the ANSWERS into typed lorebook candidates — extract entities from the
    answers, enrich each in parallel (B29), grounded in existing lore for the in-progress
    mode — and stages everything into the sandbox (B27A) for cherry-pick. Nothing lands in
    the lorebook without explicit acceptance.
"""
from __future__ import annotations

import logging

from libriscribe.utils.file_utils import parse_llm_json

logger = logging.getLogger(__name__)

# Fallback core (used when the LLM can't produce tailored questions).
CORE_QUESTIONS = [
    "What is the premise of the story in one or two sentences?",
    "How many main characters are there, and who are they (name, role, key trait)?",
    "What are the high-level story arcs (name each and its shape)?",
    "Where and when is the story set — what makes the world distinct?",
    "What is the central conflict, and who or what opposes the protagonist?",
    "What tone should the story have (dark, hopeful, gritty, comedic…)?",
    "What key factions, items, or rules of the world matter to the plot?",
]


def generate_questions(client, kb, count: int = 7) -> dict[str, str]:
    """LLM-authored, project-tailored intake questions. Merges into kb.dynamic_questions
    (preserving any existing answers); falls back to the fixed core on failure."""
    from libriscribe.services.lore_digest import build_lore_digest

    digest = build_lore_digest(kb, max_tokens=900)
    existing_block = f"\n\nThe project already has this established lore:\n{digest}\n" if digest else ""
    prompt = (
        f"You are helping an author flesh out a {kb.genre} {kb.category} book "
        f"titled \"{kb.title}\" ({kb.book_length or 'Novel'}). Premise/description: "
        f"{(kb.description or '')[:800]}{existing_block}\n"
        f"Write {count} SHORT, CONCRETE intake questions that gather the author's specifics for "
        "this particular story — counts and names of main characters, the high-level arcs, the "
        "setting's distinctives, central conflict, tone, and key factions/items/rules. Tailor the "
        "questions to THIS genre and premise (a mystery asks about the crime and suspects; a "
        "romance about the leads and what keeps them apart). When lore already exists, ask "
        "questions that EXPAND it (new characters, unexplored arcs, deepening the setting) — "
        "never questions it already answers.\n\n"
        'Respond with ONLY a JSON object: {"questions": ["...", "..."]}'
    )
    questions: list[str] = []
    if client is not None:
        try:
            raw = client.generate_content_with_json_repair(prompt, max_tokens=800, temperature=0.6)
            data = parse_llm_json(raw)
            if isinstance(data, dict) and isinstance(data.get("questions"), list):
                questions = [str(q).strip() for q in data["questions"] if str(q).strip()][:count]
        except Exception:
            logger.debug("Tailored question generation failed; using core set", exc_info=True)
    if not questions:
        questions = list(CORE_QUESTIONS)

    merged = dict(kb.dynamic_questions or {})
    for q in questions:
        merged.setdefault(q, "")
    kb.dynamic_questions = merged
    return merged


def _answers_text(kb) -> str:
    parts = [f"Q: {q}\nA: {a.strip()}" for q, a in (kb.dynamic_questions or {}).items() if str(a).strip()]
    return "\n\n".join(parts)


def elaborate(client, kb, project_name: str, max_workers: int = 4) -> dict | None:
    """Elaborate the author's ANSWERS into typed candidates and stage them in the sandbox.

    Two passes: (1) extract the entities the answers actually describe (the sorter contract
    already forbids inventing); (2) enrich each entity's full field set in parallel from the
    answers, augmenting existing records by name (in-progress mode). Returns the sandbox run,
    or None when there is nothing answered."""
    from libriscribe.services import lore_intake, sandbox
    from libriscribe.utils.parallel import bounded_map

    text = _answers_text(kb)
    if not text.strip() or client is None:
        return None

    # The author's answers are authoritative source material.
    source = (
        "The author's own answers about their story (AUTHORITATIVE — extract and elaborate "
        "exactly what they describe; do not invent unrelated entities):\n\n" + text
    )

    cats = lore_intake.extract_from_text(client, kb.genre, source, book_title=kb.title)

    # Enrich each extracted entity's full typed field set from the answers, in parallel.
    jobs: list[tuple[str, str, dict]] = []  # (category, name, base_fields)
    for cat in ("characters", "locations", "lore", "arcs"):
        for rec in cats.get(cat, []) or []:
            nm = str(rec.get("name", "")).strip()
            if nm:
                jobs.append((cat, nm, dict(rec.get("fields", {}) or {})))

    def _enrich(job):
        cat, nm, base = job
        type_key = {"characters": "character", "locations": "location", "lore": "lore", "arcs": "arc"}[cat]
        fields = lore_intake.llm_extract_for_type(
            client, kb.genre, nm, text, type_key, book_title=kb.title,
            existing_fields=lore_intake.existing_fields_for(kb, cat, nm),
        )
        merged = {**base, **{k: v for k, v in (fields or {}).items() if str(v).strip()}}
        return (cat, nm, merged)

    enriched = bounded_map(_enrich, jobs, max_workers)

    candidates = []
    stores = {"characters": kb.characters, "locations": kb.locations,
              "lore": kb.lore_entries, "arcs": kb.story_arcs}
    for r in enriched:
        if not r:
            continue
        cat, nm, fields = r
        exists = any(str(k).strip().lower() == nm.lower() for k in (stores.get(cat) or {}))
        candidates.append(sandbox.new_candidate(
            cat, nm, fields, op="update" if exists else "new",
            source="wizard", rationale="Elaborated from your wizard answers.",
        ))
    if not candidates:
        return None
    return sandbox.create_run(project_name, {"kind": "wizard"}, candidates)
