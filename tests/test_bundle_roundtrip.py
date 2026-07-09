"""Export/import bundle round-trip — versions, sessions, status, and lore must all survive."""
import json
import os
import tempfile
import unittest

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Worldbuilding


class BundleRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        self.svc = project_service
        self.pdir = project_service.get_projects_dir() / "orig"
        self.pdir.mkdir(parents=True, exist_ok=True)

        kb = ProjectKnowledgeBase(project_name="orig", title="Mine", genre="F",
                                  logline="A real logline", canon_rules=["Past tense."])
        kb.add_character(Character(name="Maren", motivations="freedom"))
        kb.worldbuilding = Worldbuilding(geography="Ash plains")
        project_service.save_kb("orig", kb)
        (self.pdir / "chapter_1.md").write_text("Chapter prose.", encoding="utf-8")
        (self.pdir / "project_status.json").write_text(
            json.dumps({"stages": {"concept": {"status": "complete"}}}), encoding="utf-8")
        (self.pdir / "chat_sessions").mkdir()
        (self.pdir / "chat_sessions" / "abc123.json").write_text(
            json.dumps({"id": "abc123", "title": "Plot", "messages": []}), encoding="utf-8")
        # A version snapshot (created through the real path so the index exists too).
        project_service.save_project_version("orig", label="checkpoint")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_full_roundtrip(self):
        bundle = self.svc.export_project_bundle("orig")
        self.assertEqual(bundle["schema_version"], 2)
        # Subdir payload present in the export.
        self.assertTrue(any(k.startswith("versions/") for k in bundle["subdirs"]))
        self.assertIn("chat_sessions/abc123.json", bundle["subdirs"])
        self.assertIn("project_status.json", bundle["extras"])

        result = self.svc.import_project_bundle(bundle, target_name="copy")
        name = result["project_name"]
        kb = self.svc.load_kb(name)
        # Lore/concept/worldbuilding survive.
        self.assertEqual(kb.logline, "A real logline")
        self.assertIn("Maren", kb.characters)
        self.assertIsNotNone(kb.worldbuilding)
        self.assertEqual(kb.canon_rules, ["Past tense."])
        # Versions survive (the user's report: they didn't import at all).
        self.assertTrue(self.svc.list_project_versions(name))
        # Sessions + stage statuses survive (statuses drove the "concept didn't import" look).
        new_dir = self.svc.get_projects_dir() / name
        self.assertTrue((new_dir / "chat_sessions" / "abc123.json").exists())
        status = json.loads((new_dir / "project_status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["stages"]["concept"]["status"], "complete")
        self.assertEqual((new_dir / "chapter_1.md").read_text(encoding="utf-8"), "Chapter prose.")

    def test_malicious_subdir_paths_rejected(self):
        bundle = self.svc.export_project_bundle("orig")
        bundle["subdirs"]["../evil/escape.json"] = "{}"
        bundle["subdirs"]["versions/../../escape2.json"] = "{}"
        bundle["subdirs"]["unknown_dir/x.json"] = "{}"
        result = self.svc.import_project_bundle(bundle, target_name="safe")
        base = self.svc.get_projects_dir()
        self.assertFalse((base.parent / "evil").exists())
        self.assertFalse((base / "escape2.json").exists())
        self.assertFalse((base / result["project_name"] / "unknown_dir").exists())

    def test_newer_schema_rejected(self):
        bundle = self.svc.export_project_bundle("orig")
        bundle["schema_version"] = 99
        with self.assertRaises(ValueError):
            self.svc.import_project_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
