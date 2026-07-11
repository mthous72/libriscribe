"""B42 — generation never overwrites the author's lore.

Character stage: name collisions become pending sandbox suggestions; the lorebook
character is untouched. Worldbuilding stage: generated values fill EMPTY fields only;
conflicts with author-written fields become pending sandbox suggestions.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Worldbuilding


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0] if self.responses else ""

    def generate_content_with_json_repair(self, prompt, **kwargs):
        # The real method normalizes to fenced JSON (commit b4c0d06) — mimic that contract.
        out = self.generate_content(prompt, **kwargs)
        return f"```json\n{out}\n```" if out and not out.startswith("```") else out


CHAR_JSON = json.dumps([
    {
        "name": "Maren",
        "age": "34",
        "sex": "Male",
        "physical description": "Completely different invented description.",
        "personality_traits": "Invented, Wrong, Traits",
        "background": "A generated backstory that must not clobber the author's.",
        "motivations": "Generated motivations.",
        "role": "Protagonist",
    },
    {
        "name": "Vex",
        "age": "29",
        "sex": "Female",
        "physical description": "A new supporting character.",
        "personality_traits": "Sly, Loyal",
        "background": "Runs a parts stall in Sector Six.",
        "motivations": "Debt.",
        "role": "Supporting",
    },
])

VOICE_JSON = json.dumps({
    "speech_patterns": "short", "vocabulary_level": "street",
    "verbal_tics": "none", "avoids": "formality", "example_dialogue": ["Hey."],
})


class LoreSafeCharacterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"PROJECTS_DIR": self.tmp.name}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def _pkb(self):
        pkb = ProjectKnowledgeBase(project_name="p", title="Helix", genre="SF", num_chapters=1)
        pkb.project_dir = Path(self.tmp.name) / "p"
        pkb.project_dir.mkdir(parents=True, exist_ok=True)
        pkb.characters["Maren"] = Character(
            name="Maren", background="AUTHOR-WRITTEN backstory.",
            personality_traits="Anxious, Precise", role="Protagonist",
        )
        return pkb

    def test_collision_never_overwrites_and_is_staged(self):
        from libriscribe.agents.character_generator import CharacterGeneratorAgent
        from libriscribe.services import sandbox

        pkb = self._pkb()
        agent = CharacterGeneratorAgent(llm_client=FakeLLM([CHAR_JSON, VOICE_JSON]))
        agent.execute(pkb)

        # Author's Maren untouched
        maren = pkb.get_character("Maren")
        self.assertEqual(maren.background, "AUTHOR-WRITTEN backstory.")
        self.assertEqual(maren.personality_traits, "Anxious, Precise")
        # New character added normally
        self.assertIn("Vex", pkb.characters)
        # Generated Maren staged as a pending update
        runs = sandbox.list_runs("p")
        self.assertEqual(len(runs), 1)
        run = sandbox.get_run("p", runs[0]["id"])
        cands = run["candidates"]
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["name"], "Maren")
        self.assertEqual(cands[0]["op"], "update")
        self.assertEqual(cands[0]["status"], "pending")
        self.assertIn("background", cands[0]["fields"])

    def test_prompt_lists_existing_characters(self):
        from libriscribe.agents.character_generator import CharacterGeneratorAgent

        pkb = self._pkb()
        fake = FakeLLM([CHAR_JSON, VOICE_JSON])
        CharacterGeneratorAgent(llm_client=fake).execute(pkb)
        self.assertIn("EXISTING CHARACTERS", fake.prompts[0])
        self.assertIn("Maren", fake.prompts[0])

    def test_accepting_staged_suggestion_applies_it(self):
        from libriscribe.agents.character_generator import CharacterGeneratorAgent
        from libriscribe.services import sandbox

        pkb = self._pkb()
        CharacterGeneratorAgent(llm_client=FakeLLM([CHAR_JSON, VOICE_JSON])).execute(pkb)
        run_id = sandbox.list_runs("p")[0]["id"]
        run = sandbox.get_run("p", run_id)
        sandbox.update_candidate("p", run_id, run["candidates"][0]["id"], status="accepted")
        result = sandbox.apply_accepted("p", pkb, run_id)
        self.assertEqual(result["applied"], 1)
        self.assertIn("generated backstory", pkb.get_character("Maren").background)


WORLD_JSON = json.dumps({
    "geography": "GENERATED geography.",
    "magic_system": "GENERATED magic system.",
    "history": "GENERATED history.",
})


class LoreSafeWorldbuildingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"PROJECTS_DIR": self.tmp.name}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def _pkb(self):
        pkb = ProjectKnowledgeBase(project_name="p", title="Helix", genre="SF",
                                   category="Fiction", num_chapters=1)
        pkb.project_dir = Path(self.tmp.name) / "p"
        pkb.project_dir.mkdir(parents=True, exist_ok=True)
        pkb.worldbuilding_needed = True
        pkb.worldbuilding = Worldbuilding(magic_system="AUTHOR-WRITTEN magic rules.")
        return pkb

    def test_fills_empty_fields_stages_conflicts(self):
        from libriscribe.agents.worldbuilding import WorldbuildingAgent
        from libriscribe.services import sandbox

        pkb = self._pkb()
        WorldbuildingAgent(llm_client=FakeLLM([WORLD_JSON])).execute(pkb)

        # Author's field untouched; empty fields filled
        self.assertEqual(pkb.worldbuilding.magic_system, "AUTHOR-WRITTEN magic rules.")
        self.assertEqual(pkb.worldbuilding.geography, "GENERATED geography.")
        self.assertEqual(pkb.worldbuilding.history, "GENERATED history.")
        # Conflict staged, pending
        runs = sandbox.list_runs("p")
        self.assertEqual(len(runs), 1)
        run = sandbox.get_run("p", runs[0]["id"])
        cand = run["candidates"][0]
        self.assertEqual(cand["category"], "worldbuilding")
        self.assertEqual(cand["status"], "pending")
        self.assertEqual(cand["fields"], {"magic_system": "GENERATED magic system."})

    def test_accepted_worldbuilding_suggestion_applies(self):
        from libriscribe.agents.worldbuilding import WorldbuildingAgent
        from libriscribe.services import sandbox

        pkb = self._pkb()
        WorldbuildingAgent(llm_client=FakeLLM([WORLD_JSON])).execute(pkb)
        run_id = sandbox.list_runs("p")[0]["id"]
        run = sandbox.get_run("p", run_id)
        sandbox.update_candidate("p", run_id, run["candidates"][0]["id"], status="accepted")
        result = sandbox.apply_accepted("p", pkb, run_id)
        self.assertEqual(result["applied"], 1)
        self.assertEqual(pkb.worldbuilding.magic_system, "GENERATED magic system.")

    def test_no_existing_content_applies_directly_no_run(self):
        from libriscribe.agents.worldbuilding import WorldbuildingAgent
        from libriscribe.services import sandbox

        pkb = self._pkb()
        pkb.worldbuilding = Worldbuilding()  # blank — nothing to protect
        WorldbuildingAgent(llm_client=FakeLLM([WORLD_JSON])).execute(pkb)
        self.assertEqual(pkb.worldbuilding.magic_system, "GENERATED magic system.")
        self.assertEqual(sandbox.list_runs("p"), [])


if __name__ == "__main__":
    unittest.main()
