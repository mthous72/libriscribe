"""B45 Slice 2: brainstorm chat focus on the story spine — concept, chapter, scene.

The chat preview endpoint assembles the exact system prompt without an LLM call, so it's
the cheapest full-stack probe of focus resolution (record + surrounding lore + prose excerpt).
"""
import os
import tempfile
import unittest

STRUCTURED = """## Chapter 1: One

### Scene 1

Maren checked the seals twice before trusting the airlock to hold.

### Scene 2

The corridor hummed with a voice that was not quite CEE's.
"""


class SpineChatFocusTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene, Character

        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(
            project_name="demo", title="Helix", genre="SF",
            logline="A sentient machine fights for her chaos.", num_chapters=2)
        ch1 = Chapter(chapter_number=1, title="One", summary="Maren finds CEE.")
        ch1.scenes.append(Scene(scene_number=1, summary="Airlock check.",
                                characters=["Maren"], goal="Get inside unseen."))
        ch1.scenes.append(Scene(scene_number=2, summary="The corridor voice.",
                                characters=["Maren", "CEE"]))
        kb.add_chapter(ch1)
        kb.add_character(Character(name="Maren", role="protagonist",
                                   background="A black-market broker losing her defenses."))
        project_service.save_kb("demo", kb)
        (pdir / "chapter_1.md").write_text(STRUCTURED, encoding="utf-8")
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def _preview(self, focus_type, focus_name):
        r = self.client.post("/api/projects/demo/chat/preview", json={
            "message": "What should happen next?",
            "focus_type": focus_type, "focus_name": focus_name,
        })
        self.assertEqual(r.status_code, 200)
        return r.json()["system_prompt"]

    def test_scene_focus_carries_record_prose_and_companions(self):
        prompt = self._preview("scene", "1.2")
        self.assertIn("Chapter 1, Scene 2", prompt)          # resolved label
        self.assertIn("The corridor voice.", prompt)         # scene summary
        self.assertIn("chapter_summary", prompt)             # chapter context attached
        self.assertIn("not quite CEE", prompt)               # THIS scene's prose excerpt
        self.assertIn("black-market broker", prompt)         # scene character's brief
        self.assertIn("STORY-STATE CHANGE", prompt)          # scene intent lens

    def test_chapter_focus_lists_scenes_and_prose(self):
        prompt = self._preview("chapter", "1")
        self.assertIn("Chapter 1: One", prompt)
        self.assertIn("Scene 1: Airlock check.", prompt)
        self.assertIn("seals twice", prompt)                 # chapter prose excerpt
        self.assertIn("ESCALATION", prompt)                  # chapter intent lens

    def test_concept_focus_uses_project_meta(self):
        prompt = self._preview("concept", "concept")
        self.assertIn("the story concept", prompt)
        self.assertIn("fights for her chaos", prompt)        # logline in the record
        self.assertIn("PREMISE", prompt)                     # concept intent lens

    def test_unknown_scene_falls_back_to_general_chat(self):
        prompt = self._preview("scene", "9.9")
        self.assertNotIn("being developed", prompt)          # no focus block
        self.assertIn("creative worldbuilding", prompt)      # general prompt path

    def test_lore_focus_still_works(self):
        prompt = self._preview("character", "Maren")
        self.assertIn("Character being developed: Maren", prompt)


if __name__ == "__main__":
    unittest.main()
