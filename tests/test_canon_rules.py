"""Phase 2 (B32 canon lock + B31 continuity hook) — inviolable rules bind generation + checks."""
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase, Character
from libriscribe.services import lore_digest


def _kb(rules=None):
    kb = ProjectKnowledgeBase(project_name="t", title="Mine", genre="F")
    if rules:
        kb.canon_rules = rules
    return kb


class CanonBlockTests(unittest.TestCase):
    def test_empty_without_rules(self):
        self.assertEqual(lore_digest.canon_block(_kb()), "")

    def test_block_carries_rules_and_binding_phrasing(self):
        b = lore_digest.canon_block(_kb(["Past tense throughout.", "Maren dies in Ch. 12."]))
        self.assertIn("CANON RULES (INVIOLABLE", b)
        self.assertIn("- Past tense throughout.", b)
        self.assertIn("- Maren dies in Ch. 12.", b)
        self.assertIn("absolute", b)

    def test_blank_rules_filtered(self):
        self.assertEqual(lore_digest.canon_block(_kb(["  ", ""])), "")

    def test_grounding_block_includes_canon_even_without_lore(self):
        # Canon binds from day one, before any lorebook exists.
        b = lore_digest.grounding_block(_kb(["No modern slang."]))
        self.assertIn("CANON RULES", b)
        self.assertNotIn("ESTABLISHED LORE", b)

    def test_grounding_block_canon_precedes_lore(self):
        kb = _kb(["Past tense."])
        kb.add_character(Character(name="Maren", motivations="freedom", character_arc="grows"))
        b = lore_digest.grounding_block(kb)
        self.assertLess(b.index("CANON RULES"), b.index("ESTABLISHED LORE"))


class ContinuityCanonContextTests(unittest.TestCase):
    def test_continuity_context_carries_canon_violation_instruction(self):
        from libriscribe.services.lore_sync import LoreSyncService

        captured = {}

        class _Client:
            def generate_content_with_json_repair(self, prompt, **kw):
                captured["prompt"] = prompt
                return '{"issues": []}'

        with tempfile.TemporaryDirectory() as td:
            from pathlib import Path
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text("She walks in present tense.", encoding="utf-8")
            kb = _kb(["Past tense throughout."])
            svc = LoreSyncService(_Client(), kb, pdir)
            svc.detect_continuity_issues()
        self.assertIn("CANON RULES", captured["prompt"])
        self.assertIn("canon_violation", captured["prompt"])


class CanonEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)
        project_service.save_kb("demo", ProjectKnowledgeBase(project_name="demo", title="T", genre="F"))
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_meta_saves_and_detail_exposes_canon_rules(self):
        r = self.client.put("/api/projects/demo/meta", json={"canon_rules": ["Past tense.", "No slang."]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["canon_rules"], ["Past tense.", "No slang."])
        kb = self.svc.load_kb("demo")
        self.assertEqual(kb.canon_rules, ["Past tense.", "No slang."])


if __name__ == "__main__":
    unittest.main()
