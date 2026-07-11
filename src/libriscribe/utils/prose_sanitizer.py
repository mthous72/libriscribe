"""Deterministic prose sanitation (B39 Slice B) — applied to every generated or revised scene.

Local models emit inconsistent text artifacts scene-to-scene: UTF-8-as-cp1252 mojibake
("â€”" where an em dash belongs), mixed "--"/em-dash usage, stray paragraph-leading
hyphens ("-No scuffs"), and mid-word caps tics ("CEE'S"). None of these are fixable by
prompting reliably, so every prose pass runs this pure-function pipeline before storing text.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Longest-first: "â€œ" must win before the bare "â€" fallback.
_MOJIBAKE_MAP = [
    ("â€�", "”"),  # right double quote whose 0x9D byte became U+FFFD
    ("â€”", "—"),  # â€” -> em dash
    ("â€“", "–"),  # â€“ -> en dash
    ("â€™", "’"),  # â€™ -> right single quote
    ("â€˜", "‘"),  # â€˜ -> left single quote
    ("â€œ", "“"),  # â€œ -> left double quote
    ("â€¦", "…"),  # â€¦ -> ellipsis
    ("â€", "”"),  # â€\x9d -> right double quote
    ("â€", "”"),        # bare â€ (0x9D byte lost) -> right double quote
    ("Ã©", "é"),  # Ã© -> é
    ("Ã¨", "è"),  # Ã¨ -> è
    ("Ãª", "ê"),  # Ãª -> ê
    ("Ã«", "ë"),  # Ã« -> ë
    ("Ã¡", "á"),  # Ã¡ -> á
    ("Ã¢", "â"),  # Ã¢ -> â
    ("Ã¤", "ä"),  # Ã¤ -> ä
    ("Ã³", "ó"),  # Ã³ -> ó
    ("Ã´", "ô"),  # Ã´ -> ô
    ("Ã¶", "ö"),  # Ã¶ -> ö
    ("Ãº", "ú"),  # Ãº -> ú
    ("Ã»", "û"),  # Ã» -> û
    ("Ã¼", "ü"),  # Ã¼ -> ü
    ("Ã±", "ñ"),  # Ã± -> ñ
    ("Ã§", "ç"),  # Ã§ -> ç
    ("Ã­", "í"),  # Ã­ -> í
    ("Ã¯", "ï"),  # Ã¯ -> ï
    ("Ã®", "î"),  # Ã® -> î
    ("Â ", " "),       # Â + nbsp -> space
]

# An em dash whose trailing cp1252 bytes were stripped in transit leaves a lone "â"
# jammed between two words ("scrapâthe").
_LONE_A_CIRCUMFLEX = re.compile(r"(?<=[A-Za-z])â(?=[A-Za-z])")
_STRAY_A_CIRCUMFLEX = re.compile(r"Â(?=\s)|(?<=\s)Â")

# 2+ hyphens used as a dash inside prose. Line-leading runs (markdown rules/frontmatter)
# are excluded by the guard in _normalize_dashes.
_DASH_RUN = re.compile(r"[ \t]*-{2,}[ \t]*")
_HR_LINE = re.compile(r"^\s*-{3,}\s*$")

# "-No scuffs" — a hyphen glued to a capital/quote at line start OR after a sentence break
# is a model tic, while a markdown list item always has a space after the hyphen.
_STRAY_LEAD_HYPHEN = re.compile(r"(?:^|(?<=[.!?”\"']\s))-(?=[A-Z“‘\"'])", re.M)

# CEE'S -> CEE's (possessive S wrongly capitalized after an all-caps name).
_CAPS_POSSESSIVE = re.compile(r"\b([A-Z][A-Z0-9]+)(['’])S\b")

# Scene label lines a model may still emit despite instructions.
_SCENE_LABEL = re.compile(r"^\s*(?:\*{1,2}|#{1,6}\s*)?Scene\s+\d+\s*[:.—-]?.*?(?:\*{1,2})?\s*$", re.I)


def fix_mojibake(text: str) -> str:
    """Repair the common UTF-8-read-as-cp1252 sequences; falls back to ftfy when installed."""
    try:
        import ftfy  # optional dependency
        text = ftfy.fix_text(text)
    except ImportError:
        pass
    for bad, good in _MOJIBAKE_MAP:
        text = text.replace(bad, good)
    text = _LONE_A_CIRCUMFLEX.sub("—", text)
    text = _STRAY_A_CIRCUMFLEX.sub("", text)
    return text


def _normalize_dashes(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        if _HR_LINE.match(line) or line.lstrip().startswith(("-", "*", "#")):
            lines.append(line)
            continue
        lines.append(_DASH_RUN.sub("—", line))
    return "\n".join(lines)


def normalize_punctuation(text: str) -> str:
    """Unify dash style (unspaced em dash), fix stray leading hyphens and caps tics."""
    text = _normalize_dashes(text)
    text = re.sub(r"[ \t]*—[ \t]*", "—", text)
    text = _STRAY_LEAD_HYPHEN.sub("", text)
    text = _CAPS_POSSESSIVE.sub(lambda m: f"{m.group(1)}{m.group(2)}s", text)
    return text


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*|<reasoning>.*?</reasoning>\s*", re.S | re.I)


def sanitize_prose(text: str) -> str:
    """The full deterministic pipeline. Safe to run repeatedly (idempotent)."""
    if not text:
        return text
    text = _THINK_BLOCK.sub("", text)  # reasoning-model chain-of-thought never reaches prose
    text = fix_mojibake(text)
    text = normalize_punctuation(text)
    text = normalize_whitespace(text)
    return text


def _similar(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"\W+", " ", s).lower().strip()
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def strip_summary_echo(text: str, scene_summary: str) -> str:
    """Drop leaked outline scaffolding from the head of a generated scene: 'Scene N: ...'
    label lines, and an opening line that just restates the scene summary."""
    if not text:
        return text
    lines = text.split("\n")
    i = 0
    dropped_label = True
    while dropped_label and i < len(lines):
        dropped_label = False
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and _SCENE_LABEL.match(lines[i]):
            i += 1
            dropped_label = True
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and scene_summary:
        first = lines[i].strip().strip("*_# ")
        summary = scene_summary.strip()
        f, s = first.rstrip(".…").lower(), summary.rstrip(".…").lower()
        is_echo = first and (
            _similar(first, summary) >= 0.7
            or (len(first) > 20 and (s.startswith(f) or f.startswith(s)))
        )
        if is_echo:
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
    return "\n".join(lines[i:]) if i else text
