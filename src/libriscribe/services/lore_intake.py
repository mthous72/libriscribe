"""Smart lore intake — one engine for parsing arbitrary input into a reviewable lore
proposal and merging it into a project's knowledge base (B12 + B13).

Two front doors share this engine:

- **Brainstorm "Apply to lore"** (chat.py) — free-text reply → `extract_from_text()`.
- **JSON import** (lorebook.py) — a foreign lore file (SillyTavern card, KoboldAI /
  SillyTavern World Info, or our own bundle) → `detect_and_adapt()` (+ optional LLM).

Both produce the same canonical *categories* shape::

    {"characters": [{"name": str, "fields": {<field>: <value>}}], "locations": [...],
     "lore": [...], "arcs": [...], "worldbuilding": {"fields": {...}}}

`build_proposal()` annotates each record with ``status`` ("new" | "update") by matching
its name against the KB (case-insensitive) and stringifies field values for editing in the
review UI. Nothing is written. `merge_apply()` then upserts confirmed records with **smart
merge**: it starts from the existing record, overlays only the non-empty fields provided,
and preserves everything not mentioned — it never wipes untouched data.
"""
from __future__ import annotations

import json
import re

from libriscribe.knowledge_base import Character, Location, LoreEntry, StoryArc, Worldbuilding

# ─── Canonical mappings ───────────────────────────────────────────────────────

# type -> (model class, KB attribute holding the name-keyed dict)
TYPE_MAP = {
    "character": (Character, "characters"),
    "location": (Location, "locations"),
    "lore": (LoreEntry, "lore_entries"),
    "arc": (StoryArc, "story_arcs"),
}
CATEGORY_TO_TYPE = {"characters": "character", "locations": "location", "lore": "lore", "arcs": "arc"}
ENTITY_CATEGORIES = ("characters", "locations", "lore", "arcs")

# The "interesting" fields the LLM is asked to populate per type (a subset of the model).
SMART_FIELDS = {
    "character": ["role", "physical_description", "personality_traits", "background", "motivations", "character_arc"],
    "location": ["description", "significance"],
    "lore": ["entry_type", "description", "significance"],
    "arc": ["arc_type", "description", "resolution_notes"],
}

# Accepted top-level keys per category in foreign/native JSON (case-insensitive).
CATEGORY_KEYS = {
    "characters": ["characters", "character", "cast", "people"],
    "locations": ["locations", "location", "places"],
    "lore": ["lore", "lore_entries", "loreentries", "entries", "worldinfo", "world_info"],
    "arcs": ["arcs", "story_arcs", "storyarcs", "arc", "plots"],
    "worldbuilding": ["worldbuilding", "world", "setting"],
}
FIELD_ALIASES = {
    "desc": "description",
    "summary": "description",
    "bio": "background",
    "personality": "personality_traits",
    "appearance": "physical_description",
    "type": "entry_type",
}


# ─── Small helpers ────────────────────────────────────────────────────────────

def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [p.strip() for p in re.split(r"[,;\n]", v) if p.strip()]
    return [str(v)]


def _to_display(v) -> str:
    """Render any field value as an editable string for the review UI."""
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def _pick(data: dict, keys: list[str]):
    low = {k.lower(): v for k, v in data.items()}
    for k in keys:
        if k in low:
            return low[k]
    return None


def _iter_entities(value):
    """Yield (name, obj) from a list of objects or a dict keyed by name."""
    if isinstance(value, list):
        for obj in value:
            if isinstance(obj, dict) and obj.get("name"):
                yield str(obj["name"]), obj
    elif isinstance(value, dict):
        for key, obj in value.items():
            if isinstance(obj, dict):
                yield str(obj.get("name") or key), obj


def _empty_cats() -> dict:
    return {"characters": [], "locations": [], "lore": [], "arcs": []}


def cats_count(cats: dict) -> int:
    n = sum(len(cats.get(c, []) or []) for c in ENTITY_CATEGORIES)
    if isinstance(cats.get("worldbuilding"), dict) and (cats["worldbuilding"].get("fields") or {}):
        n += 1
    return n


# ─── Foreign-format adapters (deterministic) ──────────────────────────────────

def _adapt_worldinfo_entries(entries) -> list[dict]:
    """SillyTavern / KoboldAI World Info entries -> lore records.

    Entries may be a dict keyed by uid or a list. Each entry typically has
    keys/key (triggers), keysecondary, comment (a label), and content (the text).
    """
    if isinstance(entries, dict):
        iterable = list(entries.values())
    elif isinstance(entries, list):
        iterable = entries
    else:
        return []

    items: list[dict] = []
    for i, e in enumerate(iterable):
        if not isinstance(e, dict):
            continue
        keys = _as_list(e.get("keys") or e.get("key"))
        sec = _as_list(e.get("keysecondary") or e.get("secondary_keys"))
        comment = str(e.get("comment") or e.get("name") or "").strip()
        content = str(e.get("content") or e.get("entry") or e.get("value") or "").strip()
        if not content and not keys:
            continue
        name = comment or (keys[0] if keys else f"Lore Entry {i + 1}")
        items.append({"name": name, "fields": {
            "entry_type": "world info",
            "description": content,
            "tags": keys + sec,
        }})
    return items


def _looks_like_worldinfo(entries) -> bool:
    items = entries.values() if isinstance(entries, dict) else entries if isinstance(entries, list) else []
    for e in items:
        if isinstance(e, dict) and ("content" in e or "key" in e or "keys" in e):
            return True
    return False


def _adapt_card(data: dict) -> dict:
    """SillyTavern / TavernAI character card (V1 flat or V2 nested) -> one character
    (+ any embedded character_book entries as lore)."""
    d = data.get("data") if isinstance(data.get("data"), dict) else data
    name = str(d.get("name") or data.get("name") or "Imported Character").strip()
    description = str(d.get("description") or "").strip()
    personality = str(d.get("personality") or "").strip()
    scenario = str(d.get("scenario") or "").strip()
    creator_notes = str(d.get("creator_notes") or "").strip()

    bg_parts = [description]
    if scenario:
        bg_parts.append(f"Scenario: {scenario}")
    if creator_notes:
        bg_parts.append(f"Notes: {creator_notes}")
    char = {"name": name, "fields": {
        "personality_traits": personality,
        "background": "\n\n".join(p for p in bg_parts if p),
    }}

    cats = _empty_cats()
    cats["characters"].append(char)
    book = d.get("character_book") or data.get("character_book")
    if isinstance(book, dict):
        cats["lore"].extend(_adapt_worldinfo_entries(book.get("entries")))
    return cats


def _adapt_native(data: dict) -> dict | None:
    """Our own bundle / a lenient {characters:[], locations:[], ...} shape."""
    cats = _empty_cats()
    found = False
    for cat in ENTITY_CATEGORIES:
        val = _pick(data, CATEGORY_KEYS[cat])
        if val is None:
            continue
        for nm, obj in _iter_entities(val):
            found = True
            cats[cat].append({"name": nm, "fields": {k: v for k, v in obj.items() if k != "name"}})
    wb = _pick(data, CATEGORY_KEYS["worldbuilding"])
    if isinstance(wb, dict):
        cats["worldbuilding"] = {"fields": dict(wb)}
        found = True
    return cats if found else None


def detect_and_adapt(data) -> tuple[dict, str] | None:
    """Map a recognized JSON shape into canonical categories. Returns (cats, label) or
    None if the shape is unrecognized (caller may then fall back to the LLM)."""
    # A bare list — of cards, WI entries, or native entity objects.
    if isinstance(data, list):
        if any(isinstance(e, dict) and ("content" in e or "keys" in e or "key" in e) for e in data):
            cats = _empty_cats()
            cats["lore"] = _adapt_worldinfo_entries(data)
            return cats, "World Info entries"
        cats = _empty_cats()
        for obj in data:
            if isinstance(obj, dict) and obj.get("name"):
                cats["lore"].append({"name": str(obj["name"]), "fields": {k: v for k, v in obj.items() if k != "name"}})
        return (cats, "entity list") if cats_count(cats) else None

    if not isinstance(data, dict):
        return None

    spec = str(data.get("spec", "")).lower()
    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    if spec.startswith("chara_card") or "first_mes" in data or "first_mes" in nested or "mes_example" in data:
        return _adapt_card(data), "SillyTavern character card"

    if _looks_like_worldinfo(data.get("entries")):
        cats = _empty_cats()
        cats["lore"] = _adapt_worldinfo_entries(data["entries"])
        return cats, "World Info / lorebook"

    native = _adapt_native(data)
    if native is not None:
        return native, "lore JSON"
    return None


# ─── LLM mapping (fallback / hybrid enrichment) ───────────────────────────────

def _normalize_cats(data) -> dict:
    """Coerce arbitrary LLM/JSON output into canonical {name, fields} categories."""
    out = _empty_cats()
    if not isinstance(data, dict):
        return out
    for cat in ENTITY_CATEGORIES:
        val = _pick(data, CATEGORY_KEYS[cat])
        if val is None:
            continue
        for nm, obj in _iter_entities(val):
            fields = {k: v for k, v in obj.items() if k != "name"} if isinstance(obj, dict) else {}
            out[cat].append({"name": nm, "fields": fields})
    wb = _pick(data, CATEGORY_KEYS["worldbuilding"])
    if isinstance(wb, dict):
        out["worldbuilding"] = {"fields": wb}
    return out


def llm_map(client, genre: str, data) -> dict:
    """Use the LLM to map arbitrary/foreign JSON into canonical categories."""
    if client is None:
        return _empty_cats()
    raw = json.dumps(data, default=str)[:12000]
    prompt = (
        f"Convert the JSON below (a lore/character file for a {genre} book, possibly from "
        "another tool like SillyTavern or KoboldAI) into a JSON object with keys: "
        "characters, locations, lore, arcs (each a list of objects with a 'name' plus "
        "relevant fields), and worldbuilding (an object). Classify each entry into the most "
        "fitting category (a person -> characters, a place -> locations, a faction/item/"
        "concept/event -> lore). Keep field names simple: name, role, physical_description, "
        "personality_traits, background, motivations, description, significance, entry_type, "
        "arc_type. Return ONLY the JSON.\n\n" + raw
    )
    try:
        result = client.generate_content_with_json_repair(prompt, max_tokens=4000, temperature=0.2)
        return _normalize_cats(json.loads(result))
    except Exception:
        return _empty_cats()


def extract_from_text(client, genre: str, text: str) -> dict:
    """Parse a free-text brainstorm note into canonical categories (B12)."""
    if client is None:
        return _empty_cats()
    prompt = (
        f"Extract structured lore from the brainstorming note below for a {genre} book.\n\n"
        "Produce a JSON object with keys characters, locations, lore, arcs — each a LIST of "
        "objects. Every object MUST have a 'name'. Include only these fields, and only when "
        "the note actually implies them:\n"
        "- character: role, physical_description, personality_traits, background, motivations, character_arc\n"
        "- location: description, significance\n"
        "- lore: entry_type, description, significance\n"
        "- arc: arc_type, description, resolution_notes\n\n"
        "Split distinct people, places, factions/items/concepts, and plotlines into separate "
        "objects. Only include an entity if the note gives real information about it. Use "
        "empty strings for unknown fields. Return ONLY the JSON.\n\nNOTE:\n" + text
    )
    try:
        raw = client.generate_content_with_json_repair(prompt, max_tokens=2500, temperature=0.3)
        return _normalize_cats(json.loads(raw))
    except Exception:
        return _empty_cats()


# ─── Proposal (annotate, no write) ────────────────────────────────────────────

def _clean_fields(model_cls, fields: dict) -> dict:
    out: dict[str, str] = {}
    for k, v in (fields or {}).items():
        key = FIELD_ALIASES.get(k, k)
        if key == "name" or key not in model_cls.model_fields:
            continue
        s = _to_display(v)
        if s.strip():
            out[key] = s
    return out


def build_proposal(kb, cats: dict) -> dict:
    """Annotate canonical categories with new/update status against the KB. No writes."""
    proposal: dict = {c: [] for c in ENTITY_CATEGORIES}
    for cat in ENTITY_CATEGORIES:
        model_cls, attr = TYPE_MAP[CATEGORY_TO_TYPE[cat]]
        store = getattr(kb, attr, {}) or {}
        lowmap = {k.lower(): k for k in store}
        for rec in cats.get(cat, []) or []:
            name = str(rec.get("name", "")).strip()
            if not name:
                continue
            fields = _clean_fields(model_cls, rec.get("fields", {}))
            matched = lowmap.get(name.lower())
            proposal[cat].append({
                "name": matched or name,
                "status": "update" if matched else "new",
                "fields": fields,
            })
    wb = cats.get("worldbuilding")
    if isinstance(wb, dict):
        wb_fields = _clean_fields(Worldbuilding, wb.get("fields", wb))
        if wb_fields:
            proposal["worldbuilding"] = {
                "status": "update" if kb.worldbuilding else "new",
                "fields": wb_fields,
            }
    return proposal


# ─── Merge apply (smart upsert) ───────────────────────────────────────────────

def _coerce_value(model_cls, field: str, value):
    ann = str(model_cls.model_fields[field].annotation).lower()
    if "list" in ann:
        if isinstance(value, list):
            items = [x for x in value if str(x).strip()]
        elif isinstance(value, str):
            items = [p.strip() for p in re.split(r"[,;\n]", value) if p.strip()]
        elif value in (None, ""):
            items = []
        else:
            items = [value]
        if "int" in ann:
            nums = []
            for x in items:
                s = str(x).strip()
                if s.lstrip("-").isdigit():
                    nums.append(int(s))
            return nums
        return [str(x) for x in items]
    if "dict" in ann:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip().startswith("{"):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return {}
    if "int" in ann:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
        return None
    # string field
    return _to_display(value)


def _safe_construct(model_cls, data: dict):
    """Build a model, progressively dropping any field that fails validation."""
    fields = {k: v for k, v in data.items() if k in model_cls.model_fields}
    try:
        return model_cls(**fields)
    except Exception:
        pass
    name = fields.get("name")
    base = {"name": name} if name is not None else {}
    for k, v in fields.items():
        if k == "name":
            continue
        try:
            model_cls(**{**base, k: v})
            base[k] = v
        except Exception:
            continue
    try:
        return model_cls(**base)
    except Exception:
        return None


def _upsert(store: dict, name: str, model_cls, fields: dict) -> bool:
    existing, key = store.get(name), name
    if existing is None:
        for k, v in store.items():
            if k.lower() == name.lower():
                existing, key = v, k
                break
    base = existing.model_dump() if existing is not None else {}
    for fk, fv in (fields or {}).items():
        f = FIELD_ALIASES.get(fk, fk)
        if f == "name" or f not in model_cls.model_fields:
            continue
        cv = _coerce_value(model_cls, f, fv)
        if cv in (None, "", [], {}):
            continue  # never overwrite with empty — preserve existing
        base[f] = cv
    base["name"] = key
    entity = _safe_construct(model_cls, base)
    if entity is None:
        if existing is not None:
            return False  # leave the existing record untouched
        entity = _safe_construct(model_cls, {"name": key})
        if entity is None:
            return False
    store[key] = entity
    return True


def _merge_worldbuilding(kb, fields: dict) -> bool:
    if not isinstance(fields, dict):
        return False
    current = kb.worldbuilding.model_dump() if kb.worldbuilding else {}
    changed = False
    for k, v in fields.items():
        key = FIELD_ALIASES.get(k, k)
        if key not in Worldbuilding.model_fields:
            continue
        s = _to_display(v)
        if s.strip():
            current[key] = s
            changed = True
    if not changed:
        return False
    built = _safe_construct(Worldbuilding, current)
    if built is None:
        return False
    kb.worldbuilding = built
    kb.worldbuilding_needed = True
    return True


def merge_apply(kb, records: dict) -> dict:
    """Upsert confirmed records into the KB with smart merge. Returns per-category counts."""
    summary = {"characters": 0, "locations": 0, "lore": 0, "arcs": 0, "worldbuilding": 0}
    for cat in ENTITY_CATEGORIES:
        model_cls, attr = TYPE_MAP[CATEGORY_TO_TYPE[cat]]
        store = getattr(kb, attr)
        for rec in records.get(cat, []) or []:
            name = str(rec.get("name", "")).strip()
            if not name:
                continue
            if _upsert(store, name, model_cls, rec.get("fields", {})):
                summary[cat] += 1
    wb = records.get("worldbuilding")
    if isinstance(wb, dict):
        if _merge_worldbuilding(kb, wb.get("fields", wb)):
            summary["worldbuilding"] = 1
    return summary
