"""Tests for project export/import, story .txt assembly, and version snapshots."""
import os
import tempfile
import unittest
from unittest import mock


class ImportExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"PROJECTS_DIR": self.tmp.name}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def _make_project(self, name="mybook"):
        from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Chapter
        from libriscribe.services.project_service import save_kb, get_projects_dir

        (get_projects_dir() / name).mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name=name, title="My Book", genre="Fantasy")
        kb.characters["Tya"] = Character(name="Tya", role="rogue")
        kb.chapters[1] = Chapter(chapter_number=1, title="Beginnings")
        save_kb(name, kb)
        (get_projects_dir() / name / "chapter_1.md").write_text(
            "# Chapter\n\nOnce upon a **time** there was [Tya](x).", encoding="utf-8"
        )
        return name

    def test_export_bundle_has_kb_and_prose(self):
        from libriscribe.services.project_service import export_project_bundle

        name = self._make_project()
        bundle = export_project_bundle(name)
        self.assertEqual(bundle["app"], "libriscribe")
        self.assertEqual(bundle["project_data"]["project_name"], name)
        self.assertIn("chapter_1.md", bundle["files"])
        self.assertIn("Tya", bundle["project_data"]["characters"])

    def test_export_missing_project_returns_none(self):
        from libriscribe.services.project_service import export_project_bundle

        self.assertIsNone(export_project_bundle("does_not_exist"))

    def test_import_roundtrip_autorenames_on_collision(self):
        from libriscribe.services.project_service import (
            export_project_bundle, import_project_bundle, get_projects_dir,
        )

        name = self._make_project()
        bundle = export_project_bundle(name)
        result = import_project_bundle(bundle)  # name already exists -> rename
        self.assertTrue(result["renamed"])
        self.assertEqual(result["project_name"], f"{name}-2")
        new_dir = get_projects_dir() / f"{name}-2"
        self.assertTrue((new_dir / "project_data.json").exists())
        self.assertTrue((new_dir / "chapter_1.md").exists())

    def test_import_rejects_non_bundle(self):
        from libriscribe.services.project_service import import_project_bundle

        with self.assertRaises(ValueError):
            import_project_bundle({"not": "a bundle"})

    def test_story_export_strips_markdown_and_orders(self):
        from libriscribe.services.project_service import export_story_text

        name = self._make_project()
        text = export_story_text(name)
        self.assertIn("My Book", text)
        self.assertIn("Chapter 1: Beginnings", text)
        self.assertIn("Once upon a time", text)  # ** stripped
        self.assertIn("Tya", text)               # link text kept
        self.assertNotIn("**", text)
        self.assertNotIn("](", text)             # link target removed

    def test_versions_save_list_and_reversible_restore(self):
        from libriscribe.services.project_service import (
            save_project_version, list_project_versions, restore_project_version,
            load_kb, save_kb,
        )

        name = self._make_project()
        v1 = save_project_version(name, label="baseline")
        self.assertEqual(v1["version"], 1)
        self.assertEqual(v1["label"], "baseline")
        self.assertEqual(v1["summary"]["characters"], 1)

        kb = load_kb(name)
        kb.title = "Changed Title"
        save_kb(name, kb)
        v2 = save_project_version(name)
        self.assertEqual(v2["version"], 2)

        restore_project_version(name, 1)  # roll back to baseline
        self.assertEqual(load_kb(name).title, "My Book")

        versions = list_project_versions(name)
        # v1, v2, plus the auto "before restore" snapshot -> reversible
        self.assertGreaterEqual(len(versions), 3)
        self.assertEqual(versions[0]["version"], max(e["version"] for e in versions))

    def test_restore_unknown_version_raises(self):
        from libriscribe.services.project_service import restore_project_version

        name = self._make_project()
        with self.assertRaises(ValueError):
            restore_project_version(name, 99)


if __name__ == "__main__":
    unittest.main()
