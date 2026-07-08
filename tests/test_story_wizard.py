"""B38 story wizard — tailored questions stored in dynamic_questions; answers elaborate to sandbox."""
import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase, Character
from libriscribe.services import story_wizard


class QuestionGenerationTests(unittest.TestCase):
    class _QClient:
        def generate_content_with_json_repair(self, prompt, **kw):
            self.prompt = prompt
            return json.dumps({"questions": ["Who is the detective?", "What is the central crime?"]})

    def test_questions_stored_preserving_existing_answers(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="Mystery")
        kb.dynamic_questions = {"Old question?": "My kept answer"}
        out = story_wizard.generate_questions(self._QClient(), kb)
        self.assertEqual(out["Old question?"], "My kept answer")   # preserved
        self.assertEqual(out["Who is the detective?"], "")          # new, unanswered
        self.assertIn("Who is the detective?", kb.dynamic_questions)

    def test_prompt_carries_project_specifics_and_lore(self):
        kb = ProjectKnowledgeBase(project_name="t", title="The Ash Case", genre="Mystery")
        kb.add_character(Character(name="Maren", role="detective"))
        c = self._QClient()
        story_wizard.generate_questions(c, kb)
        self.assertIn("Mystery", c.prompt)
        self.assertIn("The Ash Case", c.prompt)
        self.assertIn("Maren", c.prompt)   # existing-project mode: lore digest included

    def test_fallback_to_core_on_bad_output(self):
        class _Bad:
            def generate_content_with_json_repair(self, prompt, **kw):
                return "not json at all"
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        out = story_wizard.generate_questions(_Bad(), kb)
        self.assertEqual(set(out), set(story_wizard.CORE_QUESTIONS))


class ElaborateTests(unittest.TestCase):
    class _EClient:
        """extract_from_text finds what the answers describe; per-type enrich adds fields."""
        def generate_content_with_json_repair(self, prompt, **kw):
            if "brainstorming note" in prompt:   # extraction pass
                return json.dumps({"characters": [{"name": "Tya", "role": "broker"}],
                                   "locations": [], "lore": [], "arcs": []})
            if "DIALOGUE VOICE" in prompt:       # voice pass piggybacked by extract_for_type
                return json.dumps({})
            return "```json\n" + json.dumps({"motivations": "escape her debts"}) + "\n```"

    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_elaborate_stages_candidates_from_answers(self):
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.dynamic_questions = {"Who are the main characters?": "Tya, a debt-ridden broker."}
        self.svc.save_kb("demo", kb)
        run = story_wizard.elaborate(self._EClient(), kb, "demo", max_workers=1)
        self.assertIsNotNone(run)
        self.assertEqual(run["seed"]["kind"], "wizard")
        c = run["candidates"][0]
        self.assertEqual((c["category"], c["name"], c["op"], c["status"]),
                         ("characters", "Tya", "new", "pending"))
        self.assertEqual(c["fields"].get("motivations"), "escape her debts")  # enriched
        self.assertEqual(c["fields"].get("role"), "broker")                    # from extraction

    def test_elaborate_marks_existing_entity_update(self):
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.add_character(Character(name="Tya", role="broker"))
        kb.dynamic_questions = {"Q?": "More about Tya."}
        self.svc.save_kb("demo", kb)
        run = story_wizard.elaborate(self._EClient(), kb, "demo", max_workers=1)
        self.assertEqual(run["candidates"][0]["op"], "update")

    def test_mention_fallback_stages_known_entities_when_sweep_fails(self):
        # The multi-entity discovery sweep is the flakiest pass on small local models.
        # If it returns NOTHING, answers that mention existing KB entities must still stage
        # (word-boundary matched, enriched via the per-entity extractor).
        class _SweepFails:
            def generate_content_with_json_repair(self, prompt, **kw):
                if "brainstorming note" in prompt:   # discovery sweep -> nothing
                    return "not json at all"
                if "DIALOGUE VOICE" in prompt:
                    return json.dumps({})
                return "```json\n" + json.dumps({"motivations": "step into autonomy"}) + "\n```"
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.add_character(Character(name="CEE"))
        kb.add_character(Character(name="Wren"))
        kb.add_character(Character(name="Unmentioned"))
        kb.dynamic_questions = {"Climax?": "CEE steps into autonomy; we proceed as Wren planned."}
        self.svc.save_kb("demo", kb)
        run = story_wizard.elaborate(_SweepFails(), kb, "demo", max_workers=1)
        self.assertIsNotNone(run)
        names = sorted(c["name"] for c in run["candidates"])
        self.assertEqual(names, ["CEE", "Wren"])           # mentioned -> staged ("proceed" ≠ CEE)
        self.assertNotIn("Unmentioned", names)
        self.assertTrue(all(c["op"] == "update" for c in run["candidates"]))
        self.assertEqual(run["candidates"][0]["fields"].get("motivations"), "step into autonomy")

    def test_no_answers_returns_none(self):
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.dynamic_questions = {"Q?": ""}
        self.assertIsNone(story_wizard.elaborate(self._EClient(), kb, "demo"))


class WizardEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)
        project_service.save_kb("demo", ProjectKnowledgeBase(project_name="demo", title="T", genre="F"))
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_put_and_get_questions(self):
        r = self.client.put("/api/projects/demo/wizard/questions",
                            json={"questions": {"How many leads?": "Two"}})
        self.assertEqual(r.status_code, 200)
        g = self.client.get("/api/projects/demo/wizard/questions").json()
        self.assertEqual(g["questions"], {"How many leads?": "Two"})

    def test_elaborate_without_answers_400(self):
        r = self.client.post("/api/projects/demo/wizard/elaborate")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
