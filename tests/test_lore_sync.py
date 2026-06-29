"""Unit tests for LoreSyncService."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from libriscribe.knowledge_base import (
    Character,
    CharacterState,
    ContinuityNote,
    Location,
    LoreEntry,
    LoreSuggestion,
    ProjectKnowledgeBase,
)
from libriscribe.services.lore_sync import LoreSyncService


class TestLoreSyncService(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_dir = Path(self.tmpdir)

        self.kb = ProjectKnowledgeBase(
            project_name="test",
            title="Test Book",
            genre="Fantasy",
            category="Fiction",
        )
        self.kb.add_character(Character(
            name="Elara",
            role="Protagonist",
            personality_traits="Brave, clever",
            motivations="Save the world",
            background="A young mage.",
            relationships={"Kael": "ally"},
        ))
        self.kb.add_location(Location(
            name="Dark Forest",
            description="A dense forest.",
            significance="Home of spirits.",
        ))
        self.kb.add_lore_entry(LoreEntry(
            name="Dragon Pact",
            entry_type="legend",
            description="Ancient pact.",
            related_entities=["Elara"],
        ))

        # Write sample chapter files
        (self.project_dir / "chapter_1.md").write_text(
            "## Chapter 1: The Beginning\n\n"
            "Elara walked through the Dark Forest, her heart pounding. "
            "She had discovered the ancient Dragon Pact mentioned in her mentor's journal. "
            "Kael joined her, and together they pressed deeper into the woods.",
            encoding="utf-8",
        )
        (self.project_dir / "chapter_2.md").write_text(
            "## Chapter 2: Discovery\n\n"
            "Elara found a hidden cave behind the waterfall. Inside, she saw runes "
            "that confirmed the Dragon Pact was real. She felt a surge of determination. "
            "Her relationship with Kael deepened as they shared the danger together.",
            encoding="utf-8",
        )

        self.llm_client = MagicMock()

    def test_analyze_character_calls_llm(self):
        self.llm_client.generate_content_with_json_repair.return_value = json.dumps({
            "field_updates": [
                {
                    "field": "emotional_state",
                    "current_value": "",
                    "proposed_value": "determined, resolute",
                    "reason": "In Chapter 2, Elara felt a surge of determination.",
                }
            ],
            "new_knowledge": ["The Dragon Pact is real"],
            "relationship_changes": {"Kael": "deepening bond"},
            "physical_state_update": None,
            "continuity_issues": [],
        })

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        suggestions = svc.analyze_character("Elara")

        self.assertTrue(len(suggestions) > 0)
        self.llm_client.generate_content_with_json_repair.assert_called_once()

        # Check suggestion types
        fields = [s.field for s in suggestions]
        self.assertIn("emotional_state", fields)
        self.assertIn("knowledge", fields)

    def test_analyze_character_no_chapters(self):
        svc = LoreSyncService(self.llm_client, self.kb, Path("/nonexistent"))
        suggestions = svc.analyze_character("Elara")
        self.assertEqual(suggestions, [])

    def test_analyze_location_calls_llm(self):
        self.llm_client.generate_content_with_json_repair.return_value = json.dumps({
            "field_updates": [
                {
                    "field": "description",
                    "current_value": "A dense forest.",
                    "proposed_value": "A dense, ancient forest with a hidden cave behind a waterfall.",
                    "reason": "Chapter 2 reveals a cave behind a waterfall.",
                }
            ],
            "new_associated_characters": [],
            "continuity_issues": [],
        })

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        suggestions = svc.analyze_location("Dark Forest")

        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0].entity_type, "location")

    def test_analyze_lore_entry_calls_llm(self):
        self.llm_client.generate_content_with_json_repair.return_value = json.dumps({
            "field_updates": [
                {
                    "field": "description",
                    "current_value": "Ancient pact.",
                    "proposed_value": "Ancient pact between dragons and mages, confirmed by rune carvings.",
                    "reason": "Chapter 2 confirms the pact with runes.",
                }
            ],
            "new_related_entities": [],
            "continuity_issues": [],
        })

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        suggestions = svc.analyze_lore_entry("Dragon Pact")

        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0].entity_type, "lore_entry")

    def test_detect_continuity_issues(self):
        self.llm_client.generate_content_with_json_repair.return_value = json.dumps({
            "issues": [
                {
                    "note_type": "inconsistency",
                    "description": "Elara's hair color changes between chapters.",
                    "entities_involved": ["Elara"],
                    "chapter_number": 2,
                }
            ]
        })

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        notes = svc.detect_continuity_issues()

        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].note_type, "inconsistency")
        self.assertIn("Elara", notes[0].entities_involved)

    def test_apply_suggestion_character_field(self):
        self.kb.lore_suggestions = [
            LoreSuggestion(
                entity_type="character",
                entity_name="Elara",
                field="personality_traits",
                current_value="Brave, clever",
                proposed_value="Brave, clever, resolute",
                reason="Grew more determined",
                source_chapter=2,
            )
        ]

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        svc.apply_suggestion(0)

        self.assertEqual(self.kb.lore_suggestions[0].status, "accepted")
        self.assertEqual(self.kb.characters["Elara"].personality_traits, "Brave, clever, resolute")

    def test_apply_suggestion_relationship(self):
        self.kb.lore_suggestions = [
            LoreSuggestion(
                entity_type="character",
                entity_name="Elara",
                field="relationship:Kael",
                current_value="ally",
                proposed_value="deepening bond",
                reason="Shared danger",
                source_chapter=2,
            )
        ]

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        svc.apply_suggestion(0)

        self.assertEqual(self.kb.characters["Elara"].relationships["Kael"], "deepening bond")

    def test_apply_suggestion_emotional_state(self):
        self.kb.lore_suggestions = [
            LoreSuggestion(
                entity_type="character",
                entity_name="Elara",
                field="emotional_state",
                proposed_value="determined",
                source_chapter=2,
            )
        ]

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        svc.apply_suggestion(0)

        states = self.kb.character_states.get("Elara", [])
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0].emotional_state, "determined")
        self.assertEqual(states[0].chapter_number, 2)

    def test_apply_suggestion_location(self):
        self.kb.lore_suggestions = [
            LoreSuggestion(
                entity_type="location",
                entity_name="Dark Forest",
                field="description",
                proposed_value="A dense forest with hidden caves.",
                source_chapter=2,
            )
        ]

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        svc.apply_suggestion(0)

        self.assertEqual(self.kb.locations["Dark Forest"].description, "A dense forest with hidden caves.")

    def test_reject_suggestion(self):
        self.kb.lore_suggestions = [
            LoreSuggestion(
                entity_type="character",
                entity_name="Elara",
                field="motivations",
                proposed_value="new motivation",
            )
        ]

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        svc.reject_suggestion(0)

        self.assertEqual(self.kb.lore_suggestions[0].status, "rejected")
        # Original value unchanged
        self.assertEqual(self.kb.characters["Elara"].motivations, "Save the world")

    def test_chapter_range_filtering(self):
        self.llm_client.generate_content_with_json_repair.return_value = json.dumps({
            "field_updates": [],
            "new_knowledge": [],
            "relationship_changes": {},
            "physical_state_update": None,
            "continuity_issues": [],
        })

        svc = LoreSyncService(self.llm_client, self.kb, self.project_dir)
        suggestions = svc.analyze_character("Elara", chapter_range=(1, 1))

        # Should still call LLM (chapter 1 mentions Elara)
        self.llm_client.generate_content_with_json_repair.assert_called_once()

    def test_kb_backward_compat(self):
        """New fields have defaults, so loading old project data works."""
        kb = ProjectKnowledgeBase(project_name="old_project")
        self.assertEqual(kb.character_states, {})
        self.assertEqual(kb.continuity_notes, [])
        self.assertEqual(kb.lore_suggestions, [])


if __name__ == "__main__":
    unittest.main()
