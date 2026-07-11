"""B45 Slice 5: downstream-impact hints — the VISIBLE half of the no-cascade guarantee.

No LLM: a word-boundary scan of written chapter prose plus the outline's scene fields,
answering "where is this entity referenced later?" so the author can edit early items with
confidence. Advisory only — no edit endpoint ever triggers regeneration.
"""
from __future__ import annotations

import re
from pathlib import Path


def _pattern(entity_name: str) -> re.Pattern | None:
    name = (entity_name or "").strip()
    if len(name) < 2:
        return None
    return re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.IGNORECASE)


def entity_impact(kb, project_dir: Path, entity_name: str) -> dict:
    """{chapters: [{chapter, mentions}], scenes: [{chapter, scene, fields}], total_mentions}"""
    from libriscribe.utils.file_utils import get_existing_chapter_numbers, resolve_chapter_path, read_markdown_file

    pat = _pattern(entity_name)
    result = {"entity": entity_name, "chapters": [], "scenes": [], "total_mentions": 0}
    if pat is None:
        return result

    for n in get_existing_chapter_numbers(project_dir):
        try:
            text = read_markdown_file(str(resolve_chapter_path(project_dir, n)))
        except Exception:
            continue
        count = len(pat.findall(text))
        if count:
            result["chapters"].append({"chapter": n, "mentions": count})
            result["total_mentions"] += count

    for n in sorted(kb.chapters or {}):
        ch = kb.chapters[n]
        for sc in ch.scenes or []:
            fields = []
            if any(pat.fullmatch(c or "") for c in (sc.characters or [])):
                fields.append("characters")
            for fname in ("summary", "setting", "goal"):
                if pat.search(str(getattr(sc, fname, "") or "")):
                    fields.append(fname)
            if fields:
                result["scenes"].append({"chapter": n, "scene": sc.scene_number, "fields": fields})
    return result
