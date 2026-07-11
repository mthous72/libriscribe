"""Split (and later splice) chapter prose at the ``### Scene N`` markers (B45).

ChapterWriterAgent writes chapter files as::

    ## Chapter N: Title

    ### Scene 1

    <prose>

    ### Scene 2

    <prose>

Pre-B39 files (and hand-pasted prose) may have no scene markers at all; those are
reported as ``unstructured`` and callers fall back to chapter-level editing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

_SCENE_MARKER = re.compile(r"^###\s+Scene\s+(\d+)\s*$", re.MULTILINE)


@dataclass
class SceneBlock:
    scene_number: int
    body: str  # prose only — no "### Scene N" marker line

    @property
    def word_count(self) -> int:
        return len(self.body.split())


@dataclass
class ChapterSplit:
    header: str = ""  # everything before the first scene marker (chapter heading etc.)
    scenes: List[SceneBlock] = field(default_factory=list)
    unstructured: bool = False  # prose exists but carries no scene markers

    def get_scene(self, scene_number: int) -> Optional[SceneBlock]:
        for block in self.scenes:
            if block.scene_number == scene_number:
                return block
        return None


def split_chapter(text: str) -> ChapterSplit:
    """Parse chapter prose into header + per-scene blocks.

    Tolerant by design: empty text -> empty split; text without markers ->
    ``unstructured=True`` with everything kept in ``header``.
    """
    if not text or not text.strip():
        return ChapterSplit()

    markers = list(_SCENE_MARKER.finditer(text))
    if not markers:
        return ChapterSplit(header=text, unstructured=True)

    header = text[: markers[0].start()].rstrip("\n")
    scenes: List[SceneBlock] = []
    for i, m in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        body = text[m.end():end].strip("\n")
        scenes.append(SceneBlock(scene_number=int(m.group(1)), body=body))
    return ChapterSplit(header=header, scenes=scenes)


def splice_scene(text: str, scene_number: int, new_body: str,
                 chapter_number: int | None = None, chapter_title: str = "") -> str:
    """Replace (or insert, in numeric order) ONE scene's body; every other byte survives.

    Empty/missing text gets a fresh chapter scaffold. Prose without scene markers is
    REFUSED (ValueError) — splicing into an unstructured chapter would eat the author's text.
    """
    split = split_chapter(text or "")
    if split.unstructured:
        raise ValueError("Chapter has no scene markers — edit it at the chapter level instead.")

    header = split.header
    if not header.strip():
        title = f": {chapter_title}" if chapter_title else ""
        header = f"## Chapter {chapter_number}{title}" if chapter_number else ""

    body = (new_body or "").strip("\n")
    blocks = {b.scene_number: b.body for b in split.scenes}
    blocks[scene_number] = body

    parts = [header] if header else []
    for n in sorted(blocks):
        parts.append(f"### Scene {n}\n\n{blocks[n]}")
    return "\n\n".join(parts) + "\n"


def read_chapter_split(project_dir: Union[str, Path], chapter_number: int) -> Optional[ChapterSplit]:
    """Load the chapter file (revised preferred) and split it; None if no file."""
    from libriscribe.utils.file_utils import resolve_chapter_path, read_markdown_file

    path = resolve_chapter_path(project_dir, chapter_number)
    if not path.exists():
        return None
    return split_chapter(read_markdown_file(str(path)))
