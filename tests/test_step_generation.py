"""Phase 1 (B30) — step-by-step generation: mode resolution, concept-progress fix, reset."""
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Chapter, Worldbuilding
from libriscribe.services.generation_service import GenerationService
from libriscribe.workflow_state import has_concept_data, inspect_project_progress


class EffectiveModeTests(unittest.TestCase):
    def _kb(self, mode=None):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        if mode is not None:
            kb.generation_mode = mode
        return kb

    def test_default_is_step(self):
        self.assertEqual(GenerationService._effective_mode(self._kb()), "step")

    def test_kb_auto_respected(self):
        self.assertEqual(GenerationService._effective_mode(self._kb("auto")), "auto")

    def test_request_override_wins(self):
        self.assertEqual(GenerationService._effective_mode(self._kb("step"), "auto"), "auto")
        self.assertEqual(GenerationService._effective_mode(self._kb("auto"), "step"), "step")

    def test_bogus_falls_back_to_step(self):
        self.assertEqual(GenerationService._effective_mode(self._kb("bogus")), "step")


class TargetChapterTests(unittest.TestCase):
    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)

    def _pm(self, existing=(1, 2, 3)):
        class PM:
            def __init__(self):
                self.written = []
            def does_chapter_exist(self, n):
                return n in existing
            def write_and_review_chapter(self, n, streaming=False):
                self.written.append(n)
        return PM()

    def test_target_chapter_writes_exactly_that_one_even_if_it_exists(self):
        from libriscribe.services.generation_service import GenerationService
        svc = GenerationService(job_manager=None)
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", num_chapters=5)
        pm = self._pm(existing=(1, 2, 3))
        self._run(svc._run_chapters(pm, kb, False, None, one_chapter=True, target_chapter=2))
        self.assertEqual(pm.written, [2])   # explicit pick: regenerates an existing chapter

    def test_no_target_still_writes_next_missing(self):
        from libriscribe.services.generation_service import GenerationService
        svc = GenerationService(job_manager=None)
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", num_chapters=5)
        pm = self._pm(existing=(1, 2))
        self._run(svc._run_chapters(pm, kb, False, None, one_chapter=True))
        self.assertEqual(pm.written, [3])   # lowest missing


class ConceptProgressWithSuggestionsTests(unittest.TestCase):
    def test_pending_suggestion_counts_as_concept_ran(self):
        # Phase 0a: concept suggests instead of overwriting; the stage must still register
        # complete or step mode would re-run it forever.
        kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="F")
        self.assertFalse(has_concept_data(kb))
        kb.suggested_logline = "A proposed logline."
        self.assertTrue(has_concept_data(kb))

    def test_applied_logline_still_counts(self):
        kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="F", logline="Real logline")
        self.assertTrue(has_concept_data(kb))


class ResetToStageTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        self.pdir = project_service.get_projects_dir() / "demo"
        self.pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="Mine", genre="F",
                                  logline="Real logline", outline="An outline", num_chapters=3)
        kb.add_character(Character(name="Maren"))
        kb.add_chapter(Chapter(chapter_number=1, title="One"))
        kb.worldbuilding = Worldbuilding(geography="Ash plains")
        project_service.save_kb("demo", kb)
        (self.pdir / "outline.md").write_text("outline", encoding="utf-8")
        (self.pdir / "chapter_1.md").write_text("prose", encoding="utf-8")
        (self.pdir / "manuscript.md").write_text("book", encoding="utf-8")
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_reset_to_outline_clears_generation_artifacts_never_lorebook(self):
        result = self.svc.reset_to_stage("demo", "outline")
        self.assertEqual(result["reset_to"], "outline")
        self.assertIn("chapters", result["stages_reset"])
        self.assertTrue(result["snapshot"]["version"] >= 1)   # snapshot saved first

        kb = self.svc.load_kb("demo")
        self.assertEqual(kb.logline, "Real logline")           # concept untouched
        self.assertEqual(kb.outline, "")                        # outline cleared
        self.assertEqual(kb.chapters, {})
        # THE LOREBOOK IS NEVER TOUCHED (regression: an early reset cascade wiped user characters).
        self.assertIn("Maren", kb.characters)
        self.assertIsNotNone(kb.worldbuilding)
        self.assertFalse((self.pdir / "outline.md").exists())
        self.assertFalse((self.pdir / "chapter_1.md").exists())
        self.assertFalse((self.pdir / "manuscript.md").exists())
        # Progress re-gates at outline.
        progress = inspect_project_progress(self.pdir, kb)
        self.assertEqual(progress.next_step, "outline")

    def test_reset_refuses_lore_stages(self):
        for stage in ("characters", "worldbuilding"):
            with self.assertRaises(ValueError):
                self.svc.reset_to_stage("demo", stage)
        r = self.client.post("/api/projects/demo/generate/reset", json={"to_stage": "characters"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("lorebook", r.json()["detail"].lower())

    def test_reset_endpoint(self):
        r = self.client.post("/api/projects/demo/generate/reset", json={"to_stage": "chapters"})
        self.assertEqual(r.status_code, 200)
        kb = self.svc.load_kb("demo")
        self.assertEqual(kb.outline, "An outline")             # upstream kept
        self.assertFalse((self.pdir / "chapter_1.md").exists())

    def test_reset_unknown_stage_400(self):
        r = self.client.post("/api/projects/demo/generate/reset", json={"to_stage": "bogus"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
