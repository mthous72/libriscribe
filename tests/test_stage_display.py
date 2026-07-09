"""Stage cards must light from ACTUAL data completion, not only generation-run status files."""
import tempfile
import unittest
from pathlib import Path

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Worldbuilding
from libriscribe.workflow_state import inspect_project_progress


class StageDisplayTests(unittest.TestCase):
    def test_complete_data_lights_cards_without_status_file(self):
        # Imported / wizard-built / hand-edited project: full data, NO project_status.json.
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F",
                                      logline="Real logline", outline="An outline",
                                      num_chapters=1, num_characters=1, worldbuilding_needed=True)
            kb.add_character(Character(name="Maren"))
            kb.worldbuilding = Worldbuilding(geography="Ash plains")
            (pdir / "chapter_1.md").write_text("prose", encoding="utf-8")
            (pdir / "manuscript.md").write_text("book", encoding="utf-8")

            st = inspect_project_progress(pdir, kb).stage_statuses
            for stage in ("concept", "outline", "characters", "worldbuilding", "chapters", "formatting"):
                self.assertEqual(st.get(stage), "complete", stage)

    def test_incomplete_project_stays_dark_and_optional_stages_skip(self):
        with tempfile.TemporaryDirectory() as td:
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F",
                                      num_chapters=2, num_characters=0, worldbuilding_needed=False)
            st = inspect_project_progress(Path(td), kb).stage_statuses
            self.assertNotIn("concept", st)                      # nothing to light
            self.assertEqual(st.get("characters"), "skipped")     # not required, no data
            self.assertEqual(st.get("worldbuilding"), "skipped")
            self.assertNotIn("chapters", st)                      # chapters missing -> dark

    def test_partial_chapters_show_in_progress(self):
        # 1 of 3 chapters written -> the card lights as in-progress, not dark.
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text("prose", encoding="utf-8")
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", num_chapters=3)
            st = inspect_project_progress(pdir, kb).stage_statuses
            self.assertEqual(st.get("chapters"), "in_progress")

    def test_data_wins_over_stale_pending_status(self):
        # e.g. after an old reset marked stages pending but content was later imported.
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "project_status.json").write_text(
                '{"stages": {"outline": {"status": "pending"}}}', encoding="utf-8")
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", outline="Full outline")
            st = inspect_project_progress(pdir, kb).stage_statuses
            self.assertEqual(st.get("outline"), "complete")


if __name__ == "__main__":
    unittest.main()
