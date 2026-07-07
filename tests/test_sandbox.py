"""B27 Slice A — sandbox staging: per-run store, cherry-pick, apply-accepted-only, gap seed."""
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
from libriscribe.knowledge_base import ProjectKnowledgeBase, Character


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service, sandbox
        self.svc = project_service
        self.sandbox = sandbox
        (project_service.get_projects_dir() / "demo").mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F")
        kb.add_character(Character(name="Maren", role="lead"))
        project_service.save_kb("demo", kb)
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def _run_with(self, candidates):
        return self.sandbox.create_run("demo", {"kind": "manual"}, candidates)

    def test_candidates_start_pending_never_auto_accepted(self):
        c = self.sandbox.new_candidate("characters", "Tya", {"role": "broker"})
        self.assertEqual(c["status"], "pending")

    def test_apply_merges_only_accepted(self):
        run = self._run_with([
            self.sandbox.new_candidate("characters", "Tya", {"role": "broker"}),
            self.sandbox.new_candidate("characters", "Ghost", {"role": "villain"}),
            self.sandbox.new_candidate("locations", "Keep", {"description": "stone"}),
        ])
        ids = {c["name"]: c["id"] for c in run["candidates"]}
        self.sandbox.update_candidate("demo", run["id"], ids["Tya"], status="accepted")
        self.sandbox.update_candidate("demo", run["id"], ids["Ghost"], status="rejected")
        # "Keep" stays pending.
        kb = self.svc.load_kb("demo")
        result = self.sandbox.apply_accepted("demo", kb, run["id"])
        self.svc.save_kb("demo", kb)

        self.assertEqual(result["applied"], 1)
        kb = self.svc.load_kb("demo")
        self.assertIn("Tya", kb.characters)          # accepted → merged
        self.assertNotIn("Ghost", kb.characters)      # rejected → not merged
        self.assertNotIn("Keep", kb.locations)        # pending → not merged
        self.assertEqual(self.sandbox.get_run("demo", run["id"])["status"], "applied")

    def test_update_existing_entity_merges_by_name(self):
        run = self._run_with([self.sandbox.new_candidate("characters", "Maren", {"motivations": "freedom"}, op="update")])
        cid = run["candidates"][0]["id"]
        self.sandbox.update_candidate("demo", run["id"], cid, status="accepted")
        kb = self.svc.load_kb("demo")
        self.sandbox.apply_accepted("demo", kb, run["id"])
        self.svc.save_kb("demo", kb)
        kb = self.svc.load_kb("demo")
        self.assertEqual(kb.characters["Maren"].motivations, "freedom")
        self.assertEqual(kb.characters["Maren"].role, "lead")   # untouched field preserved

    def test_stage_gaps_maps_types_and_evidence(self):
        gaps = [
            {"entity_name": "the Ashfall", "entity_type": "lore", "type": "undefined_entity",
             "message": "Mentioned 4x", "evidence": "in: Chapter 1", "target": None},
            {"entity_name": "Maren", "entity_type": "character", "type": "thin_character",
             "message": "Missing motivations", "evidence": "", "target": {"type": "character", "name": "Maren"}},
        ]
        run = self.sandbox.stage_gaps("demo", gaps)
        by_name = {c["name"]: c for c in run["candidates"]}
        self.assertEqual(by_name["the Ashfall"]["category"], "lore")
        self.assertEqual(by_name["the Ashfall"]["op"], "new")        # no target → create
        self.assertEqual(by_name["Maren"]["op"], "update")            # has target → update
        self.assertIn("Chapter 1", by_name["the Ashfall"]["evidence"])
        self.assertTrue(all(c["status"] == "pending" for c in run["candidates"]))

    def test_endpoints_roundtrip(self):
        r = self.client.post("/api/projects/demo/gaps/to-sandbox", json={"gaps": [
            {"entity_name": "Tya", "entity_type": "character", "type": "undefined_entity",
             "message": "m", "evidence": "e", "target": None}]})
        self.assertEqual(r.status_code, 200)
        run_id = r.json()["id"]
        runs = self.client.get("/api/projects/demo/sandbox").json()
        self.assertTrue(any(x["id"] == run_id for x in runs))
        cid = self.client.get(f"/api/projects/demo/sandbox/{run_id}").json()["candidates"][0]["id"]
        p = self.client.patch(f"/api/projects/demo/sandbox/{run_id}/candidates/{cid}", json={"status": "accepted"})
        self.assertEqual(p.json()["status"], "accepted")
        a = self.client.post(f"/api/projects/demo/sandbox/{run_id}/apply")
        self.assertEqual(a.json()["applied"], 1)
        self.assertIn("Tya", self.svc.load_kb("demo").characters)
        d = self.client.delete(f"/api/projects/demo/sandbox/{run_id}")
        self.assertEqual(d.status_code, 204)


if __name__ == "__main__":
    unittest.main()
