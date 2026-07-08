"""World as a first-class brainstorm focus — focused apply routes into worldbuilding fields."""
import json
import unittest

from libriscribe.knowledge_base import ProjectKnowledgeBase, Worldbuilding
from libriscribe.services import lore_intake, lore_prompts
import libriscribe.api.routers.chat as chat


class WorldFieldsTests(unittest.TestCase):
    def test_worldbuilding_type_fields_and_descriptions(self):
        fields = lore_intake.SMART_FIELDS["worldbuilding"]
        for f in ("geography", "magic_system", "conflicts", "economy"):
            self.assertIn(f, fields)
        for f in fields:
            self.assertIn(f, lore_prompts.FIELD_DESCRIPTIONS)


class WorldFocusedApplyTests(unittest.TestCase):
    class _C:
        def __init__(self):
            self.prompt = None
        def generate_content_with_json_repair(self, prompt, **kw):
            self.prompt = prompt
            return json.dumps({"geography": "Volcanic ash plains.", "magic_system": "Blood-cost sorcery."})

    def test_world_apply_stages_worldbuilding_not_entities(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="Fantasy")
        client = self._C()
        cats = lore_intake.extract_focused(client, kb, "world", "World", "the ash plains and blood magic")
        self.assertEqual(cats["characters"], [])
        wb = cats["worldbuilding"]
        self.assertEqual(wb["fields"]["geography"], "Volcanic ash plains.")
        self.assertEqual(wb["fields"]["magic_system"], "Blood-cost sorcery.")
        # And the whole thing merges through the existing worldbuilding path.
        proposal = lore_intake.build_proposal(kb, cats)
        self.assertEqual(proposal["worldbuilding"]["status"], "new")
        lore_intake.merge_apply(kb, {"worldbuilding": proposal["worldbuilding"]})
        self.assertEqual(kb.worldbuilding.geography, "Volcanic ash plains.")

    def test_world_apply_respects_aspect_narrowing(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="Fantasy")
        cats = lore_intake.extract_focused(self._C(), kb, "world", "World", "...", aspect="geography")
        self.assertEqual(set(cats["worldbuilding"]["fields"]), {"geography"})

    def test_world_apply_passes_existing_fields(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="Fantasy")
        kb.worldbuilding = Worldbuilding(geography="Old plains.")
        client = self._C()
        lore_intake.extract_focused(client, kb, "world", "World", "...")
        self.assertIn("Old plains.", client.prompt)   # augment-don't-fight context included

    def test_counts_include_worldbuilding_only_result(self):
        cats = lore_intake._empty_cats()
        cats["worldbuilding"] = {"fields": {"geography": "x"}}
        self.assertEqual(lore_intake.cats_count(cats), 1)   # parse endpoint won't 422


class WorldFocusPromptTests(unittest.TestCase):
    def test_world_focus_entity_and_lens(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        kb.worldbuilding = Worldbuilding(geography="Ash plains")
        entity, resolved = chat._get_focus_entity(kb, "world", "World")
        self.assertEqual(resolved, "World")
        self.assertEqual(entity.geography, "Ash plains")
        # Lens present and world-specific.
        from types import SimpleNamespace
        p = chat._focus_system_prompt(SimpleNamespace(title="B", genre="F"), "world", "World",
                                      "(rec)", "(lore)", chat._VERBOSITY["medium"]["directive"])
        self.assertIn("RULES", p)
        self.assertIn("TEXTURE", p)

    def test_world_focus_works_without_existing_worldbuilding(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        entity, resolved = chat._get_focus_entity(kb, "world", "World")
        self.assertEqual(resolved, "World")
        self.assertIsNotNone(entity)   # empty container, not a crash


if __name__ == "__main__":
    unittest.main()
