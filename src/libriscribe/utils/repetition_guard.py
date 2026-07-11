"""B40 — deterministic repetition guard.

Instruction-only steering ("don't reuse imagery") is too weak for small local models: the
bake-off chapter opened 3 of 5 scenes with the same establishing shot and reused "heart
hammering against his ribs" four times despite the continuity rules. Small models DO follow
explicit named bans, so this module scans the prose written so far, extracts the distinctive
phrases that are already overused plus each prior scene's opening image, and renders them as
a literal ban list for the next scene's prompt (or as an overuse report for rewrite passes).

Pure functions, no LLM calls — the guard is deterministic by design.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Words that don't make a phrase "distinctive" on their own.
_STOPWORDS = frozenset(
    """a an and are as at back be been before but by could did do down for from had has have
    he her hers him his i if in into is it its just like me my no not now of off on onto or
    out over she so than that the their them then there they this through to too up was were
    what when where which while who will with would you your
    against across toward towards beneath above below between behind around within without
    upon under over onto off near still even only more most some any each every very much
    wasn't didn't couldn't wouldn't shouldn't don't doesn't can't won't isn't aren't it's
    that's he's she's there's i'm you're we're they're something anything nothing""".split()
)

_SCENE_SPLIT = re.compile(r"^(?:#{1,6}\s*Scene\s+\d+.*|\*\*Scene\s+\d+:.*\*\*)\s*$", re.M)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s")
_WORD = re.compile(r"[A-Za-z’']+")

MAX_BANNED_PHRASES = 12
MAX_OPENINGS = 6
NGRAM_RANGE = (3, 5)


def _proper_nouns(text: str) -> set[str]:
    """Words that appear capitalized mid-sentence — names/places that recur legitimately
    and must never push a phrase onto the ban list."""
    nouns: set[str] = set()
    for m in re.finditer(r"(?<![.!?\"”'’]\s)(?<!^)\b([A-Z][a-z’']+)", text):
        nouns.add(m.group(1).lower())
    return nouns


def _strip_structure(text: str) -> str:
    """Remove heading/scene-marker lines so scaffolding never enters the analysis."""
    return "\n".join(
        ln for ln in text.splitlines()
        if not ln.strip().startswith("#") and not _SCENE_SPLIT.match(ln)
    )


def _tokenize(text: str) -> list[list[str]]:
    """Lowercased word runs per sentence — n-grams never span sentence or paragraph
    boundaries."""
    sentences: list[str] = []
    for para in _strip_structure(text).split("\n"):
        sentences.extend(_SENTENCE_END.split(para))
    return [[w.lower() for w in _WORD.findall(s)] for s in sentences if s.strip()]


def overused_phrases(text: str) -> list[str]:
    """Distinctive word n-grams (3-5 words) repeated in the text, most-overused first.

    A phrase qualifies with >=2 content words at 2+ occurrences, or >=1 content word at 3+
    occurrences ("as if burned"). Content words exclude stopwords and proper nouns, so
    character and place names never get banned. Sub-phrases of a kept phrase are dropped.
    """
    if not text or not text.strip():
        return []
    names = _proper_nouns(text)
    counts: dict[tuple[str, ...], int] = {}
    for words in _tokenize(text):
        for n in range(NGRAM_RANGE[0], NGRAM_RANGE[1] + 1):
            for i in range(len(words) - n + 1):
                gram = tuple(words[i : i + n])
                counts[gram] = counts.get(gram, 0) + 1

    def content_words(gram: tuple[str, ...]) -> int:
        return sum(1 for w in gram if w not in _STOPWORDS and w not in names)

    candidates = [
        (gram, cnt)
        for gram, cnt in counts.items()
        if (cnt >= 2 and content_words(gram) >= 2) or (cnt >= 3 and content_words(gram) >= 1)
    ]
    # Most-repeated first; among equal counts prefer the longest wording.
    candidates.sort(key=lambda gc: (-gc[1], -len(gc[0])))

    kept: list[str] = []
    for gram, _cnt in candidates:
        phrase = " ".join(gram)
        if any(phrase in k or k in phrase for k in kept):
            continue
        kept.append(phrase)
        if len(kept) >= MAX_BANNED_PHRASES * 2:  # merge below shrinks the list
            break
    return _merge_staggered(kept)[:MAX_BANNED_PHRASES]


def _merge_staggered(phrases: list[str]) -> list[str]:
    """A phrase longer than the n-gram window surfaces as several staggered fragments
    ("aside a heavy sheet of" / "a heavy sheet of corrugated" / "heavy sheet of corrugated
    plastic"). Chain-merge fragments that overlap by >=2 words into the full phrase."""
    merged = list(phrases)
    changed = True
    while changed:
        changed = False
        out: list[str] = []
        used = [False] * len(merged)
        for i, a in enumerate(merged):
            if used[i]:
                continue
            aw = a.split()
            progress = True
            while progress:
                progress = False
                for j, b in enumerate(merged):
                    if i == j or used[j]:
                        continue
                    bw = b.split()
                    for k in range(min(len(aw), len(bw)) - 1, 1, -1):
                        if aw[-k:] == bw[:k]:
                            aw = aw + bw[k:]
                            used[j] = True
                            changed = progress = True
                            break
                        if bw[-k:] == aw[:k]:
                            aw = bw + aw[k:]
                            used[j] = True
                            changed = progress = True
                            break
                    if progress:
                        break
            used[i] = True
            out.append(" ".join(aw))
        merged = out
    final: list[str] = []
    for p in sorted(merged, key=len, reverse=True):
        if not any(p in q for q in final):
            final.append(p)
    return final


def overused_words(text: str, min_count: int = 6, per_thousand: float = 2.5) -> list[str]:
    """Single content words repeated conspicuously often ("skin" x19 in one chapter) —
    invisible to the phrase detector. Name- and stopword-aware, most-overused first."""
    if not text or not text.strip():
        return []
    from collections import Counter
    names = _proper_nouns(text)
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return []
    threshold = max(min_count, int(len(words) / 1000 * per_thousand))
    counts = Counter(w for w in words if len(w) > 3 and w not in _STOPWORDS and w not in names)
    return [w for w, n in counts.most_common() if n >= threshold][:10]


def scene_openings(text: str) -> list[str]:
    """The first sentence of each scene in the prose (splitting on '### Scene N' /
    legacy bold markers; a markerless text counts as one scene)."""
    openings: list[str] = []
    for section in _SCENE_SPLIT.split(text):
        section = section.strip()
        if not section:
            continue
        first_line = next(
            (ln for ln in section.splitlines() if ln.strip() and not ln.strip().startswith("#")), ""
        )
        sentence = _SENTENCE_END.split(first_line.strip())[0].strip()
        if sentence:
            openings.append(sentence)
    return openings[-MAX_OPENINGS:]


def repetition_guard_block(prior_prose: str) -> str:
    """Ban-list prompt block for the NEXT scene, built from the prose so far.
    Empty string when there is nothing to guard against."""
    text = (prior_prose or "").strip()
    if not text:
        return ""
    phrases = overused_phrases(text)
    openings = scene_openings(text)
    words = overused_words(text)
    if not phrases and not openings and not words:
        return ""
    lines = ["=== REPETITION GUARD (hard constraints) ==="]
    if phrases:
        lines.append(
            "These phrases are ALREADY OVERUSED in the story so far. You are BANNED from "
            "using them, or close variants of them, anywhere in this scene:"
        )
        lines.extend(f'- "{p}"' for p in phrases)
    if words:
        lines.append(
            "These words already appear far too often in the story. Use each AT MOST ONCE "
            "in this scene — find different words: " + ", ".join(words)
        )
    if openings:
        lines.append(
            "Previous scenes opened with the images below. Your scene must open DIFFERENTLY — "
            "a different sense, subject, and sentence shape than ALL of these:"
        )
        lines.extend(f'- "{o}"' for o in openings)
    return "\n".join(lines)


def find_violations(scene_text: str, prior_prose: str) -> list[str]:
    """Deterministic post-generation check: did the new scene reuse banned phrases or open
    like an earlier scene? Named violations feed the one-shot regenerate-with-feedback retry —
    instructions alone are advisory to a small model; this is the enforcement half."""
    if not scene_text or not (prior_prose or "").strip():
        return []
    norm = lambda s: " ".join(w.lower() for w in _WORD.findall(s))
    scene_norm = norm(scene_text)
    violations = []
    for p in overused_phrases(prior_prose):
        if p in scene_norm:
            violations.append(f'reused the banned phrase "{p}"')
    first = ""
    for section in _strip_structure(scene_text).splitlines():
        if section.strip():
            first = _SENTENCE_END.split(section.strip())[0].strip()
            break
    if first:
        for o in scene_openings(prior_prose):
            if SequenceMatcher(None, norm(first), norm(o)).ratio() >= 0.6:
                violations.append(f'opened almost the same way as an earlier scene ("{o[:70]}")')
                break
    return violations


def repetition_report_block(chapter_text: str) -> str:
    """Overuse report for rewrite passes (editor): same detector, framed as fix-this
    guidance instead of a ban. Empty string when the chapter has no overused phrases."""
    phrases = overused_phrases((chapter_text or "").strip())
    if not phrases:
        return ""
    lines = [
        "OVERUSED PHRASES: the following phrases repeat too often in this chapter. Keep at "
        "most ONE occurrence of each and rewrite the rest with fresh wording:"
    ]
    lines.extend(f'- "{p}"' for p in phrases)
    return "\n".join(lines)
