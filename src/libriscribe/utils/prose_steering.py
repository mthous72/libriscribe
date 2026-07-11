"""Shared prose steering — ONE stack for every pass that writes or rewrites prose.

The first-draft scene pass carried canon rules + the prose register, but the editor and
style passes rewrote chapters with bare prompts — no register, no canon, no writing system
prompt — so two "polish" passes normalized the draft right back to generic register. Every
prose pass now pulls the same stack from here.
"""
from __future__ import annotations


def steering_blocks(kb) -> str:
    """Canon rules (B32) + active prose-register directive (B36, gated) — prepend to any
    prose-writing/rewriting prompt. Empty string when neither applies."""
    from libriscribe.services.lore_digest import canon_block
    from libriscribe.utils.style_register import active_register_directive

    blocks = []
    try:
        from libriscribe.settings import Settings
        reg = active_register_directive(kb, Settings())
        if reg:
            blocks.append(reg)
    except Exception:
        pass
    canon = canon_block(kb)
    if canon:
        blocks.append(canon)
    return "\n\n".join(blocks)


def writing_system_prompt(kb) -> str:
    """The system prompt for prose passes: project override → global setting → craft default."""
    from libriscribe.utils.system_prompts import CREATIVE_WRITING_SYSTEM_PROMPT

    if getattr(kb, "writing_system_prompt", ""):
        return kb.writing_system_prompt
    try:
        from libriscribe.settings import Settings
        s = Settings()
        if s.writing_system_prompt:
            return s.writing_system_prompt
    except Exception:
        pass
    return CREATIVE_WRITING_SYSTEM_PROMPT


def _first_last_sentence(prose: str) -> tuple[str, str]:
    import re
    lines = [l.strip() for l in prose.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return "", ""
    first = re.split(r"(?<=[.!?])\s", lines[0])[0].strip()
    last = re.split(r"(?<=[.!?])\s", lines[-1])[-1].strip()
    return first, last


def scene_recap_block(entries) -> str:
    """B40: rolling recap of ALL previously written scenes — (label, beat, prose) triples,
    e.g. ("Chapter 2, Scene 1", <outline summary>, <scene text>).

    The verbatim continuity tail only reaches back a scene or two; this compact digest keeps
    EVERY prior beat and opening visible, so late scenes stop re-running early beats
    (minimizing — not eliminating — repetition across chapters). Deterministic: the planned
    beat comes from the outline, opened/ended lines from the actual prose."""
    lines = []
    for label, beat, prose in entries or []:
        first, last = _first_last_sentence(prose or "")
        line = f"- {label}: {(beat or '').strip()}".rstrip(": ")
        if first:
            line += f'\n  opened with: "{first}"'
        if last and last != first:
            line += f'\n  ended with: "{last}"'
        lines.append(line)
    if not lines:
        return ""
    return (
        "=== EVERY SCENE ALREADY WRITTEN (do not repeat any of this) ===\n"
        + "\n".join(lines)
        + "\nThese beats are DONE. Do not re-run or re-describe any of them. Your scene must "
        "move the story FORWARD from where the last one ended, and must not open with the "
        "same image, sense, or sentence shape as any opening above. If your scene brief "
        "overlaps anything above, skip the overlap — depict only what is NEW."
    )


def continuity_block(prior_prose: str, max_words: int = 2000) -> str:
    """The tail of the prose written immediately before this scene, plus the rules that stop a
    small model from re-describing and recycling imagery (the top cause of repetitive output).
    Empty when there's no prior prose (first scene of chapter 1)."""
    text = (prior_prose or "").strip()
    if not text:
        return ""
    words = text.split()
    tail = " ".join(words[-max_words:])
    return (
        "=== THE STORY SO FAR (the prose immediately before this scene) ===\n"
        f"...{tail}\n"
        "=== end prior prose ===\n"
        "CONTINUITY RULES:\n"
        "- Continue seamlessly from the prose above — no recap, no re-establishing.\n"
        "- Do NOT re-describe settings, appearances, or sensations already established above.\n"
        "- Do NOT reuse distinctive imagery, metaphors, or phrases that appear above — every "
        "scene needs fresh language. If the text above says something 'dropped an octave' or "
        "names a specific smell/sound, find a different detail this time.\n"
        "- Vary sentence rhythm and scene-opening structure relative to the text above."
    )
