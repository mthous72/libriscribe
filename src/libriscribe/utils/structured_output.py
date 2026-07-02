"""Native structured-output (JSON schema) helpers.

We already ask models for JSON in the prompt and parse robustly (parse_llm_json). This module
lets callers ALSO force valid, correctly-shaped JSON at generation time via each provider's
native structured-output feature. On llama.cpp-backed local servers (LM Studio, Ollama) an
OpenAI-style ``response_format: {type: "json_schema", ...}`` compiles to a GBNF grammar and
constrains decoding at the token level — so even a small local model cannot emit a fence,
preamble, missing key, or non-JSON. It enforces SHAPE, not content, so it complements the
prompt/sorter guidance rather than replacing it.

Everything here is pure (no IO) and provider-agnostic: builders produce a plain JSON Schema
dict; ``llm_client`` wraps it into each provider's native envelope and degrades gracefully if a
provider rejects or ignores it (parse_llm_json remains the universal fallback).
"""
from __future__ import annotations


def json_schema_for_fields(fields: list[str]) -> dict:
    """A flat object schema: each field is a string. Every field is 'required' so the key is
    always present, but an empty string satisfies ``type: string`` — the model can still leave a
    field blank, so grammar constraint never forces a hallucinated value."""
    return {
        "type": "object",
        "properties": {f: {"type": "string"} for f in fields},
        "required": list(fields),
        "additionalProperties": False,
    }


def cats_schema() -> dict:
    """Schema for multi-entity extraction (brainstorm 'Apply to lore', batch import map):
    ``{characters:[{name,...}], locations:[...], lore:[...], arcs:[...]}``. Each entity REQUIRES a
    name (what _normalize_cats keys on) but allows extra fields (reasoning + typed fields), so it
    forces the array-of-named-objects shape without railroading content."""
    entity = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    arr = {"type": "array", "items": entity}
    return {
        "type": "object",
        "properties": {"characters": arr, "locations": arr, "lore": arr, "arcs": arr},
        "required": ["characters", "locations", "lore", "arcs"],
        "additionalProperties": False,
    }


def classify_schema() -> dict:
    """Schema for the per-entry classifier: pick a category, explain briefly, extract fields.

    ``fields`` is intentionally loose (any object) so one schema covers all four categories; the
    caller filters to the chosen type's fields afterward."""
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["character", "location", "lore", "arc"]},
            "reasoning": {"type": "string"},
            "fields": {"type": "object"},
        },
        "required": ["category", "fields"],
        "additionalProperties": False,
    }


# ─── Per-provider envelopes ───────────────────────────────────────────────────
# Each returns the kwargs/params to merge into that provider's request when a schema is active.

def _all_objects_closed(schema) -> bool:
    """True if every object in the schema sets additionalProperties:false. OpenAI 'strict' mode
    requires that (and all keys required); an open object (e.g. our entity items or a loose
    'fields' object) must be non-strict, or strict providers reject it."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" and schema.get("additionalProperties", True) is not False:
            return False
        return all(_all_objects_closed(v) for v in schema.values())
    if isinstance(schema, list):
        return all(_all_objects_closed(v) for v in schema)
    return True


def response_format_openai(schema: dict, name: str = "lore") -> dict:
    """OpenAI-compatible json_schema response_format (OpenAI, OpenRouter, LM Studio, Ollama,
    Mistral). ``strict`` is auto-set: only closed-object schemas can be strict."""
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "schema": schema, "strict": _all_objects_closed(schema)},
    }


def response_format_json_object() -> dict:
    """Best-effort JSON mode for providers without schema support (e.g. DeepSeek)."""
    return {"type": "json_object"}
