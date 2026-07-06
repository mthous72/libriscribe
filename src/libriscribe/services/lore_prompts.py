"""Prompt builders for smart lore intake (the "base contextual prompt starter" + "sorter").

Each LLM call in the lore pipeline (import classification, batch map, per-type field
extraction, brainstorm extraction) shares a common contract:

- a **base system prompt** framing the model as a lorebook librarian that returns ONLY a
  fenced ```json object (matches :func:`libriscribe.utils.file_utils.parse_llm_json`);
- a **sorter instruction** telling it to ignore game-state / chat / markdown noise and pull
  only stated facts about the target entity;
- a **concrete JSON example** rendered from the type's field list, so the model sees the exact
  output shape and each field's meaning (the single most reliable pattern in this codebase).

This module is pure (no IO, no LLM, no imports from ``lore_intake``) so it can be unit-tested
directly and reused without circular imports. It is the single source of truth for the
prompt-facing field lists (``TYPE_FIELDS``); ``lore_intake.SMART_FIELDS`` aliases it.
"""
from __future__ import annotations

import json

# type key -> the "interesting" fields the model is asked to populate (subset of the model).
TYPE_FIELDS = {
    "character": [
        "role", "age", "sex", "sexual_orientation", "physical_description",
        "personality_traits", "background", "motivations", "internal_conflicts",
        "external_conflicts", "character_arc",
    ],
    "location": ["description", "significance"],
    "lore": ["entry_type", "description", "significance"],
    "arc": ["arc_type", "description", "resolution_notes"],
}

# The character's dialogue VoiceProfile (nested on the model). Extracted by a dedicated pass and
# assembled into `voice_profile` on merge — used by the chapter writer to keep dialogue in voice.
VOICE_FIELDS = ["speech_patterns", "vocabulary_level", "verbal_tics", "avoids", "example_dialogue"]

# One-line meaning for each field, shown in the prompt so content lands in the right place
# (instead of everything collapsing into background/description).
FIELD_DESCRIPTIONS = {
    "role": "role or function in the story (e.g. protagonist, mentor, android servant)",
    "physical_description": "physical appearance — body, face, clothing, distinguishing features",
    "personality_traits": "temperament, disposition, notable traits and quirks",
    "background": "history, origin, backstory, and formative events",
    "motivations": "goals, desires, drives — what this entity wants",
    "internal_conflicts": "inner struggles — doubts, guilt, competing desires, and self-doubt within the character",
    "external_conflicts": "conflicts with other people, forces, institutions, or circumstances",
    "character_arc": "how the entity changes, or is expected to change, across the story",
    "age": "the character's age",
    "sex": "the character's sex or gender (e.g. male, female, nonbinary, intersex)",
    "sexual_orientation": "the character's sexual orientation (e.g. heterosexual, gay, bisexual, asexual)",
    "description": "a clear description of what this is",
    "significance": "why it matters to the story or world",
    "entry_type": "the kind of thing this is (e.g. faction, item, technology, concept, event, rule)",
    "arc_type": "the kind of arc (e.g. redemption, mystery, romance, coming-of-age)",
    "resolution_notes": "how the arc resolves, or is intended to resolve",
    # Dialogue voice (VoiceProfile)
    "speech_patterns": "how they structure sentences (e.g. short clipped sentences, formal with subordinate clauses, rambling with digressions)",
    "vocabulary_level": "word-choice level (e.g. street slang, academic, plain and direct, archaic formal)",
    "verbal_tics": "recurring speech habits (e.g. says 'right?' after statements, clears throat, uses nautical metaphors)",
    "avoids": "words or patterns this character would NEVER use (e.g. never swears, avoids contractions, no slang)",
    "example_dialogue": "2-3 example lines this character might actually say, one per line, demonstrating their voice",
}

BASE_SYSTEM_PROMPT = (
    "You are a meticulous lorebook librarian for fiction writers. You read messy imported source "
    "material — character cards, world-info entries, chat logs, game state, and free-form notes — "
    "and distill only the real, stated facts into clean structured records. You never invent "
    "details and never summarize away specifics. You ALWAYS respond with ONLY a single JSON object "
    "inside a ```json fenced code block, with no prose, reasoning, or commentary before or after it."
)

SORTER_INSTRUCTION = (
    "The SOURCE below may contain unrelated material — game or system state, UI text, chat history, "
    "markdown formatting, settings, tags, or notes about other entities. Ignore all of it. Extract "
    "ONLY facts explicitly stated about the target, and place each fact under the field where it "
    "belongs. If a field is not addressed by the source, use an empty string. Do not invent, guess, "
    "or pad, and do not collapse everything into one field."
)

CATEGORY_DEFINITIONS = (
    "- characters: a person, being, creature, android, or any named individual\n"
    "- locations: a place, building, region, or setting\n"
    "- lore: a faction, organization, item, technology, concept, event, rule, or system\n"
    "- arcs: a storyline, plot thread, or narrative arc"
)

_RUBRIC_TYPES = ("character", "location", "lore", "arc")


def _field_lines(type_key: str) -> str:
    """Bulleted `field: meaning` lines for one type."""
    fields = TYPE_FIELDS.get(type_key, ["description"])
    return "\n".join(f"- {f}: {FIELD_DESCRIPTIONS.get(f, f)}" for f in fields)


def _rubric() -> str:
    """Compact per-type field rubric covering all four categories."""
    return "\n".join(f"   {t}: " + ", ".join(TYPE_FIELDS[t]) for t in _RUBRIC_TYPES)


def json_example(type_key: str, name: str = "Example Name") -> str:
    """A concrete ```json example object for one type, keys = name + the type's fields."""
    obj = {"name": name}
    for f in TYPE_FIELDS.get(type_key, ["description"]):
        obj[f] = f"<{f.replace('_', ' ')}>"
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def _book(book_title: str) -> str:
    return f' titled "{book_title}"' if book_title else ""


def build_extract_prompt(
    genre: str,
    book_title: str,
    name: str,
    content: str,
    type_key: str,
    entry_type_hint: str | None = None,
    existing_fields: dict | None = None,
) -> str:
    """User prompt to extract one entity's typed sub-fields for a KNOWN category."""
    hint = f"\nThe source labels this entry as: {entry_type_hint}." if entry_type_hint else ""
    existing = ""
    if existing_fields:
        existing = (
            "\n\nEXISTING RECORD — augment, don't fight. Keep what is already here and add detail "
            "from the source; do not contradict it unless the source clearly corrects it:\n"
            + json.dumps(existing_fields, ensure_ascii=False, indent=2)
        )
    return (
        f'Extract the details for the {type_key} named "{name}" in a {genre} book{_book(book_title)}.{hint}\n\n'
        f"{SORTER_INSTRUCTION}\n\n"
        f"Fill these fields (every value is a plain string):\n{_field_lines(type_key)}"
        f"{existing}\n\n"
        f"Respond with ONLY a JSON object of exactly this shape:\n{json_example(type_key, name)}\n\n"
        f"SOURCE:\n{(content or '')[:6000]}"
    )


def build_voice_prompt(genre: str, book_title: str, name: str, content: str, existing_voice: dict | None = None) -> str:
    """User prompt to extract/infer a character's dialogue VoiceProfile from the source."""
    field_lines = "\n".join(f"- {f}: {FIELD_DESCRIPTIONS.get(f, f)}" for f in VOICE_FIELDS)
    example = "```json\n{\n" + ",\n".join(f'  "{f}": "<{f.replace("_", " ")}>"' for f in VOICE_FIELDS) + "\n}\n```"
    existing = ""
    if existing_voice:
        existing = (
            "\n\nEXISTING VOICE — augment, don't fight. Keep what's here and refine it from the source:\n"
            + json.dumps(existing_voice, ensure_ascii=False, indent=2)
        )
    return (
        f'Capture the DIALOGUE VOICE of the character "{name}" in a {genre} book{_book(book_title)} — '
        f"how they actually speak. Base it on the SOURCE; you may make modest, consistent inferences "
        f"from their personality/background, but do not contradict stated facts.\n\n"
        f"{SORTER_INSTRUCTION}\n\n"
        f"Fill these fields (plain strings; put each example line on its own line):\n{field_lines}"
        f"{existing}\n\n"
        f"Respond with ONLY a JSON object of exactly this shape:\n{example}\n\n"
        f"SOURCE:\n{(content or '')[:6000]}"
    )


def build_classify_prompt(genre: str, book_title: str, name: str, content: str) -> str:
    """User prompt to classify ONE entry and extract its fields. Keeps an ENTRY NAME: anchor."""
    example = (
        "```json\n{\n"
        '  "category": "character",\n'
        '  "reasoning": "<one sentence: why this category>",\n'
        '  "fields": {\n    "role": "<...>",\n    "physical_description": "<...>"\n  }\n'
        "}\n```"
    )
    return (
        f"Sort ONE lore entry for a {genre} book{_book(book_title)} into a lorebook and extract its details.\n\n"
        f"ENTRY NAME: {name}\n"
        f"ENTRY CONTENT:\n{(content or '')[:6000]}\n\n"
        f"{SORTER_INSTRUCTION}\n\n"
        "1) Decide the single best category for this entry:\n"
        f"{CATEGORY_DEFINITIONS}\n"
        "2) Extract its details into that category's fields:\n"
        f"{_rubric()}\n\n"
        "Respond with ONLY a JSON object of this shape (category is one of "
        "character|location|lore|arc):\n"
        f"{example}"
    )


def build_map_prompt(genre: str, book_title: str, entries_json: str) -> str:
    """User prompt to batch-classify many entries at once (fallback for large imports)."""
    example = (
        "```json\n{\n"
        '  "characters": [{"name": "<name>", "reasoning": "<why>", "role": "<...>", "background": "<...>"}],\n'
        '  "locations": [],\n  "lore": [],\n  "arcs": []\n'
        "}\n```"
    )
    return (
        f"You are organizing imported worldbuilding notes into a story lorebook for a {genre} book"
        f"{_book(book_title)}. Below is a JSON list of entries, each with a name and content.\n\n"
        f"{SORTER_INSTRUCTION}\n\n"
        "Work through them ONE AT A TIME. For each entry, decide the single best category:\n"
        f"{CATEGORY_DEFINITIONS}\n"
        "Then pull the relevant details into that category's typed fields:\n"
        f"{_rubric()}\n\n"
        "Return a JSON object with keys characters, locations, lore, arcs (each a list of objects). "
        "Every object MUST include a 'name' and a short 'reasoning' field naming why it belongs in "
        "that category. Keep the substance from the content; do not invent entries.\n\n"
        f"Respond with ONLY a JSON object of this shape:\n{example}\n\n"
        "ENTRIES:\n" + entries_json
    )


def build_extract_from_text_prompt(genre: str, book_title: str, text: str) -> str:
    """User prompt to parse a free-text brainstorm note into canonical categories."""
    example = (
        "```json\n{\n"
        '  "characters": [{"name": "<name>", "reasoning": "<why>", "role": "<...>"}],\n'
        '  "locations": [],\n  "lore": [],\n  "arcs": []\n'
        "}\n```"
    )
    return (
        f"Extract structured lore from the brainstorming note below for a {genre} book{_book(book_title)}.\n\n"
        "Identify each distinct entity the note actually describes, then assign each to the single "
        "best category:\n"
        f"{CATEGORY_DEFINITIONS}\n"
        "Include these typed fields when the note implies them:\n"
        f"{_rubric()}\n\n"
        "Only include an entity if the note gives real information about it. Do not invent entities. "
        "Use empty strings for unknown fields.\n\n"
        f"Respond with ONLY a JSON object of this shape:\n{example}\n\n"
        "NOTE:\n" + text
    )
