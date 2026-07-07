"""Phase 6 — B36 gated prose-register (off by default, gated enable) + B37 DOCX export."""
import os
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase
from libriscribe.utils import style_register
from libriscribe.services import exporter


class _S:
    def __init__(self, enabled):
        self.prose_register_enabled = enabled


class RegisterTests(unittest.TestCase):
    def test_levels_defined_and_bounded(self):
        for lvl in (1, 2, 3, 4, 5):
            self.assertTrue(style_register.register_directive(lvl))
        for bad in (0, 6, None, "x"):
            self.assertEqual(style_register.register_directive(bad), "")

    def test_inactive_unless_globally_enabled_AND_project_set(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        # Disabled globally -> nothing, even with a project level.
        kb.prose_register = 5
        self.assertEqual(style_register.active_register_directive(kb, _S(False)), "")
        # Enabled globally but project off -> nothing.
        kb.prose_register = None
        self.assertEqual(style_register.active_register_directive(kb, _S(True)), "")
        # Both -> directive.
        kb.prose_register = 3
        self.assertIn("PROSE REGISTER 3", style_register.active_register_directive(kb, _S(True)))


class AdvancedGateTests(unittest.TestCase):
    def setUp(self):
        self._prev_env = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev_env is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev_env

    def test_enable_requires_both_acknowledgments(self):
        r = self.client.post("/api/settings/advanced", json={"enable": True, "confirm_age": True})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/settings/advanced", json={"enable": True, "accept_terms": True})
        self.assertEqual(r.status_code, 400)

    def test_get_exposes_disclaimer(self):
        r = self.client.get("/api/settings/advanced")
        self.assertEqual(r.status_code, 200)
        self.assertIn("solely responsible", r.json()["disclaimer"])


class DocxExportTests(unittest.TestCase):
    def test_build_docx_contains_title_and_chapters(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text("# Chapter 1: The Keep\n\nMaren crept inside.\n\nIt was cold.", encoding="utf-8")
            (pdir / "chapter_2.md").write_text("More prose here.", encoding="utf-8")
            kb = ProjectKnowledgeBase(project_name="t", title="My Book", genre="F", logline="A tale.")
            data = exporter.build_docx(kb, pdir)
        self.assertIsNotNone(data)
        with zipfile.ZipFile(BytesIO(data)) as z:
            names = set(z.namelist())
            self.assertIn("word/document.xml", names)
            self.assertIn("[Content_Types].xml", names)
            doc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("My Book", doc)
        self.assertIn("Chapter 1: The Keep", doc)
        self.assertIn("Maren crept inside.", doc)
        self.assertIn("More prose here.", doc)

    def test_prefers_revised_and_escapes_xml(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text("old & busted", encoding="utf-8")
            (pdir / "chapter_1_revised.md").write_text("new & <shiny>", encoding="utf-8")
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
            data = exporter.build_docx(kb, pdir)
        with zipfile.ZipFile(BytesIO(data)) as z:
            doc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("new &amp; &lt;shiny&gt;", doc)
        self.assertNotIn("old", doc)

    def test_no_chapters_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
            self.assertIsNone(exporter.build_docx(kb, Path(td)))


if __name__ == "__main__":
    unittest.main()
