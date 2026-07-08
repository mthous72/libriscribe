"""Per-project AI task lock + deep-scan persistence — one heavy LLM task at a time; no lost scans."""
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase
from libriscribe.services import task_lock, gap_finder


class TaskLockTests(unittest.TestCase):
    def tearDown(self):
        task_lock.release("p1")
        task_lock.release("p2")

    def test_acquire_release_cycle(self):
        self.assertTrue(task_lock.acquire("p1", "Deep scan"))
        self.assertEqual(task_lock.current("p1"), "Deep scan")
        self.assertFalse(task_lock.acquire("p1", "Story wizard"))   # busy
        self.assertEqual(task_lock.current("p1"), "Deep scan")      # holder unchanged
        task_lock.release("p1")
        self.assertIsNone(task_lock.current("p1"))
        self.assertTrue(task_lock.acquire("p1", "Story wizard"))

    def test_projects_are_independent(self):
        self.assertTrue(task_lock.acquire("p1", "Deep scan"))
        self.assertTrue(task_lock.acquire("p2", "Generation"))      # other project unaffected

    def test_busy_detail_names_the_task(self):
        task_lock.acquire("p1", "Deep scan")
        self.assertIn("Deep scan", task_lock.busy_detail("p1"))


class EndpointGuardTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)
        project_service.save_kb("demo", ProjectKnowledgeBase(project_name="demo", title="T", genre="F"))
        self.client = TestClient(create_app())

    def tearDown(self):
        task_lock.release("demo")
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_deep_scan_409_while_another_task_runs(self):
        task_lock.acquire("demo", "Story wizard")
        r = self.client.post("/api/projects/demo/gaps/deep-scan")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Story wizard", r.json()["detail"])

    def test_generation_409_while_batch_task_runs(self):
        task_lock.acquire("demo", "Deep scan")
        r = self.client.post("/api/projects/demo/generate", json={})
        self.assertEqual(r.status_code, 409)
        self.assertIn("Deep scan", r.json()["detail"])

    def test_revise_409_while_locked(self):
        task_lock.acquire("demo", "Generation")
        r = self.client.post("/api/projects/demo/chapters/1/revise", json={"guidance": "x"})
        self.assertEqual(r.status_code, 409)


class DeepScanPersistenceTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            result = {"gaps": [{"entity_name": "the Ashfall", "type": "undefined_entity"}],
                      "scanned": 3, "truncated": False}
            gap_finder.save_deep_scan(td, result)
            loaded = gap_finder.load_deep_scan(td)
            self.assertEqual(loaded["gaps"][0]["entity_name"], "the Ashfall")
            self.assertEqual(loaded["scanned"], 3)
            self.assertTrue(loaded["scanned_at"])   # timestamp stamped

    def test_load_empty_when_never_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            loaded = gap_finder.load_deep_scan(td)
            self.assertEqual(loaded["gaps"], [])
            self.assertIsNone(loaded["scanned_at"])

    def test_last_scan_endpoint(self):
        prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        try:
            from libriscribe.services import project_service
            pdir = project_service.get_projects_dir() / "demo"
            pdir.mkdir(parents=True, exist_ok=True)
            project_service.save_kb("demo", ProjectKnowledgeBase(project_name="demo", title="T", genre="F"))
            gap_finder.save_deep_scan(pdir, {"gaps": [{"entity_name": "X"}], "scanned": 1, "truncated": False})
            client = TestClient(create_app())
            r = client.get("/api/projects/demo/gaps/deep-scan/last")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["gaps"][0]["entity_name"], "X")
        finally:
            if prev is None:
                os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
            else:
                os.environ["LIBRISCRIBE_PROJECTS_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
