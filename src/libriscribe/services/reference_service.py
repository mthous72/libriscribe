"""Bring-your-own-reference material (B19) + OCR (B20).

Authors can import external reference documents (PDF, plain text, markdown, and — via OCR —
scanned PDFs and images) into a project: a research folder, a style guide, a prior book's
"series bible". Text is extracted once and stored under ``<project>/references/`` with a
manifest. Reference content is indexed as a distinct ``reference`` source so it can *inform*
brainstorming and generation without ever polluting the lorebook, and it's excluded from
exports.

Extraction strategy:
- ``.txt/.md/...``           -> decode directly.
- ``.pdf``                   -> pypdf text layer; pages with little/no text are rasterized
                                (PyMuPDF) and OCR'd (Tesseract) for scanned documents.
- images (``.png/.jpg/...``) -> OCR directly (Tesseract).

OCR needs the **Tesseract** binary plus ``pytesseract`` + ``pymupdf``. When OCR isn't
available, text/text-PDF imports still work; scanned/image imports fail with a clear message.

Because OCR is slow, uploads are processed in the background: a reference starts with
``status="processing"`` and flips to ``"ready"`` (or ``"error"``) when extraction finishes.

Layout::

    <project_dir>/references/
        manifest.json      # [{id, filename, title, added_at, bytes, char_count, status, ocr, error}]
        <id>.txt           # extracted plain text (once ready)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TEXT_EXT = {".txt", ".md", ".markdown", ".text", ".rst"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}
SUPPORTED_EXT = TEXT_EXT | IMAGE_EXT | {".pdf"}

# A page with fewer than this many characters of text layer is treated as "needs OCR".
_MIN_PAGE_CHARS = 20


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


def _update_entry(project_dir: Path, ref_id: str, **fields) -> None:
    entries = load_manifest(project_dir)
    for e in entries:
        if e["id"] == ref_id:
            e.update(fields)
            break
    _save_manifest(project_dir, entries)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "reference"


# ─── Tesseract / OCR ──────────────────────────────────────────────────────────

def _configure_tesseract() -> None:
    """Point pytesseract at the Tesseract binary: $TESSERACT_CMD, a bundled copy next to
    the app (installer places one there), or rely on PATH."""
    try:
        import pytesseract
    except Exception:
        return
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd and Path(cmd).exists():
        pytesseract.pytesseract.tesseract_cmd = cmd
        return
    exe_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for cand in (
        exe_dir / "tesseract" / "tesseract.exe",
        exe_dir / "tesseract.exe",
        Path(sys.executable).parent / "tesseract" / "tesseract.exe",
    ):
        if cand.exists():
            pytesseract.pytesseract.tesseract_cmd = str(cand)
            return


def ocr_available() -> bool:
    """True if OCR can run (libraries importable and the Tesseract binary reachable)."""
    try:
        import pytesseract  # noqa: F401
        import fitz  # noqa: F401  (pymupdf)
        from PIL import Image  # noqa: F401

        _configure_tesseract()
        import pytesseract as pt
        pt.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_image(img) -> str:
    import pytesseract
    _configure_tesseract()
    return pytesseract.image_to_string(img)


def _ocr_image_bytes(raw: bytes) -> str:
    if not ocr_available():
        raise ValueError(
            "This looks like a scanned/image file, but OCR isn't available. Install Tesseract "
            "OCR (and the pytesseract + pymupdf packages) to import scanned documents."
        )
    from PIL import Image
    return _ocr_image(Image.open(io.BytesIO(raw)))


def _extract_pdf(raw: bytes) -> tuple[str, bool]:
    """Extract text from a PDF: use the text layer, OCR pages that lack one."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages_text = [(page.extract_text() or "") for page in reader.pages]
    total_chars = sum(len(t.strip()) for t in pages_text)

    # Good text layer, or OCR unavailable -> return whatever text we have.
    if total_chars >= max(40, _MIN_PAGE_CHARS * len(pages_text)) or not ocr_available():
        return "\n\n".join(pages_text).strip(), False

    # Scanned / sparse: OCR the pages that need it, keep the text layer where present.
    import fitz
    from PIL import Image

    doc = fitz.open(stream=raw, filetype="pdf")
    out: list[str] = []
    used_ocr = False
    for i, t in enumerate(pages_text):
        if len(t.strip()) >= _MIN_PAGE_CHARS or i >= doc.page_count:
            out.append(t)
            continue
        pix = doc[i].get_pixmap(dpi=300)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out.append(_ocr_image(img))
        used_ocr = True
    return "\n\n".join(out).strip(), used_ocr


def extract_text_with_ocr(filename: str, raw: bytes) -> tuple[str, bool]:
    """Return (text, used_ocr) for a reference file."""
    ext = Path(filename).suffix.lower()
    if ext in TEXT_EXT or ext == "":
        return raw.decode("utf-8", errors="ignore").strip(), False
    if ext == ".pdf":
        return _extract_pdf(raw)
    if ext in IMAGE_EXT:
        return _ocr_image_bytes(raw).strip(), True
    raise ValueError(f"Unsupported file type '{ext}'. Supported: PDF, TXT, MD, and images (with OCR).")


def extract_text(filename: str, raw: bytes) -> str:
    """Extract plain text (OCR applied as needed). Returns just the text."""
    return extract_text_with_ocr(filename, raw)[0]


# ─── Add / process / list / delete ────────────────────────────────────────────

def _write_text(project_dir: Path, ref_id: str, text: str) -> None:
    d = references_dir(project_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ref_id}.txt").write_text(text, encoding="utf-8")


def add_reference(project_dir: Path, filename: str, raw: bytes, title: str | None = None) -> dict:
    """Synchronously extract, store, and register a reference. Returns its manifest entry.

    Re-uploading the same filename replaces the prior reference (edited draft) rather than
    accumulating duplicates."""
    text, used_ocr = extract_text_with_ocr(filename, raw)
    if not text.strip():
        raise ValueError("No text could be extracted from that file.")

    ref_id = _slug(Path(filename).stem)
    _write_text(project_dir, ref_id, text)
    entry = {
        "id": ref_id,
        "filename": filename,
        "title": title or filename,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(raw),
        "char_count": len(text),
        "status": "ready",
        "ocr": used_ocr,
    }
    entries = [e for e in load_manifest(project_dir) if e["id"] != ref_id] + [entry]
    _save_manifest(project_dir, entries)
    return entry


def register_pending(project_dir: Path, filename: str, raw: bytes, title: str | None = None) -> dict:
    """Register a reference as 'processing' before (slow) extraction runs in the background."""
    ref_id = _slug(Path(filename).stem)
    entry = {
        "id": ref_id,
        "filename": filename,
        "title": title or filename,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(raw),
        "char_count": 0,
        "status": "processing",
        "ocr": False,
    }
    entries = [e for e in load_manifest(project_dir) if e["id"] != ref_id] + [entry]
    _save_manifest(project_dir, entries)
    # Drop any stale extracted text from a previous version.
    old = references_dir(project_dir) / f"{ref_id}.txt"
    try:
        if old.exists():
            old.unlink()
    except Exception:
        pass
    return entry


def finalize(project_dir: Path, ref_id: str, filename: str, raw: bytes) -> bool:
    """Run extraction (with OCR) and flip the reference to 'ready' or 'error'."""
    try:
        text, used_ocr = extract_text_with_ocr(filename, raw)
        if not text.strip():
            raise ValueError("No text could be extracted (empty or unreadable file).")
        _write_text(project_dir, ref_id, text)
        _update_entry(project_dir, ref_id, status="ready", char_count=len(text), ocr=used_ocr, error=None)
        return True
    except Exception as exc:
        _update_entry(project_dir, ref_id, status="error", error=str(exc))
        return False


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
    _save_manifest(project_dir, [e for e in entries if e["id"] != ref_id])
    txt = references_dir(project_dir) / f"{ref_id}.txt"
    try:
        if txt.exists():
            txt.unlink()
    except Exception:
        pass
    return True


def build_reference_documents(project_dir: Path):
    """Build RetrievalDocument objects for all ready references (source_type='reference')."""
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
