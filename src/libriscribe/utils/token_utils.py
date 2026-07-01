"""Shared token estimation.

A single home for the word-based token heuristic used for prompt/context budgeting and
usage logging (previously duplicated as `int(len(text.split()) * 1.3)` in several modules).

Note: retrieval chunk sizing uses a separate character-based heuristic (`len(text) // 4`) in
`retrieval/chunking.py`; that is intentional (it sizes chunks, not prompt budgets) and is left
as-is.
"""
from __future__ import annotations

_WORDS_PER_TOKEN_FACTOR = 1.3


def estimate_tokens(text: str) -> int:
    """Rough token count for a block of text (word-count based)."""
    if not text:
        return 0
    return int(len(text.split()) * _WORDS_PER_TOKEN_FACTOR)
