"""Generate examples/project_data.template.json — the reference for a project's data file.

The template documents EVERY field of ProjectKnowledgeBase (and each nested model) with a
populated example, generated FROM the pydantic models so it can't silently drift from the
code. Regenerate after any knowledge_base.py change:

    PYTHONPATH=src python scripts/generate_kb_template.py

tests/test_kb_template.py fails whenever the models change and this wasn't re-run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

TEMPLATE_PATH = REPO / "examples" / "project_data.template.json"


def build_template_kb():
    """A fully-populated example KB: every collection holds one illustrative entry."""
    from libriscribe.knowledge_base import (
        ArcMilestone, Chapter, Character, CharacterState, ContinuityNote, LoreEntry,
        LoreSuggestion, Location, NarrativeThread, ProjectKnowledgeBase, Scene,
        StoryArc, TimelineEvent, VoiceProfile, Worldbuilding,
    )

    kb = ProjectKnowledgeBase(
        project_name="example_project",
        title="The Example Title",
        genre="Fantasy",
        description="One-paragraph premise of the story.",
        category="Fiction",
        language="English",
        num_characters=3,
        worldbuilding_needed=True,
        review_preference="Human",
        book_length="Novel",
        logline="A one-sentence summary of the story.",
        tone="Dark",
        target_audience="Adult",
        num_chapters=12,
        target_word_count=80000,
        suggested_title="",           # generation SUGGESTS here; never overwrites `title`
        suggested_logline="",
        suggested_description="",
        suggested_num_chapters=None,
        generation_mode="step",       # 'step' = one stage per run (default) | 'auto' = legacy full run
        canon_rules=[                  # B32: INVIOLABLE story-mechanics rules, one per line
            "Past tense throughout.",
            "The protagonist never uses modern slang.",
        ],
        prose_register=None,           # B36 (gated): 1-5 intensity; None = off
        llm_provider="local",
        model="example-writing-model",
        utility_model="example-utility-model",
        max_concurrency=4,             # B29: concurrent LLM calls for batch work; 1 = serial
        dynamic_questions={            # B38 wizard: {question: answer} ('' = unanswered)
            "Who are the main characters?": "",
        },
    )

    kb.add_character(Character(
        name="Example Character",
        age="34",
        sex="female",
        sexual_orientation="bisexual",
        physical_description="Tall; grey eyes; a scar across one brow.",
        personality_traits="Wry, guarded, loyal",
        background="Raised in the capital; exiled after the coup.",
        motivations="Clear her family's name.",
        relationships={"Second Character": "estranged sibling"},
        role="protagonist",
        internal_conflicts="Duty to family vs. hunger for a quiet life.",
        external_conflicts="Hunted by the Compact.",
        character_arc="From fugitive to reluctant leader.",
        voice_profile=VoiceProfile(
            speech_patterns="Short, clipped sentences.",
            vocabulary_level="Plain and direct",
            verbal_tics="Says 'aye' when conceding a point.",
            avoids="Never swears.",
            example_dialogue=["Aye. But not today.", "Ask me again when the ash settles."],
        ),
    ))
    kb.add_location(Location(
        name="Example Keep",
        description="A black-stone fortress above the ash plains.",
        significance="Seat of the old dynasty; the story's endpoint.",
        associated_characters=["Example Character"],
        first_appearance=2,
        tags=["fortress", "ancestral"],
    ))
    kb.lore_entries["Example Compact"] = LoreEntry(
        name="Example Compact",
        entry_type="faction",
        description="A pact of exiled houses that enforces the old law.",
        significance="The antagonist force pressing on every arc.",
        related_entities=["Example Character", "Example Keep"],
        first_appearance=1,
        tags=["faction"],
    )
    kb.story_arcs["Example Arc"] = StoryArc(
        name="Example Arc",
        description="The fall and retaking of the Keep.",
        arc_type="main",
        chapters_involved=[1, 6, 12],
        characters_involved=["Example Character"],
        status="active",
        resolution_notes="Resolves when the Keep falls in the finale.",
        milestones=[ArcMilestone(
            name="The gates fall",
            milestone_type="climax",
            target_chapter=12,
            actual_chapter=None,
            description="The Compact breaches the Keep.",
            status="pending",
        )],
    )
    kb.narrative_threads["Example Thread"] = NarrativeThread(
        name="Example Thread",
        thread_type="promise",
        description="Who sent the unsigned letter?",
        opened_chapter=1,
        target_resolution_chapter=10,
        resolved_chapter=None,
        status="open",
        characters_involved=["Example Character"],
    )
    kb.character_states["Example Character"] = [CharacterState(
        character_name="Example Character",
        chapter_number=1,
        emotional_state="wary",
        knowledge=["Learns the letter bears the Compact's seal."],
        relationships={"Second Character": "suspicious of"},
        physical_state="uninjured",
        notes="Ends the chapter at Example Keep.",
    )]
    kb.timeline_events = [TimelineEvent(
        chapter_number=1,
        description="The unsigned letter arrives.",
        characters_involved=["Example Character"],
    )]
    kb.continuity_notes = [ContinuityNote(
        chapter_number=3,
        note_type="inconsistency",
        description="Eye colour described as brown; canon says grey.",
        entities_involved=["Example Character"],
        resolved=False,
    )]
    kb.lore_suggestions = [LoreSuggestion(
        entity_type="character",
        entity_name="Example Character",
        field="motivations",
        current_value="Clear her family's name.",
        proposed_value="Clear her family's name — and take the Keep back.",
        reason="Chapter 6 escalates her goal.",
        source_chapter=6,
        status="pending",
    )]
    kb.worldbuilding = Worldbuilding(
        geography="Volcanic ash plains ringed by black mountains.",
        culture_and_society="Clan-based; oaths outrank written law.",
        history="The dynasty fell a generation ago.",
        rules_and_laws="Oath-breaking is punishable by exile.",
        technology_level="Late-medieval with early gunpowder.",
        magic_system="Blood-cost sorcery; nothing raises the dead.",
        key_locations="Example Keep; the Ash Road.",
        important_organizations="The Example Compact.",
        flora_and_fauna="Ash-adapted scrub; carrion drakes.",
        languages="Common tongue; Old Dynastic in rites.",
        religions_and_beliefs="Ancestor veneration.",
        economy="Barter and salt-scrip.",
        conflicts="Compact vs. the exiled heirs.",
    )
    kb.add_chapter(Chapter(
        chapter_number=1,
        title="The Letter",
        summary="An unsigned letter pulls the protagonist out of hiding.",
        scenes=[Scene(
            scene_number=1,
            summary="The letter arrives at the waystation.",
            characters=["Example Character"],
            setting="Ash Road waystation",
            goal="Hook: establish the threat and the summons.",
            emotional_beat="unease",
            scene_type="quiet",
            target_word_count=1200,
        )],
    ))
    kb.outline = "# Outline\n\nChapter 1: The Letter — ..."
    return kb


def template_dict() -> dict:
    kb = build_template_kb()
    data = json.loads(kb.model_dump_json())
    data.pop("project_dir", None)  # runtime-only path, not part of the format
    return data


def main() -> None:
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.write_text(json.dumps(template_dict(), indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    print(f"wrote {TEMPLATE_PATH}")


if __name__ == "__main__":
    main()
