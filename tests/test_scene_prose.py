"""B45 Slice 1: scene_prose splitter + scene-prose / workbench-tree endpoints.

Chapter files are split at the '### Scene N' markers ChapterWriterAgent emits; files
without markers (pre-B39 / hand-pasted) must be reported unstructured, not mangled.
"""
import os
import tempfile
import unittest

from libriscribe.services.scene_prose import split_chapter

STRUCTURED = """## Chapter 2: The Descent

### Scene 1

Maren checked the seals twice.

She did not trust the airlock.

### Scene 2

The corridor hummed.
"""


class SplitChapterTests(unittest.TestCase):
    def test_structured_split(self):
        split = split_chapter(STRUCTURED)
        self.assertFalse(split.unstructured)
        self.assertEqual(split.header, "## Chapter 2: The Descent")
        self.assertEqual([b.scene_number for b in split.scenes], [1, 2])
        self.assertIn("seals twice", split.scenes[0].body)
        self.assertIn("did not trust", split.scenes[0].body)  # multi-paragraph kept
        self.assertNotIn("### Scene", split.scenes[0].body)   # marker excluded from body
        self.assertEqual(split.scenes[1].body, "The corridor hummed.")
        self.assertEqual(split.get_scene(2).word_count, 3)
        self.assertIsNone(split.get_scene(9))

    def test_unstructured_prose(self):
        split = split_chapter("Just a wall of prose.\n\nNo markers anywhere.")
        self.assertTrue(split.unstructured)
        self.assertEqual(split.scenes, [])
        self.assertIn("wall of prose", split.header)

    def test_empty_text(self):
        for text in ("", "   \n\n  "):
            split = split_chapter(text)
            self.assertFalse(split.unstructured)
            self.assertEqual(split.scenes, [])

    def test_marker_requires_own_line(self):
        # A mid-sentence mention must not split the chapter.
        text = "## Chapter 1: T\n\n### Scene 1\n\nShe said '### Scene 5' was her favorite heading style."
        split = split_chapter(text)
        self.assertEqual(len(split.scenes), 1)


class SceneProseEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import (
            ProjectKnowledgeBase, Chapter, Scene, Character, StoryArc, ArcMilestone,
        )

        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F", num_chapters=3)
        ch1 = Chapter(chapter_number=1, title="One", summary="Real.")
        ch1.scenes.append(Scene(scene_number=1, summary="A scene."))
        ch1.scenes.append(Scene(scene_number=2, summary=""))
        kb.add_chapter(ch1)
        kb.add_chapter(Chapter(chapter_number=2, title="Two", summary=""))
        kb.add_character(Character(name="Maren", role="protagonist",
                                   personality_traits="wary", motivations="survive"))
        kb.add_story_arc(StoryArc(
            name="Drift", milestones=[ArcMilestone(name="Wake", target_chapter=1)]))
        project_service.save_kb("demo", kb)
        (pdir / "chapter_1.md").write_text(STRUCTURED.replace("Chapter 2", "Chapter 1"),
                                           encoding="utf-8")
        (pdir / "chapter_2.md").write_text("No markers here at all.", encoding="utf-8")
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_list_scene_prose(self):
        data = self.client.get("/api/projects/demo/chapters/1/scene-prose").json()
        self.assertTrue(data["exists"])
        self.assertFalse(data["unstructured"])
        self.assertEqual([s["scene_number"] for s in data["scenes"]], [1, 2])
        self.assertTrue(all(s["has_prose"] for s in data["scenes"]))

    def test_list_unstructured_and_missing(self):
        data = self.client.get("/api/projects/demo/chapters/2/scene-prose").json()
        self.assertTrue(data["exists"])
        self.assertTrue(data["unstructured"])
        data = self.client.get("/api/projects/demo/chapters/3/scene-prose").json()
        self.assertFalse(data["exists"])

    def test_get_single_scene(self):
        r = self.client.get("/api/projects/demo/chapters/1/scene-prose/2")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["text"], "The corridor hummed.")
        self.assertEqual(
            self.client.get("/api/projects/demo/chapters/1/scene-prose/9").status_code, 404)
        # Unstructured chapter → 409 (edit at chapter level), not a silent empty answer.
        self.assertEqual(
            self.client.get("/api/projects/demo/chapters/2/scene-prose/1").status_code, 409)

    def test_workbench_tree(self):
        data = self.client.get("/api/projects/demo/workbench-tree").json()
        chapters = {c["chapter_number"]: c for c in data["chapters"]}
        self.assertEqual(sorted(chapters), [1, 2, 3])
        ch1 = chapters[1]
        self.assertTrue(ch1["has_file"])
        self.assertTrue(ch1["summary_set"])
        self.assertEqual(
            [(s["scene_number"], s["summary_set"], s["has_prose"]) for s in ch1["scenes"]],
            [(1, True, True), (2, False, True)])
        self.assertTrue(chapters[2]["unstructured"])
        self.assertFalse(chapters[3]["has_file"])       # planned but nonexistent chapter
        self.assertEqual(chapters[3]["scenes"], [])
        self.assertEqual(data["characters"][0]["name"], "Maren")
        self.assertFalse(data["characters"][0]["has_voice"])
        self.assertGreaterEqual(data["characters"][0]["fields_set"], 3)
        self.assertEqual(data["arcs"][0]["milestones"][0]["name"], "Wake")
        self.assertIn("stage_statuses", data)

    def test_update_chapter_meta_upserts(self):
        r = self.client.put("/api/projects/demo/chapters/1/meta", json={"summary": "New sum."})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["summary"], "New sum.")
        self.assertEqual(r.json()["title"], "One")           # untouched field survives
        # Planned-but-empty chapter 3: meta edit creates the KB entry.
        r = self.client.put("/api/projects/demo/chapters/3/meta",
                            json={"title": "Three", "summary": "S3."})
        self.assertEqual(r.status_code, 200)
        tree = self.client.get("/api/projects/demo/workbench-tree").json()
        ch3 = next(c for c in tree["chapters"] if c["chapter_number"] == 3)
        self.assertEqual(ch3["title"], "Three")
        self.assertTrue(ch3["summary_set"])

    def test_workbench_tree_missing_project(self):
        self.assertEqual(self.client.get("/api/projects/nope/workbench-tree").status_code, 404)


if __name__ == "__main__":
    unittest.main()
