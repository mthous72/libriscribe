"""Phase 0b — lore digest + grounding of concept/outline in the author's established world."""
import unittest

from libriscribe.knowledge_base import (
    ProjectKnowledgeBase, Character, Location, LoreEntry, StoryArc, NarrativeThread, Worldbuilding,
)
from libriscribe.services import lore_digest


def _rich_kb():
    kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="Fantasy")
    kb.add_character(Character(name="Maren", role="protagonist", motivations="freedom",
                               character_arc="learns to trust"))
    kb.add_character(Character(name="Tya", role="broker"))
    kb.add_location(Location(name="The Keep", description="A black stone fortress."))
    kb.lore_entries["Ashfall Compact"] = LoreEntry(name="Ashfall Compact", entry_type="faction",
                                                   description="A pact of exiled houses.")
    kb.story_arcs["Fall"] = StoryArc(name="Fall", status="active", description="The Keep falls.")
    kb.narrative_threads["Debt"] = NarrativeThread(name="Debt", status="open",
                                                   description="Tya owes the Compact.")
    kb.worldbuilding = Worldbuilding(geography="Volcanic ash plains.")
    return kb


class LoreDigestTests(unittest.TestCase):
    def test_digest_covers_all_entity_kinds(self):
        d = lore_digest.build_lore_digest(_rich_kb())
        for expected in ("CHARACTERS", "Maren", "protagonist", "STORY ARCS", "Fall",
                         "NARRATIVE THREADS", "Debt", "WORLD", "Volcanic",
                         "LOCATIONS", "The Keep", "CODEX", "Ashfall Compact"):
            self.assertIn(expected, d)

    def test_empty_kb_yields_empty_digest_and_block(self):
        kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="F")
        self.assertEqual(lore_digest.build_lore_digest(kb), "")
        self.assertEqual(lore_digest.grounding_block(kb), "")

    def test_budget_truncates_but_keeps_characters_first(self):
        kb = _rich_kb()
        for i in range(60):
            kb.add_character(Character(name=f"Extra {i}", role="minor"))
        d = lore_digest.build_lore_digest(kb, max_tokens=200)
        self.assertIn("CHARACTERS", d)          # highest priority survives
        self.assertNotIn("CODEX", d)            # lowest priority truncated away

    def test_grounding_block_carries_binding_instruction(self):
        b = lore_digest.grounding_block(_rich_kb())
        self.assertIn("ESTABLISHED LORE", b)
        self.assertIn("Do NOT invent replacements", b)


class GroundingInjectionTests(unittest.TestCase):
    """Concept + outline prompts carry the established-lore block when lore exists."""

    class _CaptureClient:
        def __init__(self):
            self.prompts = []
        def generate_content_with_json_repair(self, prompt, **kw):
            self.prompts.append(prompt)
            return '```json\n{"title": "X", "logline": "Y", "description": "Z"}\n```'
        def generate_content(self, prompt, **kw):
            self.prompts.append(prompt)
            return "critique text"

    def test_concept_prompts_include_lore_block(self):
        from libriscribe.agents.concept_generator import ConceptGeneratorAgent
        client = self._CaptureClient()
        kb = _rich_kb()
        ConceptGeneratorAgent(client).execute(kb)
        self.assertTrue(client.prompts)
        # Initial + refine prompts both grounded (critique operates on the JSON, not the world).
        self.assertIn("ESTABLISHED LORE", client.prompts[0])
        self.assertIn("Maren", client.prompts[0])
        self.assertIn("ESTABLISHED LORE", client.prompts[-1])
        # And the canonical title is still untouched (0a behavior holds).
        self.assertEqual(kb.title, "Mine")
        self.assertEqual(kb.suggested_title, "X")

    def test_concept_prompt_clean_when_no_lore(self):
        from libriscribe.agents.concept_generator import ConceptGeneratorAgent
        client = self._CaptureClient()
        kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="F")
        ConceptGeneratorAgent(client).execute(kb)
        self.assertNotIn("ESTABLISHED LORE", client.prompts[0])

    def test_outline_prompt_includes_lore_block(self):
        from libriscribe.agents.outliner import OutlinerAgent

        captured = []

        class _OutlineClient:
            def generate_content(self, prompt, **kw):
                captured.append(prompt)
                return ""   # abort after the first call — we only need the prompt
        OutlinerAgent(_OutlineClient()).execute(_rich_kb())
        self.assertTrue(captured)
        self.assertIn("ESTABLISHED LORE", captured[0])
        self.assertIn("The Keep", captured[0])


if __name__ == "__main__":
    unittest.main()
