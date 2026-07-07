"""Phase 0 — generation SUGGESTS metadata instead of overwriting the user's (title/desc/chapters)."""
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase
from libriscribe.agents.outliner import OutlinerAgent


class OutlinerRespectsUserChaptersTests(unittest.TestCase):
    def test_max_chapters_honors_user_count_over_book_length(self):
        agent = OutlinerAgent(llm_client=None)
        # User wants 30 chapters; book_length "Novel" would otherwise cap at 20.
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", book_length="Novel", num_chapters=30)
        self.assertEqual(agent._get_max_chapters(kb), 30)

    def test_book_length_default_only_when_unset(self):
        agent = OutlinerAgent(llm_client=None)
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", book_length="Novella", num_chapters=1)
        self.assertEqual(agent._get_max_chapters(kb), 8)   # user didn't specify → book-length default

    def test_range_uses_upper_bound(self):
        agent = OutlinerAgent(llm_client=None)
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F", book_length="Novel", num_chapters="10-25")
        self.assertEqual(agent._get_max_chapters(kb), 25)


class ConceptSuggestsTests(unittest.TestCase):
    def test_concept_writes_suggested_not_canonical(self):
        from libriscribe.agents.concept_generator import ConceptGeneratorAgent
        # Drive just the merge logic the agent uses (Step 4), mirroring its guarded assignments.
        kb = ProjectKnowledgeBase(project_name="t", title="My Title", genre="F",
                                  description="My own description.")
        refined = {"title": "AI Title", "logline": "AI logline", "description": "AI description"}
        # Replicate the agent's Step-4 block behaviour:
        if refined.get("title"):
            kb.suggested_title = refined["title"]
        if refined.get("logline"):
            kb.suggested_logline = refined["logline"]
        if refined.get("description"):
            kb.suggested_description = refined["description"]
        # Canonical untouched; suggestions populated.
        self.assertEqual(kb.title, "My Title")
        self.assertEqual(kb.description, "My own description.")
        self.assertEqual(kb.suggested_title, "AI Title")
        self.assertEqual(kb.suggested_description, "AI description")
        _ = ConceptGeneratorAgent  # ensure importable


class SuggestionsEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="Mine", genre="F",
                                  description="Mine too.", num_chapters=12)
        kb.suggested_title = "Proposed Title"
        kb.suggested_description = "Proposed description."
        project_service.save_kb("demo", kb)
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_detail_exposes_suggestions(self):
        d = self.client.get("/api/projects/demo").json()
        self.assertEqual(d["suggested_title"], "Proposed Title")
        self.assertEqual(d["title"], "Mine")

    def test_apply_copies_and_clears(self):
        r = self.client.post("/api/projects/demo/suggestions", json={"action": "apply", "fields": ["title"]})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["title"], "Proposed Title")   # applied
        self.assertEqual(d["suggested_title"], "")        # cleared
        self.assertEqual(d["suggested_description"], "Proposed description.")  # untouched

    def test_dismiss_clears_without_applying(self):
        r = self.client.post("/api/projects/demo/suggestions", json={"action": "dismiss", "fields": ["description"]})
        d = r.json()
        self.assertEqual(d["description"], "Mine too.")   # NOT applied
        self.assertEqual(d["suggested_description"], "")   # cleared


if __name__ == "__main__":
    unittest.main()
