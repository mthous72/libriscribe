"""Regression: deleting lorebook entities whose names contain special characters.

The frontend now URL-encodes entity names in the path; this confirms the backend decodes them
and deletes correctly (previously a space / unicode em-dash produced a malformed path that 404'd,
and the UI swallowed the error so 'Delete' silently did nothing)."""
import os
import tempfile
import unittest
import urllib.parse

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app


class LorebookDeleteTests(unittest.TestCase):
    def setUp(self):
        self._prev_dir = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Character
        self.project_service = project_service
        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.add_character(Character(name="Maren"))            # simple
        kb.add_character(Character(name="Maren Vance"))       # space
        kb.add_character(Character(name="CEE — UNIT C-774"))  # unicode em-dash + hyphens
        project_service.save_kb("demo", kb)
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev_dir is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev_dir

    def _delete(self, char_name: str) -> int:
        return self.client.delete(
            f"/api/projects/demo/characters/{urllib.parse.quote(char_name)}"
        ).status_code

    def test_delete_simple_spaced_and_unicode_names(self):
        self.assertEqual(self._delete("Maren"), 204)
        self.assertEqual(self._delete("Maren Vance"), 204)
        self.assertEqual(self._delete("CEE — UNIT C-774"), 204)
        remaining = [c["name"] for c in self.client.get("/api/projects/demo/characters").json()]
        self.assertEqual(remaining, [])

    def test_delete_missing_returns_404(self):
        self.assertEqual(self._delete("Nobody"), 404)


if __name__ == "__main__":
    unittest.main()
