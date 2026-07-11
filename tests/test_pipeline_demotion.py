"""B45 Slice 6: characters/worldbuilding left the default pipeline.

STAGE_ORDER drops them, next_step skips them (covered in test_workflow_state), the generate
endpoint refuses them with a pointer to the opt-in tools, and unknown tools 400.
"""
import os
import tempfile
import unittest


class PipelineDemotionTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase

        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        project_service.save_kb("demo", ProjectKnowledgeBase(
            project_name="demo", title="T", genre="F", num_chapters=2))
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_stage_order_dropped_demoted_stages(self):
        from libriscribe.services.generation_service import STAGE_ORDER, TOOL_STAGES
        self.assertEqual(STAGE_ORDER, ["concept", "outline", "chapters", "formatting"])
        self.assertEqual(set(TOOL_STAGES), {"characters", "worldbuilding"})

    def test_generate_refuses_demoted_stages_with_pointer(self):
        for stage in ("characters", "worldbuilding"):
            r = self.client.post("/api/projects/demo/generate",
                                 json={"start_from_stage": stage})
            self.assertEqual(r.status_code, 400)
            self.assertIn(f"/tools/{stage}", r.json()["detail"])

    def test_unknown_tool_400(self):
        r = self.client.post("/api/projects/demo/tools/plumbing")
        self.assertEqual(r.status_code, 400)
        self.assertIn("characters", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
