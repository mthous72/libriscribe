"""Unit tests for ContextBuilder."""

import unittest

from libriscribe.knowledge_base import (
    Character,
    Chapter,
    CharacterState,
    Location,
    LoreEntry,
    ProjectKnowledgeBase,
    Scene,
    Worldbuilding,
)
from libriscribe.services.context_builder import ContextBuilder, TokenBudget


class TestTokenBudget(unittest.TestCase):
    def test_consume_fits(self):
        budget = TokenBudget(500)
        text = "Hello world this is a test"
        result = budget.consume(text)
        self.assertEqual(result, text)
        self.assertGreater(budget.used, 0)

    def test_consume_truncates(self):
        budget = TokenBudget(10)
        text = " ".join(["word"] * 100)
        result = budget.consume(text)
        self.assertTrue(result.endswith("..."))
        self.assertTrue(budget.exhausted())

    def test_consume_empty_budget(self):
        budget = TokenBudget(0)
        result = budget.consume("anything")
        self.assertEqual(result, "")

    def test_remaining(self):
        budget = TokenBudget(100)
        self.assertEqual(budget.remaining(), 100)
        budget.consume("Some words here")
        self.assertLess(budget.remaining(), 100)


class TestContextBuilder(unittest.TestCase):
    def _make_kb(self, **overrides):
        defaults = dict(
            project_name="test",
            title="Test Book",
            genre="Fantasy",
            category="Fiction",
        )
        defaults.update(overrides)
        return ProjectKnowledgeBase(**defaults)

    def test_empty_context(self):
        kb = self._make_kb()
        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="Test", characters=[], setting="")
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)
        self.assertEqual(result, "")

    def test_character_profiles_included(self):
        kb = self._make_kb()
        kb.add_character(Character(
            name="Elara",
            role="Protagonist",
            personality_traits="Brave, clever",
            motivations="Save the world",
            background="A young mage from the north.",
        ))

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="A fight", characters=["Elara"])
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)

        self.assertIn("Elara", result)
        self.assertIn("Protagonist", result)
        self.assertIn("Brave, clever", result)

    def test_chapter_recaps_included(self):
        kb = self._make_kb()
        kb.add_chapter(Chapter(
            chapter_number=1, title="Beginning", summary="The journey begins."
        ))
        kb.add_chapter(Chapter(
            chapter_number=2, title="Rising", summary="Conflict arises."
        ))

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="A fight", characters=[])
        chapter = Chapter(chapter_number=3, title="Ch3")
        result = builder.build_scene_context(3, scene, chapter)

        self.assertIn("PREVIOUS CHAPTERS", result)
        self.assertIn("The journey begins", result)
        self.assertIn("Conflict arises", result)

    def test_location_context_included(self):
        kb = self._make_kb()
        kb.add_location(Location(
            name="Dark Forest",
            description="A dense, ancient forest shrouded in mist.",
            significance="Home of the elder spirits.",
        ))

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=[], setting="Dark Forest")
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)

        self.assertIn("Dark Forest", result)
        self.assertIn("dense, ancient forest", result)

    def test_worldbuilding_context_for_fiction(self):
        kb = self._make_kb(
            worldbuilding_needed=True,
        )
        kb.worldbuilding = Worldbuilding(
            magic_system="Elemental magic based on crystal resonance.",
            geography="Vast continents separated by magical seas.",
        )

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=[])
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)

        self.assertIn("WORLDBUILDING", result)
        self.assertIn("crystal resonance", result)

    def test_lore_context_matched_by_character(self):
        kb = self._make_kb()
        kb.add_lore_entry(LoreEntry(
            name="Dragon Pact",
            entry_type="legend",
            description="An ancient pact between dragons and mages.",
            related_entities=["Elara"],
            tags=["magic"],
        ))

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=["Elara"])
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)

        self.assertIn("Dragon Pact", result)

    def test_character_states_included(self):
        kb = self._make_kb()
        kb.character_states = {
            "Elara": [
                CharacterState(
                    character_name="Elara",
                    chapter_number=2,
                    emotional_state="Determined",
                    knowledge=["Knows the gate location"],
                )
            ]
        }

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=["Elara"])
        chapter = Chapter(chapter_number=3, title="Ch3")
        result = builder.build_scene_context(3, scene, chapter)

        self.assertIn("CHARACTER STATES", result)
        self.assertIn("Determined", result)

    def test_character_states_not_included_for_current_chapter(self):
        kb = self._make_kb()
        kb.character_states = {
            "Elara": [
                CharacterState(
                    character_name="Elara",
                    chapter_number=3,
                    emotional_state="Angry",
                )
            ]
        }

        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=["Elara"])
        chapter = Chapter(chapter_number=3, title="Ch3")
        result = builder.build_scene_context(3, scene, chapter)

        self.assertNotIn("CHARACTER STATES", result)

    def test_unknown_character_skipped(self):
        kb = self._make_kb()
        builder = ContextBuilder(kb)
        scene = Scene(scene_number=1, summary="X", characters=["NonExistent"])
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)
        self.assertNotIn("CHARACTER PROFILES", result)

    def test_budget_limits_output(self):
        kb = self._make_kb()
        # Add many characters to test budget limiting
        for i in range(20):
            kb.add_character(Character(
                name=f"Character{i}",
                role="Supporting",
                personality_traits="Trait " * 50,
                motivations="Motivation " * 50,
                background="Background " * 50,
            ))

        builder = ContextBuilder(kb)
        builder.MAX_CONTEXT_TOKENS = 200  # Very small budget
        scene = Scene(
            scene_number=1, summary="X",
            characters=[f"Character{i}" for i in range(20)],
        )
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)

        # Should have some content but be truncated
        word_count = len(result.split())
        self.assertLess(word_count, 500)

    def test_no_retrieval_when_no_service(self):
        kb = self._make_kb()
        builder = ContextBuilder(kb, search_service=None)
        scene = Scene(scene_number=1, summary="X", characters=[])
        chapter = Chapter(chapter_number=1, title="Ch1")
        result = builder.build_scene_context(1, scene, chapter)
        self.assertNotIn("PREVIOUSLY ESTABLISHED", result)


if __name__ == "__main__":
    unittest.main()
