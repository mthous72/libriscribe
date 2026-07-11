"""B45 Slice 5: downstream-impact scan (prose + outline references, no LLM)."""
import os
import tempfile
import unittest


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene

        self.pdir = project_service.get_projects_dir() / "demo"
        self.pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F", num_chapters=3)
        ch2 = Chapter(chapter_number=2, title="Two", summary="x")
        ch2.scenes.append(Scene(scene_number=1, summary="Maren breaks in.", characters=["Maren"]))
        ch2.scenes.append(Scene(scene_number=2, summary="Quiet.", setting="The Helix core"))
        kb.add_chapter(ch2)
        project_service.save_kb("demo", kb)
        (self.pdir / "chapter_1.md").write_text(
            "Maren waited. Maren watched. The Helix core pulsed.", encoding="utf-8")
        (self.pdir / "chapter_3.md").write_text("Nobody here.", encoding="utf-8")
        self.kb = project_service.load_kb("demo")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_counts_prose_mentions_and_scene_fields(self):
        from libriscribe.services.impact import entity_impact

        r = entity_impact(self.kb, self.pdir, "Maren")
        self.assertEqual(r["chapters"], [{"chapter": 1, "mentions": 2}])
        self.assertEqual(r["scenes"], [{"chapter": 2, "scene": 1, "fields": ["characters", "summary"]}])
        self.assertEqual(r["total_mentions"], 2)

    def test_word_boundary_no_partial_hits(self):
        from libriscribe.services.impact import entity_impact
        # 'Mare' must not match inside 'Maren'.
        r = entity_impact(self.kb, self.pdir, "Mare")
        self.assertEqual(r["chapters"], [])

    def test_absent_entity_and_setting_match(self):
        from libriscribe.services.impact import entity_impact

        self.assertEqual(entity_impact(self.kb, self.pdir, "Nobody Known")["scenes"], [])
        r = entity_impact(self.kb, self.pdir, "The Helix core")
        self.assertEqual(r["chapters"][0]["mentions"], 1)
        self.assertIn({"chapter": 2, "scene": 2, "fields": ["setting"]}, r["scenes"])


if __name__ == "__main__":
    unittest.main()
