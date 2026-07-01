"""Bring-your-own-reference material (B19).

Authors can import external reference documents (PDF, plain text, markdown) into a project —
a research folder, a style guide, a prior book's "series bible". The text is extracted once and
stored under ``<project>/references/`` with a manifest. Reference content is indexed as a
distinct ``reference`` source so it can *inform* brainstorming and generation without ever
polluting the lorebook (it's never treated as canon, and it's excluded from exports).

Layout::

    <project_dir>/references/
        manifest.json      # [{id, filename, title, added_at, bytes, char_count}]
        <id>.txt           # extracted plain text for each reference
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED_EXT = {".pdf", ".txt", ".md", ".markdown", ".text", ".rst"}


def references_dir(project_dir: Path) -> Path:
    return project_dir / "references"


def _manifest_path(project_dir: Path) -> Path:
    return references_dir(project_dir) / "manifest.json"


def load_manifest(project_dir: Path) -> list[dict]:
    path = _manifest_path(project_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("references", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _save_manifest(project_dir: Path, entries: list[dict]) -> None:
    d = references_dir(project_dir)
    d.mkdir(parents=True, exist_ok=True)
    _manifest_path(project_dir).write_text(json.dumps({"references": entries}, indent=2), encoding="utf-8")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "reference"


def extract_text(filename: str, raw: bytes) -> str:
    """Extract plain text from a supported reference file."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - dependency missing
            raise ValueError(f"PDF support requires pypdf: {exc}") from exc
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if ext in SUPPORTED_EXT or ext == "":
        return raw.decode("utf-8", errors="ignore").strip()
    raise ValueError(f"Unsupported file type '{ext}'. Supported: PDF, TXT, MD.")


def add_reference(project_dir: Path, filename: str, raw: bytes, title: str | None = None) -> dict:
    """Extract, store, and register a reference. Returns its manifest entry."""
    text = extract_text(filename, raw)
    if not text.strip():
        raise ValueError("No text could be extracted from that file.")

    entries = load_manifest(project_dir)
    # Identify a reference by its filename slug: re-uploading the same file replaces it
    # (update an edited draft) rather than accumulating duplicates.
    ref_id = _slug(Path(filename).stem)

    d = references_dir(project_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ref_id}.txt").write_text(text, encoding="utf-8")

    entry = {
        "id": ref_id,
        "filename": filename,
        "title": title or filename,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(raw),
        "char_count": len(text),
    }
    entries = [e for e in entries if e["id"] != ref_id] + [entry]
    _save_manifest(project_dir, entries)
    return entry


def _read_text(project_dir: Path, ref_id: str) -> str:
    path = references_dir(project_dir) / f"{ref_id}.txt"
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def list_references(project_dir: Path) -> list[dict]:
    return load_manifest(project_dir)


def delete_reference(project_dir: Path, ref_id: str) -> bool:
    entries = load_manifest(project_dir)
    if not any(e["id"] == ref_id for e in entries):
        return False
    entries = [e for e in entries if e["id"] != ref_id]
    _save_manifest(project_dir, entries)
    txt = references_dir(project_dir) / f"{ref_id}.txt"
    try:
        if txt.exists():
            txt.unlink()
    except Exception:
        pass
    return True


def build_reference_documents(project_dir: Path):
    """Build RetrievalDocument objects for all references (source_type='reference')."""
    from libriscribe.retrieval.models import RetrievalDocument
    from libriscribe.retrieval.document_builder import compute_sha256

    docs = []
    for entry in load_manifest(project_dir):
        text = _read_text(project_dir, entry["id"])
        if not text.strip():
            continue
        docs.append(RetrievalDocument(
            document_id=f"reference::{entry['id']}",
            project_name=project_dir.name,
            source_type="reference",
            title=entry.get("title") or entry.get("filename") or entry["id"],
            text=text,
            source_path=f"references/{entry['id']}.txt",
            entity_name=None,
            updated_at=entry.get("added_at", ""),
            hash=compute_sha256(text),
        ))
    return docs
