"""B45 Slice 3: single-scene write/rewrite + splice — the small-bites core.

splice_scene must be byte-preserving for every OTHER scene; write_scene must carry the full
steering stack (canon, recap, continuity, guard) scoped to one scene and never save.
"""
import os
import tempfile
import unittest

from libriscribe.services.scene_prose import split_chapter, splice_scene

CHAPTER = """## Chapter 2: The Descent

### Scene 1

Maren checked the seals twice.

### Scene 2

The corridor hummed.

### Scene 3

CEE's pigment flared amber.
"""


class SpliceSceneTests(unittest.TestCase):
    def test_replace_middle_scene_preserves_others(self):
        out = splice_scene(CHAPTER, 2, "A brand new middle scene.")
        split = split_chapter(out)
        self.assertEqual(split.header, "## Chapter 2: The Descent")
        self.assertEqual(split.get_scene(1).body, "Maren checked the seals twice.")
        self.assertEqual(split.get_scene(2).body, "A brand new middle scene.")
        self.assertEqual(split.get_scene(3).body, "CEE's pigment flared amber.")

    def test_append_missing_scene_in_numeric_order(self):
        out = splice_scene(CHAPTER, 4, "The airlock finally opened.")
        split = split_chapter(out)
        self.assertEqual([b.scene_number for b in split.scenes], [1, 2, 3, 4])

    def test_empty_text_creates_scaffold(self):
        out = splice_scene("", 1, "First words.", chapter_number=5, chapter_title="Five")
        split = split_chapter(out)
        self.assertEqual(split.header, "## Chapter 5: Five")
        self.assertEqual(split.get_scene(1).body, "First words.")

    def test_unstructured_refused(self):
        with self.assertRaises(ValueError):
            splice_scene("A wall of prose without markers.", 1, "x")

    def test_roundtrip_idempotent(self):
        once = splice_scene(CHAPTER, 2, "New.")
        twice = splice_scene(once, 2, "New.")
        self.assertEqual(once, twice)


class _FakeClient:
    def __init__(self, response="Fresh scene prose that moves the story forward."):
        self.prompts = []
        self.response = response
        self.model = ""

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.response

    def set_model(self, m):
        self.model = m


class WriteSceneTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene

        self.project_dir = project_service.get_projects_dir() / "demo"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="Helix", genre="SF", num_chapters=3)
        kb.canon_rules = ["CEE's pigmentation tracks her emotional state."]
        ch = Chapter(chapter_number=2, title="The Descent", summary="Down they go.")
        ch.scenes.append(Scene(scene_number=1, summary="Seals.", characters=["Maren"]))
        ch.scenes.append(Scene(scene_number=2, summary="The hum.", characters=["Maren"],
                               goal="Reach the core hatch."))
        ch.scenes.append(Scene(scene_number=3, summary="Amber flare.", characters=["CEE"]))
        kb.add_chapter(ch)
        project_service.save_kb("demo", kb)
        (self.project_dir / "chapter_2.md").write_text(CHAPTER, encoding="utf-8")
        self.kb = project_service.load_kb("demo")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def _write(self, scene_number, guidance="", monkey_client=None):
        from unittest import mock
        from libriscribe.services import scene_writer

        fake = monkey_client or _FakeClient()
        with mock.patch("libriscribe.services.project_service.create_llm_client", return_value=fake):
            result = scene_writer.write_scene(self.kb, self.project_dir, 2, scene_number, guidance)
        return result, fake

    def test_prompt_carries_steering_and_returns_unsaved(self):
        result, fake = self._write(2, guidance="More menace in the hum.")
        prompt = fake.prompts[0]
        self.assertIn("pigmentation tracks", prompt)          # canon rules bound
        self.assertIn("Reach the core hatch", prompt)         # this scene's brief
        self.assertIn("Maren checked the seals twice.", prompt)  # prior-scene continuity
        self.assertIn("More menace in the hum.", prompt)      # author guidance appended
        self.assertEqual(result["original"], "The corridor hummed.")
        self.assertIn("Fresh scene prose", result["revised"])
        # NOT saved: the file still has the old scene 2.
        text = (self.project_dir / "chapter_2.md").read_text(encoding="utf-8")
        self.assertIn("The corridor hummed.", text)

    def test_missing_scene_raises(self):
        from libriscribe.services import scene_writer
        with self.assertRaises(ValueError):
            scene_writer.write_scene(self.kb, self.project_dir, 2, 9)

    def test_unstructured_chapter_refused(self):
        (self.project_dir / "chapter_2.md").write_text("No markers here.", encoding="utf-8")
        from libriscribe.services import scene_writer
        with self.assertRaises(ValueError):
            scene_writer.write_scene(self.kb, self.project_dir, 2, 2)

    def test_unwritten_chapter_scene_one_uses_prev_chapter_tail(self):
        from libriscribe.knowledge_base import Chapter, Scene
        ch3 = Chapter(chapter_number=3, title="Three", summary="Next.")
        ch3.scenes.append(Scene(scene_number=1, summary="Opening.", characters=["Maren"]))
        self.kb.add_chapter(ch3)
        result, fake = self._write_ch(3, 1)
        self.assertIn("CEE's pigment flared amber.", fake.prompts[0])  # ch2 tail as continuity
        self.assertEqual(result["original"], "")

    def _write_ch(self, chapter, scene_number):
        from unittest import mock
        from libriscribe.services import scene_writer

        fake = _FakeClient()
        with mock.patch("libriscribe.services.project_service.create_llm_client", return_value=fake):
            result = scene_writer.write_scene(self.kb, self.project_dir, chapter, scene_number)
        return result, fake


class SceneEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene

        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F", num_chapters=2)
        ch = Chapter(chapter_number=2, title="The Descent", summary="Down.")
        ch.scenes.append(Scene(scene_number=1, summary="Seals."))
        ch.scenes.append(Scene(scene_number=2, summary="Hum."))
        kb.add_chapter(ch)
        project_service.save_kb("demo", kb)
        (pdir / "chapter_2.md").write_text(CHAPTER, encoding="utf-8")
        self.pdir = pdir
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_put_scene_prose_splices(self):
        r = self.client.put("/api/projects/demo/chapters/2/scene-prose/2",
                            json={"text": "Rewritten hum."})
        self.assertEqual(r.status_code, 200)
        text = (self.pdir / "chapter_2.md").read_text(encoding="utf-8")
        self.assertIn("Rewritten hum.", text)
        self.assertIn("Maren checked the seals twice.", text)   # neighbors untouched
        self.assertIn("CEE's pigment flared amber.", text)
        self.assertNotIn("The corridor hummed.", text)

    def test_put_prefers_revised_file(self):
        (self.pdir / "chapter_2_revised.md").write_text(CHAPTER, encoding="utf-8")
        self.client.put("/api/projects/demo/chapters/2/scene-prose/1", json={"text": "New one."})
        revised = (self.pdir / "chapter_2_revised.md").read_text(encoding="utf-8")
        base = (self.pdir / "chapter_2.md").read_text(encoding="utf-8")
        self.assertIn("New one.", revised)                       # revised file updated…
        self.assertNotIn("New one.", base)                       # …base untouched

    def test_put_unstructured_conflict(self):
        (self.pdir / "chapter_2.md").write_text("No markers.", encoding="utf-8")
        r = self.client.put("/api/projects/demo/chapters/2/scene-prose/1", json={"text": "x"})
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
