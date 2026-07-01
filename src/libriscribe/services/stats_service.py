"""Readability & manuscript statistics (B14).

Dependency-free, offline text metrics over a project's chapter prose: word / sentence /
paragraph counts, average sentence length, a syllable-based Flesch Reading Ease and
Flesch-Kincaid grade, adverb and dialogue ratios, and estimated reading time — per chapter
and for the whole book (a simple pacing view). No LLM, no network.
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_SENTENCE_RE = re.compile(r"[.!?]+")
_READING_WPM = 220


def _syllables(word: str) -> int:
    """Heuristic syllable count for an English word."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(groups))


def _dialogue_chars(text: str) -> int:
    """Number of characters enclosed in double quotes (straight or smart)."""
    t = text.replace("“", '"').replace("”", '"')
    count, in_q = 0, False
    for ch in t:
        if ch == '"':
            in_q = not in_q
            continue
        if in_q:
            count += 1
    return count


def compute_text_stats(text: str) -> dict:
    """Compute readability + count metrics for a block of plain text."""
    text = text or ""
    words = _WORD_RE.findall(text)
    word_count = len(words)
    sentence_count = max(1, len([s for s in _SENTENCE_RE.split(text) if s.strip()]))
    paragraph_count = max(1, len([p for p in re.split(r"\n\s*\n", text) if p.strip()])) if text.strip() else 0

    if word_count == 0:
        return {
            "word_count": 0, "sentence_count": 0, "paragraph_count": 0,
            "avg_sentence_length": 0.0, "avg_syllables_per_word": 0.0,
            "flesch_reading_ease": 0.0, "flesch_kincaid_grade": 0.0,
            "adverb_ratio": 0.0, "dialogue_ratio": 0.0, "reading_time_min": 0.0,
        }

    syllables = sum(_syllables(w) for w in words)
    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllables / word_count

    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    fk_grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    adverbs = sum(1 for w in words if len(w) > 3 and w.lower().endswith("ly"))
    total_chars = len(text)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_sentence_length": round(words_per_sentence, 1),
        "avg_syllables_per_word": round(syllables_per_word, 2),
        "flesch_reading_ease": round(max(0.0, min(120.0, flesch)), 1),
        "flesch_kincaid_grade": round(max(0.0, fk_grade), 1),
        "adverb_ratio": round(adverbs / word_count, 3),
        "dialogue_ratio": round(_dialogue_chars(text) / total_chars, 3) if total_chars else 0.0,
        "reading_time_min": round(word_count / _READING_WPM, 1),
    }


def project_stats(project_name: str) -> dict | None:
    """Per-chapter + whole-book stats. Returns None if the project is missing."""
    from libriscribe.services.project_service import get_projects_dir, load_kb, _strip_markdown
    from libriscribe.utils.file_utils import get_existing_chapter_numbers, resolve_chapter_path

    project_dir = get_projects_dir() / project_name
    kb = load_kb(project_name)
    if not kb:
        return None

    chapters: list[dict] = []
    all_prose: list[str] = []
    for n in sorted(get_existing_chapter_numbers(project_dir)):
        path = resolve_chapter_path(project_dir, n)
        if not path.exists():
            continue
        prose = _strip_markdown(path.read_text(encoding="utf-8")).strip()
        if not prose:
            continue
        ch = kb.get_chapter(n)
        chapters.append({
            "chapter_number": n,
            "title": (ch.title if ch else "") or "",
            **compute_text_stats(prose),
        })
        all_prose.append(prose)

    overall = compute_text_stats("\n\n".join(all_prose))
    overall["chapter_count"] = len(chapters)
    return {"overall": overall, "chapters": chapters}
