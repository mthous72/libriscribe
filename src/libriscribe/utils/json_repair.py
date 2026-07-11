"""B43 — automatic repair for damaged import JSON.

Import files that were hand-edited or round-tripped through an external tool arrive with a
recurring set of defects (all observed in real user files):

- UTF-8 BOM (Windows editors) — JSON parsers reject it.
- Orphan duplicate blocks: an edit/merge leaves an old ``"key": ...`` block dangling AFTER
  its object already closed, dragging in an extra closing brace that ends the document early
  ("Extra data").
- Missing commas between members ("Expecting ',' delimiter").
- Trailing commas before a closing brace/bracket ("Expecting property name...").
- Mojibake in string values (em dashes mangled to "â..." in earlier round-trips).

``repair_json`` fixes what it safely can and returns the parsed data together with a
human-readable list of every repair made — imports surface that list so the user knows the
file was not taken verbatim. Unrepairable input raises the ORIGINAL JSONDecodeError.
"""
from __future__ import annotations

import json
import re
from typing import Any

MAX_PASSES = 40

_ORPHAN_KEY = re.compile(r'^(\s*)"[^"]+":')


def repair_json(raw: str) -> tuple[Any, list[str]]:
    """Parse ``raw`` as JSON, applying targeted repairs on failure.
    Returns (data, repairs). Raises json.JSONDecodeError when unrepairable."""
    repairs: list[str] = []
    text = raw

    if text.startswith("﻿"):
        text = text.lstrip("﻿")
        repairs.append("removed UTF-8 byte-order mark")

    try:
        original_error = None
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        original_error = exc
        text, orphan_fixes = _remove_orphan_blocks(text)
        repairs.extend(orphan_fixes)
        data = None

    if data is None:
        for _ in range(MAX_PASSES):
            try:
                data = json.loads(text)
                break
            except json.JSONDecodeError as exc:
                fixed = _fix_one(text, exc, repairs)
                if fixed is None:
                    raise original_error or exc
                text = fixed
        else:
            raise original_error or json.JSONDecodeError("unrepairable", text, 0)

    data, mojibake_count = _fix_mojibake_strings(data)
    if mojibake_count:
        repairs.append(f"repaired mojibake text in {mojibake_count} field(s)")

    return data, repairs


def _fix_one(text: str, exc: json.JSONDecodeError, repairs: list[str]) -> str | None:
    """Apply ONE targeted fix for the decoder error, or None when unhandled."""
    if "Expecting ',' delimiter" in exc.msg:
        # walk back over whitespace to the end of the previous token and insert the comma
        k = exc.pos - 1
        while k > 0 and text[k] in " \t\r\n":
            k -= 1
        repairs.append(f"inserted missing comma (line {exc.lineno})")
        return text[: k + 1] + "," + text[k + 1 :]

    if ("Expecting property name" in exc.msg or "Expecting value" in exc.msg
            or "trailing comma" in exc.msg.lower()):
        # a trailing comma right before a closing brace/bracket (Python ≥3.13 names it
        # explicitly as "Illegal trailing comma"; older versions report the next token)
        k = min(exc.pos, len(text) - 1)
        while k > 0 and text[k] != ",":
            k -= 1
        if k > 0 and text[k] == ",":
            repairs.append(f"removed trailing comma (line {exc.lineno})")
            return text[:k] + text[k + 1 :]
        return None

    if "Extra data" in exc.msg:
        remainder = text[exc.pos :]
        if not remainder.strip():
            return text[: exc.pos]
        # try orphan-block removal again in case earlier fixes exposed new ones
        fixed, orphan_fixes = _remove_orphan_blocks(text)
        if orphan_fixes:
            repairs.extend(orphan_fixes)
            return fixed
        return None

    return None


def _remove_orphan_blocks(text: str) -> tuple[str, list[str]]:
    """Remove duplicate blocks left dangling after their object closed.

    Signature (from real files, pretty-printed JSON): a ``"key":`` line whose previous
    non-blank line is ``}`` or ``},`` at a SHALLOWER indent — a sibling key cannot sit
    deeper than the brace that just closed, so the block is merge debris. The block runs
    until bracket depth goes negative (the stray closing brace it drags along)."""
    lines = text.splitlines(keepends=True)
    fixes: list[str] = []

    def orphan_starts() -> list[int]:
        starts = []
        for i in range(1, len(lines)):
            m = _ORPHAN_KEY.match(lines[i])
            if not m:
                continue
            prev = lines[i - 1]
            if prev.strip() not in ("}", "},"):
                continue
            prev_indent = len(prev) - len(prev.lstrip())
            if len(m.group(1)) > prev_indent:
                starts.append(i)
        return starts

    for start in reversed(orphan_starts()):
        depth = 0
        in_string = False
        escape = False
        end = None
        for j in range(start, len(lines)):
            for ch in lines[j]:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = in_string
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch in "{[":
                    depth += 1
                elif ch in "}]":
                    depth -= 1
            if depth < 0:
                end = j
                break
        if end is None:
            continue
        key = lines[start].strip().split(":", 1)[0].strip('" ')
        fixes.append(
            f'removed orphan duplicate "{key}" block (lines {start + 1}-{end + 1})'
        )
        del lines[start : end + 1]

    return "".join(lines), fixes


def _fix_mojibake_strings(data: Any) -> tuple[Any, int]:
    """Walk the parsed structure and repair mojibake inside string values (and keys)."""
    from libriscribe.utils.prose_sanitizer import fix_mojibake

    count = 0

    def walk(value: Any) -> Any:
        nonlocal count
        if isinstance(value, str):
            fixed = fix_mojibake(value)
            if fixed != value:
                count += 1
            return fixed
        if isinstance(value, dict):
            return {walk(k): walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    return walk(data), count
