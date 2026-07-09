"""Human-directed revision (B34) — rewrite an existing chapter under the author's guidance.

The revise pass NEVER saves: it returns {original, revised} so the UI can show a diff (B35)
and the author explicitly keeps the new text (existing chapter save endpoint) or discards it.
Canon rules (B32) and a light lore grounding bind the rewrite.
"""
from __future__ import annotations

from pathlib import Path


def revise_chapter(client, kb, project_dir: Path, chapter_number: int, guidance: str) -> dict | None:
    """Rewrite chapter N following the author's guidance. Returns {original, revised} or None
    when the chapter file doesn't exist / generation fails. Does NOT write anything."""
    from libriscribe.services.lore_digest import canon_block, grounding_block

    ch_path = Path(project_dir) / f"chapter_{chapter_number}.md"
    if not ch_path.exists():
        return None
    original = ch_path.read_text(encoding="utf-8")
    if not original.strip():
        return None

    canon = canon_block(kb)
    lore = grounding_block(kb, max_tokens=900)
    blocks = [b for b in (canon if canon and not lore else "", lore) if b]

    prompt = (
        ("\n\n".join(blocks) + "\n\n" if blocks else "")
        + f"Revise Chapter {chapter_number} of this {kb.genre} book following the author's "
        "instructions. Preserve the story events, characters, and continuity unless the "
        "instructions say otherwise. Keep roughly the same length unless asked. Return ONLY the "
        "revised chapter text in Markdown — no commentary, no preamble.\n\n"
        f"AUTHOR'S REVISION INSTRUCTIONS:\n{guidance.strip() or 'Improve the prose quality.'}\n\n"
        f"CHAPTER {chapter_number} (original):\n{original[:48000]}"
    )
    system_prompt = None
    if getattr(kb, "writing_system_prompt", ""):
        system_prompt = kb.writing_system_prompt

    revised = client.generate_content(
        prompt, max_tokens=8000, temperature=0.7, system_prompt=system_prompt
    )
    if not revised or not revised.strip():
        return None
    return {"original": original, "revised": revised.strip()}
