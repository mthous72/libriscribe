"""Auto-polish toggle — draft-only mode skips the automatic review/edit/style passes."""
import unittest

from libriscribe.agents.project_manager import ProjectManagerAgent
from libriscribe.knowledge_base import ProjectKnowledgeBase


class AutoPolishTests(unittest.TestCase):
    def _pm(self, auto_polish: bool, review_preference: str = "AI"):
        pm = ProjectManagerAgent()
        pm.project_knowledge_base = ProjectKnowledgeBase(
            project_name="t", title="T", genre="F",
            review_preference=review_preference, auto_polish=auto_polish,
        )
        pm.calls = []
        pm.write_chapter = lambda n, streaming=False: pm.calls.append("write")
        pm.review_content = lambda n: pm.calls.append("review")
        pm.edit_chapter = lambda n: pm.calls.append("edit")
        pm.edit_style = lambda n: pm.calls.append("style")
        return pm

    def test_polish_on_runs_full_chain(self):
        pm = self._pm(auto_polish=True)
        pm.write_and_review_chapter(1)
        self.assertEqual(pm.calls, ["write", "review", "edit", "style"])

    def test_draft_only_writes_and_stops(self):
        pm = self._pm(auto_polish=False)
        pm.write_and_review_chapter(1)
        self.assertEqual(pm.calls, ["write"])   # no review, no edit, no style

    def test_draft_only_beats_human_mode_chain_too(self):
        # Draft-only means draft-only regardless of review_preference (no blocking gate,
        # no style pass) — the step flow is the human gate.
        pm = self._pm(auto_polish=False, review_preference="Human")
        pm.write_and_review_chapter(1)
        self.assertEqual(pm.calls, ["write"])

    def test_default_is_polish_on(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        self.assertTrue(kb.auto_polish)


if __name__ == "__main__":
    unittest.main()
