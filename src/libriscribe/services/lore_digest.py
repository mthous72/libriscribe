"""Lorebook digest (Phase 0b) — a compact, token-budgeted summary of the user's established
world, injected into generation prompts (concept, outline, …) so every stage EXTENDS the
author's lore instead of inventing a new world.

Pure KB reads — no LLM calls, no retrieval/embedding (so no local model swaps). Priority order
puts the most story-shaping material first (characters → arcs → threads → worldbuilding →
locations → codex) and the budget truncates gracefully from the bottom.
"""
from __future__ import annotations

from libriscribe.services.context_builder import TokenBudget


def _clip(text: str, limit: int = 240) -> str:
    t = " ".join(str(text or "").split())
    return t[: limit - 1] + "…" if len(t) > limit else t


def build_lore_digest(kb, max_tokens: int = 1600) -> str:
    """A budgeted plain-text digest of the KB's established lore. Empty string if the
    lorebook is empty (callers then omit the grounding block entirely)."""
    budget = TokenBudget(max_tokens)
    sections: list[str] = []

    def add_section(title: str, lines: list[str]) -> None:
        if not lines or budget.exhausted():
            return
        block = budget.consume(f"{title}:\n" + "\n".join(lines))
        if block:
            sections.append(block)

    chars = []
    for c in (kb.characters or {}).values():
        bits = [b for b in (c.role, c.motivations, c.character_arc) if str(b or "").strip()]
        chars.append(f"- {c.name}" + (f" — {_clip(' | '.join(bits))}" if bits else ""))
    add_section("CHARACTERS", chars)

    arcs = []
    for a in (kb.story_arcs or {}).values():
        detail = _clip(a.description) if str(a.description or "").strip() else a.arc_type
        arcs.append(f"- {a.name} ({a.status or 'active'}) — {detail}")
    add_section("STORY ARCS", arcs)

    threads = []
    for t in (kb.narrative_threads or {}).values():
        threads.append(f"- {t.name} ({t.status or 'open'}) — {_clip(t.description)}")
    add_section("NARRATIVE THREADS", threads)

    wb = getattr(kb, "worldbuilding", None)
    world = []
    if wb:
        for k, v in wb.model_dump().items():
            if isinstance(v, str) and v.strip():
                world.append(f"- {k.replace('_', ' ')}: {_clip(v)}")
    add_section("WORLD", world)

    locs = [f"- {l.name} — {_clip(l.description)}" for l in (kb.locations or {}).values()]
    add_section("LOCATIONS", locs)

    lore = [f"- {e.name} ({e.entry_type or 'lore'}) — {_clip(e.description)}"
            for e in (kb.lore_entries or {}).values()]
    add_section("CODEX", lore)

    return "\n\n".join(sections)


def canon_block(kb) -> str:
    """The author's INVIOLABLE canon rules (B32), phrased as binding constraints.
    Empty string when no rules are set."""
    rules = [str(r).strip() for r in (getattr(kb, "canon_rules", None) or []) if str(r).strip()]
    if not rules:
        return ""
    lines = "\n".join(f"- {r}" for r in rules)
    return (
        "=== CANON RULES (INVIOLABLE — never contradict these) ===\n"
        f"{lines}\n"
        "=== end canon rules ===\n"
        "These rules are absolute. Every line you write must comply with them."
    )


def grounding_block(kb, max_tokens: int = 3200) -> str:
    """The digest wrapped in the instruction that makes it binding, plus the canon rules (B32).
    Empty if no lore exists AND no canon rules are set."""
    digest = build_lore_digest(kb, max_tokens)
    canon = canon_block(kb)
    if not digest.strip():
        return canon  # canon rules apply even before any lore exists
    lore = (
        "=== ESTABLISHED LORE (the author's world — build on it) ===\n"
        f"{digest}\n"
        "=== end established lore ===\n"
        "IMPORTANT: This story belongs to the world above. Use these characters, arcs, places, "
        "and facts as the foundation — extend and deepen them. Do NOT invent replacements for "
        "them, rename them, or contradict them. Only introduce new elements where the "
        "established lore has gaps."
    )
    return f"{canon}\n\n{lore}" if canon else lore
