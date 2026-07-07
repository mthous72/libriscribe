"""Publish-ready export (B37, slice 1: DOCX). Pure-offline, no dependencies.

A .docx is a zip of OOXML parts; we emit the minimal set (content types, package rels,
document, basic styles) so Word/LibreOffice/Google Docs open it cleanly. Chapters become
Heading 1 sections; the title page uses the Title style. EPUB is the next slice; PDF is
explicitly delayed (per the locked order DOCX → EPUB → PDF).
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>
<w:rPr><w:b/><w:sz w:val="56"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>
<w:pPr><w:pageBreakBefore/><w:spacing w:after="240"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>
</w:styles>"""

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _para(text: str, style: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    if not text.strip():
        return f"<w:p>{ppr}</w:p>"
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _strip_md(line: str) -> str:
    """Light markdown cleanup for prose lines (bold/italic markers)."""
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"\*(.+?)\*", r"\1", line)
    return line


def _read_chapters(project_dir: Path) -> list[tuple[int, str]]:
    """(chapter_number, text) sorted; prefers *_revised.md over the base file."""
    best: dict[int, tuple[bool, str]] = {}
    for f in project_dir.glob("chapter_*.md"):
        if f.name.endswith("_original.md"):
            continue
        try:
            n = int(f.stem.split("_")[1])
        except (ValueError, IndexError):
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if not t.strip():
            continue
        revised = "revised" in f.name
        prev = best.get(n)
        if prev is None or (revised and not prev[0]):
            best[n] = (revised, t)
    return [(n, best[n][1]) for n in sorted(best)]


def build_docx(kb, project_dir: Path) -> bytes | None:
    """Assemble the manuscript into a .docx (title page + one Heading-1 section per chapter).
    None when there are no chapters yet."""
    chapters = _read_chapters(Path(project_dir))
    if not chapters:
        return None

    body: list[str] = [_para(kb.title or "Untitled", style="Title")]
    if getattr(kb, "logline", "") and kb.logline != "No logline available":
        body.append(_para(kb.logline))
    body.append(_para(""))

    for n, text in chapters:
        title = f"Chapter {n}"
        lines = text.splitlines()
        prose_lines: list[str] = []
        for ln in lines:
            if ln.startswith("#"):
                heading = ln.lstrip("#").strip()
                if heading and title == f"Chapter {n}" and not prose_lines:
                    title = heading if heading.lower().startswith("chapter") else f"Chapter {n}: {heading}"
                    continue
            prose_lines.append(ln)
        body.append(_para(title, style="Heading1"))
        for para_text in re.split(r"\n\s*\n", "\n".join(prose_lines)):
            cleaned = _strip_md(" ".join(para_text.split()))
            if cleaned.strip():
                body.append(_para(cleaned))

    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{"".join(body)}</w:body></w:document>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("word/document.xml", document)
    return buf.getvalue()
