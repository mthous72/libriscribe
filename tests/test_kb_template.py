"""Drift guard: examples/project_data.template.json must match the current models.

When ProjectKnowledgeBase (or any nested model) changes, regenerate the template:

    PYTHONPATH=src python scripts/generate_kb_template.py

This test fails until you do — keeping the committed reference honest.
"""
import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "examples" / "project_data.template.json"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_kb_template", REPO / "scripts" / "generate_kb_template.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class KbTemplateTests(unittest.TestCase):
    def test_template_exists_and_matches_models(self):
        self.assertTrue(TEMPLATE.exists(), "template missing — run scripts/generate_kb_template.py")
        gen = _load_generator()
        expected = gen.template_dict()
        actual = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(
            actual, expected,
            "examples/project_data.template.json is stale — the KB models changed. "
            "Regenerate: PYTHONPATH=src python scripts/generate_kb_template.py",
        )

    def test_template_covers_every_kb_field(self):
        from libriscribe.knowledge_base import ProjectKnowledgeBase
        data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        model_fields = set(ProjectKnowledgeBase.model_fields) - {"project_dir"}
        missing = model_fields - set(data)
        self.assertFalse(missing, f"template missing KB fields: {sorted(missing)}")

    def test_template_loads_as_valid_kb(self):
        import tempfile
        from libriscribe.knowledge_base import ProjectKnowledgeBase
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(TEMPLATE.read_text(encoding="utf-8"))
            path = f.name
        kb = ProjectKnowledgeBase.load_from_file(path)
        self.assertIsNotNone(kb)
        self.assertIn("Example Character", kb.characters)
        self.assertTrue(kb.canon_rules)


if __name__ == "__main__":
    unittest.main()
