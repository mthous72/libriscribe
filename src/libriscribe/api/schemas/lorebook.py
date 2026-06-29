from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceProfileRequest(BaseModel):
    speech_patterns: str = ""
    vocabulary_level: str = ""
    verbal_tics: str = ""
    avoids: str = ""
    example_dialogue: list[str] = Field(default_factory=list)


class CharacterRequest(BaseModel):
    name: str
    age: str = ""
    physical_description: str = ""
    personality_traits: str = ""
    background: str = ""
    motivations: str = ""
    relationships: dict[str, str] = Field(default_factory=dict)
    role: str = ""
    internal_conflicts: str = ""
    external_conflicts: str = ""
    character_arc: str = ""
    voice_profile: VoiceProfileRequest | None = None


class LocationRequest(BaseModel):
    name: str
    description: str = ""
    significance: str = ""
    associated_characters: list[str] = Field(default_factory=list)
    first_appearance: int | None = None
    tags: list[str] = Field(default_factory=list)


class LoreEntryRequest(BaseModel):
    name: str
    entry_type: str = ""
    description: str = ""
    significance: str = ""
    related_entities: list[str] = Field(default_factory=list)
    first_appearance: int | None = None
    tags: list[str] = Field(default_factory=list)


class ArcMilestoneRequest(BaseModel):
    name: str
    milestone_type: str = "rising_action"
    target_chapter: int | None = None
    actual_chapter: int | None = None
    description: str = ""
    status: str = "pending"


class StoryArcRequest(BaseModel):
    name: str
    description: str = ""
    arc_type: str = "main"
    chapters_involved: list[int] = Field(default_factory=list)
    characters_involved: list[str] = Field(default_factory=list)
    status: str = "active"
    resolution_notes: str = ""
    milestones: list[ArcMilestoneRequest] = Field(default_factory=list)


class WorldbuildingRequest(BaseModel):
    geography: str = ""
    culture_and_society: str = ""
    history: str = ""
    rules_and_laws: str = ""
    technology_level: str = ""
    magic_system: str = ""
    key_locations: str = ""
    important_organizations: str = ""
    flora_and_fauna: str = ""
    languages: str = ""
    religions_and_beliefs: str = ""
    economy: str = ""
    conflicts: str = ""
    setting_context: str = ""
    key_figures: str = ""
    major_events: str = ""
    underlying_causes: str = ""
    consequences: str = ""
    relevant_data: str = ""
    different_perspectives: str = ""
    key_concepts: str = ""
    industry_overview: str = ""
    target_audience: str = ""
    market_analysis: str = ""
    business_model: str = ""
    marketing_and_sales_strategy: str = ""
    operations: str = ""
    financial_projections: str = ""
    management_team: str = ""
    legal_and_regulatory_environment: str = ""
    risks_and_challenges: str = ""
    opportunities_for_growth: str = ""
    introduction: str = ""
    literature_review: str = ""
    methodology: str = ""
    results: str = ""
    discussion: str = ""
    conclusion: str = ""
    references: str = ""
    appendices: str = ""


class SceneRequest(BaseModel):
    scene_number: int
    summary: str = ""
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    goal: str = ""
    emotional_beat: str = ""
    scene_type: str = ""
    target_word_count: int | None = None


class SearchRequest(BaseModel):
    query: str
    filters: dict[str, str] = Field(default_factory=dict)
    top_k: int = 6


class AnalyzeRequest(BaseModel):
    chapter_start: int | None = None
    chapter_end: int | None = None


class LoreSuggestionResponse(BaseModel):
    index: int
    entity_type: str
    entity_name: str
    field: str
    current_value: str = ""
    proposed_value: str = ""
    reason: str = ""
    source_chapter: int = 0
    status: str = "pending"


class EditSuggestionRequest(BaseModel):
    proposed_value: str


class CharacterStateResponse(BaseModel):
    character_name: str
    chapter_number: int
    emotional_state: str = ""
    knowledge: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)
    physical_state: str = ""
    notes: str = ""


class NarrativeThreadRequest(BaseModel):
    name: str
    thread_type: str = "promise"
    description: str = ""
    opened_chapter: int | None = None
    target_resolution_chapter: int | None = None
    resolved_chapter: int | None = None
    status: str = "open"
    characters_involved: list[str] = Field(default_factory=list)


class NarrativeThreadResponse(BaseModel):
    name: str
    thread_type: str = "promise"
    description: str = ""
    opened_chapter: int | None = None
    target_resolution_chapter: int | None = None
    resolved_chapter: int | None = None
    status: str = "open"
    characters_involved: list[str] = Field(default_factory=list)


class ContinuityNoteResponse(BaseModel):
    chapter_number: int
    note_type: str = ""
    description: str = ""
    entities_involved: list[str] = Field(default_factory=list)
    resolved: bool = False
