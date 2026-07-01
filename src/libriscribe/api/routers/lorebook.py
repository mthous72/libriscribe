"""Lorebook CRUD endpoints - characters, locations, lore, arcs, worldbuilding, xref, search, scenes."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from libriscribe.api.schemas.lorebook import (
    AnalyzeRequest,
    CharacterRequest,
    CharacterStateResponse,
    ContinuityNoteResponse,
    EditSuggestionRequest,
    LocationRequest,
    LoreEntryRequest,
    LoreSuggestionResponse,
    NarrativeThreadRequest,
    NarrativeThreadResponse,
    StoryArcRequest,
    WorldbuildingRequest,
    SceneRequest,
    SearchRequest,
)
from libriscribe.knowledge_base import (
    Character,
    Location,
    LoreEntry,
    NarrativeThread,
    StoryArc,
    VoiceProfile,
    ArcMilestone,
    Worldbuilding,
    Scene,
)
from libriscribe.services.project_service import load_kb, save_kb, get_projects_dir

router = APIRouter(prefix="/api/projects", tags=["lorebook"])


# ─── Characters ───────────────────────────────────────────────────

@router.get("/{name}/characters")
def list_characters(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(kb.characters.values())


@router.get("/{name}/characters/{char_name}")
def get_character(name: str, char_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    char = kb.get_character(char_name)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


def _build_character_from_request(req: CharacterRequest) -> Character:
    data = req.model_dump()
    vp_data = data.pop("voice_profile", None)
    char = Character(**data)
    if vp_data:
        char.voice_profile = VoiceProfile(**vp_data)
    return char


@router.post("/{name}/characters")
def create_character(name: str, req: CharacterRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    char = _build_character_from_request(req)
    kb.add_character(char)
    save_kb(name, kb)
    return char


@router.put("/{name}/characters/{char_name}")
def update_character(name: str, char_name: str, req: CharacterRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    # Remove old key if name changed
    if char_name in kb.characters and req.name != char_name:
        del kb.characters[char_name]
    char = _build_character_from_request(req)
    kb.add_character(char)
    save_kb(name, kb)
    return char


@router.delete("/{name}/characters/{char_name}", status_code=204)
def delete_character(name: str, char_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if char_name not in kb.characters:
        raise HTTPException(status_code=404, detail="Character not found")
    del kb.characters[char_name]
    save_kb(name, kb)


# ─── Locations ────────────────────────────────────────────────────

@router.get("/{name}/locations")
def list_locations(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(kb.locations.values())


@router.get("/{name}/locations/{loc_name}")
def get_location(name: str, loc_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    loc = kb.get_location(loc_name)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.post("/{name}/locations")
def create_location(name: str, req: LocationRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    loc = Location(**req.model_dump())
    kb.add_location(loc)
    save_kb(name, kb)
    return loc


@router.put("/{name}/locations/{loc_name}")
def update_location(name: str, loc_name: str, req: LocationRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if loc_name in kb.locations and req.name != loc_name:
        del kb.locations[loc_name]
    loc = Location(**req.model_dump())
    kb.add_location(loc)
    save_kb(name, kb)
    return loc


@router.delete("/{name}/locations/{loc_name}", status_code=204)
def delete_location(name: str, loc_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if loc_name not in kb.locations:
        raise HTTPException(status_code=404, detail="Location not found")
    del kb.locations[loc_name]
    save_kb(name, kb)


# ─── Lore Entries ─────────────────────────────────────────────────

@router.get("/{name}/lore")
def list_lore(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(kb.lore_entries.values())


@router.get("/{name}/lore/{entry_name}")
def get_lore_entry(name: str, entry_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    entry = kb.get_lore_entry(entry_name)
    if not entry:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    return entry


@router.post("/{name}/lore")
def create_lore_entry(name: str, req: LoreEntryRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    entry = LoreEntry(**req.model_dump())
    kb.add_lore_entry(entry)
    save_kb(name, kb)
    return entry


@router.put("/{name}/lore/{entry_name}")
def update_lore_entry(name: str, entry_name: str, req: LoreEntryRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if entry_name in kb.lore_entries and req.name != entry_name:
        del kb.lore_entries[entry_name]
    entry = LoreEntry(**req.model_dump())
    kb.add_lore_entry(entry)
    save_kb(name, kb)
    return entry


@router.delete("/{name}/lore/{entry_name}", status_code=204)
def delete_lore_entry(name: str, entry_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if entry_name not in kb.lore_entries:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    del kb.lore_entries[entry_name]
    save_kb(name, kb)


# ─── Story Arcs ──────────────────────────────────────────────────

@router.get("/{name}/arcs")
def list_arcs(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(kb.story_arcs.values())


@router.get("/{name}/arcs/{arc_name}")
def get_arc(name: str, arc_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    arc = kb.get_story_arc(arc_name)
    if not arc:
        raise HTTPException(status_code=404, detail="Story arc not found")
    return arc


def _build_arc_from_request(req: StoryArcRequest) -> StoryArc:
    data = req.model_dump()
    milestones_data = data.pop("milestones", [])
    arc = StoryArc(**data)
    arc.milestones = [ArcMilestone(**m) for m in milestones_data]
    return arc


@router.post("/{name}/arcs")
def create_arc(name: str, req: StoryArcRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    arc = _build_arc_from_request(req)
    kb.add_story_arc(arc)
    save_kb(name, kb)
    return arc


@router.put("/{name}/arcs/{arc_name}")
def update_arc(name: str, arc_name: str, req: StoryArcRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if arc_name in kb.story_arcs and req.name != arc_name:
        del kb.story_arcs[arc_name]
    arc = _build_arc_from_request(req)
    kb.add_story_arc(arc)
    save_kb(name, kb)
    return arc


@router.delete("/{name}/arcs/{arc_name}", status_code=204)
def delete_arc(name: str, arc_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if arc_name not in kb.story_arcs:
        raise HTTPException(status_code=404, detail="Story arc not found")
    del kb.story_arcs[arc_name]
    save_kb(name, kb)


# ─── Worldbuilding ────────────────────────────────────────────────

@router.get("/{name}/worldbuilding")
def get_worldbuilding(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if not kb.worldbuilding:
        return {}
    return kb.worldbuilding.model_dump()


@router.put("/{name}/worldbuilding")
def update_worldbuilding(name: str, req: WorldbuildingRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if not kb.worldbuilding:
        kb.worldbuilding = Worldbuilding()
        kb.worldbuilding_needed = True
    for field, value in req.model_dump(exclude_unset=True).items():
        if hasattr(kb.worldbuilding, field):
            setattr(kb.worldbuilding, field, value)
    save_kb(name, kb)
    return kb.worldbuilding.model_dump()


# ─── Cross-References ─────────────────────────────────────────────

@router.get("/{name}/xref")
def list_xref(name: str):
    """Returns all cross-reference entries from the retrieval index."""
    project_dir = get_projects_dir() / name
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from libriscribe.retrieval.search_service import SearchServiceImpl
        from libriscribe.retrieval.models import RetrievalConfig
        config = kb.retrieval if kb.retrieval and kb.retrieval.enabled else RetrievalConfig(enabled=True)
        svc = SearchServiceImpl(project_dir, config)
        entries = svc.index_manager.xref_index.get_all_entries()
        return [e.model_dump() for e in entries]
    except Exception:
        return []


@router.get("/{name}/xref/{entity_name}")
def get_xref(name: str, entity_name: str):
    project_dir = get_projects_dir() / name
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from libriscribe.retrieval.search_service import SearchServiceImpl
        from libriscribe.retrieval.models import RetrievalConfig
        config = kb.retrieval if kb.retrieval and kb.retrieval.enabled else RetrievalConfig(enabled=True)
        svc = SearchServiceImpl(project_dir, config)
        entry = svc.index_manager.xref_index.lookup(entity_name)
        if not entry:
            raise HTTPException(status_code=404, detail="Entity not found in cross-reference index")
        return entry.model_dump()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Cross-reference index not available")


# ─── Search ───────────────────────────────────────────────────────

@router.post("/{name}/search")
def search_project(name: str, req: SearchRequest):
    project_dir = get_projects_dir() / name
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        from libriscribe.retrieval.search_service import SearchServiceImpl
        from libriscribe.retrieval.models import RetrievalConfig
        config = kb.retrieval if kb.retrieval and kb.retrieval.enabled else RetrievalConfig(enabled=True, mode="keyword")
        svc = SearchServiceImpl(project_dir, config)
        results = svc.search(
            req.query,
            mode="keyword",
            top_k=req.top_k,
            filters=req.filters if req.filters else None,
        )
        return [r.model_dump() for r in results]
    except Exception:
        return []


# ─── Lore import (JSON) ───────────────────────────────────────────

class LoreImportRequest(BaseModel):
    data: dict | list
    smart: bool = False


# Accepted top-level keys per category (case-insensitive).
_CATEGORY_KEYS = {
    "characters": ["characters", "character", "cast"],
    "locations": ["locations", "location", "places"],
    "lore": ["lore", "lore_entries", "loreentries", "entries"],
    "arcs": ["arcs", "story_arcs", "storyarcs", "arc"],
    "worldbuilding": ["worldbuilding", "world", "setting"],
}
_FIELD_ALIASES = {"desc": "description", "summary": "description"}


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


def _coerce(obj: dict, model_cls, name: str):
    fields = {}
    for k, v in obj.items():
        key = _FIELD_ALIASES.get(k, k)
        if key != "name" and key in model_cls.model_fields:
            fields[key] = v
    try:
        return model_cls(name=name, **fields)
    except Exception:
        try:
            return model_cls(name=name)
        except Exception:
            return None


def _smart_normalize(kb, data) -> dict:
    """Use the project's LLM to map arbitrary JSON into our lore categories."""
    from libriscribe.utils.llm_client import LLMClient

    raw = json.dumps(data)[:12000]
    prompt = (
        "Convert the JSON below into a JSON object with keys: characters, locations, "
        "lore, arcs (each a list of objects that include a 'name' plus relevant fields), "
        "and worldbuilding (an object). Keep field names simple (name, description, role, "
        "background, significance, entry_type, arc_type). Return ONLY the JSON.\n\n" + raw
    )
    try:
        client = LLMClient(kb.llm_provider)
        if kb.model:
            client.set_model(kb.model)
        result = client.generate_content_with_json_repair(prompt, max_tokens=4000, temperature=0.2)
        parsed = json.loads(result)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@router.post("/{name}/lore/import")
def import_lore(name: str, body: LoreImportRequest):
    """Import lore from JSON, parsing it into characters / locations / lore / arcs /
    worldbuilding. Lenient about shape; `smart` uses the LLM to map non-standard JSON."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    data = body.data
    if body.smart or not isinstance(data, dict):
        normalized = _smart_normalize(kb, data)
        if normalized:
            data = normalized
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object with lore categories (characters, locations, lore, arcs, worldbuilding).")

    summary = {"characters": 0, "locations": 0, "lore": 0, "arcs": 0, "worldbuilding": 0}

    for nm, obj in _iter_entities(_pick(data, _CATEGORY_KEYS["characters"]) or []):
        e = _coerce(obj, Character, nm)
        if e:
            kb.characters[nm] = e
            summary["characters"] += 1
    for nm, obj in _iter_entities(_pick(data, _CATEGORY_KEYS["locations"]) or []):
        e = _coerce(obj, Location, nm)
        if e:
            kb.locations[nm] = e
            summary["locations"] += 1
    for nm, obj in _iter_entities(_pick(data, _CATEGORY_KEYS["lore"]) or []):
        e = _coerce(obj, LoreEntry, nm)
        if e:
            kb.lore_entries[nm] = e
            summary["lore"] += 1
    for nm, obj in _iter_entities(_pick(data, _CATEGORY_KEYS["arcs"]) or []):
        e = _coerce(obj, StoryArc, nm)
        if e:
            kb.story_arcs[nm] = e
            summary["arcs"] += 1

    wb = _pick(data, _CATEGORY_KEYS["worldbuilding"])
    if isinstance(wb, dict):
        allowed = {k: v for k, v in wb.items() if k in Worldbuilding.model_fields}
        try:
            kb.worldbuilding = Worldbuilding(**allowed)
            kb.worldbuilding_needed = True
            summary["worldbuilding"] = 1
        except Exception:
            pass

    if sum(summary.values()) == 0:
        raise HTTPException(
            status_code=400,
            detail="No recognizable lore found. Expected categories: characters, locations, lore, arcs, worldbuilding. Try the AI-map option for non-standard JSON.",
        )

    save_kb(name, kb)
    return summary


# ─── Smart lore intake: parse → review → merge (B12 + B13) ────────

class LoreParseRequest(BaseModel):
    data: dict | list
    smart: bool = False


class ProposalApplyRequest(BaseModel):
    records: dict


def _maybe_client(kb):
    """Best-effort LLM client for the project; None if it can't be built."""
    from libriscribe.utils.llm_client import LLMClient
    try:
        client = LLMClient(kb.llm_provider)
        if kb.model:
            client.set_model(kb.model)
        return client
    except Exception:
        return None


@router.post("/{name}/lore/parse")
def parse_lore(name: str, body: LoreParseRequest):
    """Parse a (possibly foreign) lore JSON file into a reviewable proposal — no writes.

    Recognized shapes (SillyTavern character cards, KoboldAI / SillyTavern World Info, our
    own bundle) are adapted deterministically. `smart` adds an LLM pass to re-classify and
    enrich them; unrecognized shapes fall back to pure-LLM mapping automatically."""
    from libriscribe.services import lore_intake

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    detected = lore_intake.detect_and_adapt(body.data)
    cats = detected[0] if detected else lore_intake._empty_cats()
    fmt = detected[1] if detected else "unrecognized"
    used_llm = False

    # Hybrid: enrich recognized formats when asked; always LLM-map unrecognized shapes.
    if body.smart or detected is None:
        source = body.data if detected is None else {**cats}
        llm_cats = lore_intake.llm_map(_maybe_client(kb), kb.genre, source)
        if lore_intake.cats_count(llm_cats) > 0:
            cats = llm_cats
            used_llm = True
            fmt = f"{fmt} + AI" if detected else "AI-mapped"

    if lore_intake.cats_count(cats) == 0:
        raise HTTPException(
            status_code=422,
            detail="No recognizable lore found. Supported: our bundle, SillyTavern cards, "
                   "KoboldAI / SillyTavern World Info. Enable AI-map for other formats.",
        )

    return {"proposal": lore_intake.build_proposal(kb, cats), "format": fmt, "used_llm": used_llm}


@router.post("/{name}/lore/apply-parsed")
def apply_parsed(name: str, body: ProposalApplyRequest):
    """Merge confirmed proposal records into the KB (smart merge — preserves untouched
    fields). Shared by brainstorm Smart Apply and JSON import review."""
    from libriscribe.services import lore_intake

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    summary = lore_intake.merge_apply(kb, body.records or {})
    if sum(summary.values()) == 0:
        raise HTTPException(status_code=400, detail="Nothing was applied.")
    save_kb(name, kb)
    return summary


# ─── Outline ──────────────────────────────────────────────────────

@router.get("/{name}/outline")
def get_outline(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapters_data = []
    for ch_num in sorted(kb.chapters.keys()):
        ch = kb.chapters[ch_num]
        chapters_data.append({
            "chapter_number": ch.chapter_number,
            "title": ch.title,
            "summary": ch.summary,
            "scene_count": len(ch.scenes),
        })
    return {
        "outline_markdown": kb.outline,
        "chapters": chapters_data,
    }


@router.put("/{name}/outline")
def update_outline(name: str, body: dict):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if "outline_markdown" in body:
        kb.outline = body["outline_markdown"]
    save_kb(name, kb)
    return {"outline_markdown": kb.outline}


# ─── Scenes ──────────────────────────────────────────────────────

@router.get("/{name}/scenes/{chapter_num}")
def list_scenes(name: str, chapter_num: int):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = kb.get_chapter(chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return [s.model_dump() for s in chapter.scenes]


@router.put("/{name}/scenes/{chapter_num}/{scene_num}")
def update_scene(name: str, chapter_num: int, scene_num: int, req: SceneRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = kb.get_chapter(chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    for i, scene in enumerate(chapter.scenes):
        if scene.scene_number == scene_num:
            chapter.scenes[i] = Scene(**req.model_dump())
            save_kb(name, kb)
            return chapter.scenes[i].model_dump()

    raise HTTPException(status_code=404, detail="Scene not found")


@router.post("/{name}/scenes/{chapter_num}")
def create_scene(name: str, chapter_num: int, req: SceneRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = kb.get_chapter(chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    scene = Scene(**req.model_dump())
    chapter.scenes.append(scene)
    chapter.scenes.sort(key=lambda s: s.scene_number)
    save_kb(name, kb)
    return scene.model_dump()


@router.delete("/{name}/scenes/{chapter_num}/{scene_num}", status_code=204)
def delete_scene(name: str, chapter_num: int, scene_num: int):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    chapter = kb.get_chapter(chapter_num)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    chapter.scenes = [s for s in chapter.scenes if s.scene_number != scene_num]
    # Re-number
    for i, scene in enumerate(chapter.scenes):
        scene.scene_number = i + 1
    save_kb(name, kb)


# ─── Lore Sync / Analysis ──────────────────────────────────
def _get_lore_sync(name: str):
    """Helper to instantiate LoreSyncService for a project."""
    from libriscribe.services.lore_sync import LoreSyncService
    from libriscribe.utils.llm_client import LLMClient
    from libriscribe.settings import Settings

    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")

    settings = Settings()
    project_dir = get_projects_dir() / name
    llm_client = LLMClient(kb.llm_provider)
    if kb.model:
        llm_client.set_model(kb.model)

    return LoreSyncService(llm_client, kb, project_dir), kb


def _parse_chapter_range(body: AnalyzeRequest | None) -> tuple[int, int] | None:
    if body and body.chapter_start is not None and body.chapter_end is not None:
        return (body.chapter_start, body.chapter_end)
    return None


@router.post("/{name}/analyze/character/{char_name}")
def analyze_character(name: str, char_name: str, body: AnalyzeRequest | None = None):
    """Triggers AI analysis of a character across chapters. Returns suggestions."""
    svc, kb = _get_lore_sync(name)
    ch_range = _parse_chapter_range(body)
    suggestions = svc.analyze_character(char_name, ch_range)
    # Store suggestions in KB
    kb.lore_suggestions.extend(suggestions)
    save_kb(name, kb)
    start_idx = len(kb.lore_suggestions) - len(suggestions)
    return [
        LoreSuggestionResponse(index=start_idx + i, **s.model_dump())
        for i, s in enumerate(suggestions)
    ]


@router.post("/{name}/analyze/location/{loc_name}")
def analyze_location(name: str, loc_name: str, body: AnalyzeRequest | None = None):
    """Triggers AI analysis of a location across chapters."""
    svc, kb = _get_lore_sync(name)
    ch_range = _parse_chapter_range(body)
    suggestions = svc.analyze_location(loc_name, ch_range)
    kb.lore_suggestions.extend(suggestions)
    save_kb(name, kb)
    start_idx = len(kb.lore_suggestions) - len(suggestions)
    return [
        LoreSuggestionResponse(index=start_idx + i, **s.model_dump())
        for i, s in enumerate(suggestions)
    ]


@router.post("/{name}/analyze/lore/{entry_name}")
def analyze_lore_entry_sync(name: str, entry_name: str, body: AnalyzeRequest | None = None):
    """Triggers AI analysis of a lore entry across chapters."""
    svc, kb = _get_lore_sync(name)
    ch_range = _parse_chapter_range(body)
    suggestions = svc.analyze_lore_entry(entry_name, ch_range)
    kb.lore_suggestions.extend(suggestions)
    save_kb(name, kb)
    start_idx = len(kb.lore_suggestions) - len(suggestions)
    return [
        LoreSuggestionResponse(index=start_idx + i, **s.model_dump())
        for i, s in enumerate(suggestions)
    ]


@router.post("/{name}/analyze/continuity")
def check_continuity(name: str, body: AnalyzeRequest | None = None):
    """Runs continuity check across all entities."""
    svc, kb = _get_lore_sync(name)
    ch_range = _parse_chapter_range(body)
    notes = svc.detect_continuity_issues(ch_range)
    kb.continuity_notes.extend(notes)
    save_kb(name, kb)
    return [ContinuityNoteResponse(**n.model_dump()) for n in notes]


@router.get("/{name}/suggestions")
def list_suggestions(name: str, status: str = "pending"):
    """Returns all lore suggestions, filtered by status."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return [
        LoreSuggestionResponse(index=i, **s.model_dump())
        for i, s in enumerate(kb.lore_suggestions)
        if status == "all" or s.status == status
    ]


@router.put("/{name}/suggestions/{idx}/accept")
def accept_suggestion(name: str, idx: int):
    """Accepts a suggestion -- applies the change to the entity."""
    svc, kb = _get_lore_sync(name)
    if idx < 0 or idx >= len(kb.lore_suggestions):
        raise HTTPException(status_code=404, detail="Suggestion not found")
    svc.apply_suggestion(idx)
    save_kb(name, kb)
    return LoreSuggestionResponse(index=idx, **kb.lore_suggestions[idx].model_dump())


@router.put("/{name}/suggestions/{idx}/reject")
def reject_suggestion(name: str, idx: int):
    """Rejects a suggestion -- marks it rejected, no change applied."""
    svc, kb = _get_lore_sync(name)
    if idx < 0 or idx >= len(kb.lore_suggestions):
        raise HTTPException(status_code=404, detail="Suggestion not found")
    svc.reject_suggestion(idx)
    save_kb(name, kb)
    return LoreSuggestionResponse(index=idx, **kb.lore_suggestions[idx].model_dump())


@router.put("/{name}/suggestions/{idx}/edit")
def edit_suggestion(name: str, idx: int, body: EditSuggestionRequest):
    """User edits the proposed value before accepting."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if idx < 0 or idx >= len(kb.lore_suggestions):
        raise HTTPException(status_code=404, detail="Suggestion not found")
    kb.lore_suggestions[idx].proposed_value = body.proposed_value
    save_kb(name, kb)
    return LoreSuggestionResponse(index=idx, **kb.lore_suggestions[idx].model_dump())


# ─── Character States ──────────────────────────────────────
@router.get("/{name}/character-states")
def list_character_states(name: str):
    """Returns all character state snapshots."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    result = []
    for char_name, states in kb.character_states.items():
        for s in states:
            result.append(CharacterStateResponse(**s.model_dump()))
    return result


@router.get("/{name}/character-states/{char_name}")
def get_character_states(name: str, char_name: str):
    """Returns state history for a specific character."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    states = kb.character_states.get(char_name, [])
    return [CharacterStateResponse(**s.model_dump()) for s in states]


# ─── Continuity Notes ──────────────────────────────────────
@router.get("/{name}/continuity-notes")
def list_continuity_notes(name: str):
    """Returns all continuity notes."""
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return [ContinuityNoteResponse(**n.model_dump()) for n in kb.continuity_notes]


# ─── Narrative Threads ──────────────────────────────────────

@router.get("/{name}/threads")
def list_threads(name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    return [NarrativeThreadResponse(**t.model_dump()) for t in kb.narrative_threads.values()]


@router.get("/{name}/threads/{thread_name}")
def get_thread(name: str, thread_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    thread = kb.get_narrative_thread(thread_name)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return NarrativeThreadResponse(**thread.model_dump())


@router.post("/{name}/threads")
def create_thread(name: str, req: NarrativeThreadRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    thread = NarrativeThread(**req.model_dump())
    kb.add_narrative_thread(thread)
    save_kb(name, kb)
    return NarrativeThreadResponse(**thread.model_dump())


@router.put("/{name}/threads/{thread_name}")
def update_thread(name: str, thread_name: str, req: NarrativeThreadRequest):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if thread_name in kb.narrative_threads and req.name != thread_name:
        del kb.narrative_threads[thread_name]
    thread = NarrativeThread(**req.model_dump())
    kb.add_narrative_thread(thread)
    save_kb(name, kb)
    return NarrativeThreadResponse(**thread.model_dump())


@router.delete("/{name}/threads/{thread_name}", status_code=204)
def delete_thread(name: str, thread_name: str):
    kb = load_kb(name)
    if not kb:
        raise HTTPException(status_code=404, detail="Project not found")
    if thread_name not in kb.narrative_threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    del kb.narrative_threads[thread_name]
    save_kb(name, kb)
