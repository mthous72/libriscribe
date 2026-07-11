"""B45 Slice 4: real milestones — AI-verified, human-approved, always reversible.

The old numeric auto-complete (milestone flips because a chapter number matched) is gone;
these tests pin the replacement: proposals with evidence (substring trust guard), explicit
accept/reject, manual status flips, and index-addressed CRUD.
"""
import json
import os
import tempfile
import unittest

PROSE = """## Chapter 4: The Catalyst

### Scene 1

Tya pressed her palm to the conduit and the crude words spilled out of her, displacing
every technical term she had ever memorized. The vocabulary was gone; only hunger remained.
"""


class _FakeVerifier:
    """Returns a canned JSON verdict array."""

    def __init__(self, verdicts):
        self.verdicts = verdicts
        self.prompts = []

    def generate_content_with_json_repair(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return json.dumps(self.verdicts)


class MilestoneVerifierTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import ProjectKnowledgeBase, StoryArc, ArcMilestone

        self.pdir = project_service.get_projects_dir() / "demo"
        self.pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="Helix", genre="SF", num_chapters=5)
        kb.add_story_arc(StoryArc(name="Drift", milestones=[
            ArcMilestone(name="Semantic Colonization", milestone_type="escalation",
                         target_chapter=4, description="Crude language displaces technical vocabulary."),
            ArcMilestone(name="Elsewhere", target_chapter=2),
        ]))
        project_service.save_kb("demo", kb)
        (self.pdir / "chapter_4.md").write_text(PROSE, encoding="utf-8")
        self.kb = project_service.load_kb("demo")

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_delivered_with_real_evidence_proposes_completed(self):
        from libriscribe.services import milestone_verifier

        fake = _FakeVerifier([{"id": 0, "delivered": True,
                               "evidence": "displacing every technical term",
                               "reasoning": "The beat lands."}])
        results = milestone_verifier.verify_chapter(fake, self.kb, self.pdir, 4)
        self.assertEqual(len(results), 1)                       # only ch-4 milestones graded
        m = self.kb.story_arcs["Drift"].milestones[0]
        self.assertEqual(m.proposal.proposed_status, "completed")
        self.assertEqual(m.proposal.chapter, 4)
        self.assertEqual(m.status, "pending")                    # AI never touches status
        other = self.kb.story_arcs["Drift"].milestones[1]
        self.assertIsNone(other.proposal)                        # untargeted milestone untouched

    def test_fabricated_evidence_downgrades_to_uncertain(self):
        from libriscribe.services import milestone_verifier

        fake = _FakeVerifier([{"id": 0, "delivered": True,
                               "evidence": "a quote that appears nowhere in the chapter text",
                               "reasoning": "Sure."}])
        milestone_verifier.verify_chapter(fake, self.kb, self.pdir, 4)
        m = self.kb.story_arcs["Drift"].milestones[0]
        self.assertEqual(m.proposal.proposed_status, "uncertain")
        self.assertIn("not an actual quote", m.proposal.reasoning)

    def test_not_delivered_proposes_not_completed(self):
        from libriscribe.services import milestone_verifier

        fake = _FakeVerifier([{"id": 0, "delivered": False, "evidence": "",
                               "reasoning": "Only set up, never lands."}])
        milestone_verifier.verify_chapter(fake, self.kb, self.pdir, 4)
        self.assertEqual(self.kb.story_arcs["Drift"].milestones[0].proposal.proposed_status,
                         "not_completed")

    def test_missing_prose_raises(self):
        from libriscribe.services import milestone_verifier
        self.kb.story_arcs["Drift"].milestones[1].target_chapter = 2
        with self.assertRaises(ValueError):
            milestone_verifier.verify_chapter(_FakeVerifier([]), self.kb, self.pdir, 2)

    def test_writer_no_longer_fakes_completion(self):
        # The old auto-complete is deleted outright.
        from libriscribe.agents.project_manager import ProjectManagerAgent
        self.assertFalse(hasattr(ProjectManagerAgent, "_update_arc_milestones"))


class MilestoneEndpointTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        from libriscribe.services import project_service
        from libriscribe.knowledge_base import (
            ProjectKnowledgeBase, StoryArc, ArcMilestone, MilestoneProposal,
        )

        pdir = project_service.get_projects_dir() / "demo"
        pdir.mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name="demo", title="T", genre="F", num_chapters=5)
        kb.add_story_arc(StoryArc(name="Drift", milestones=[
            ArcMilestone(name="Wake", target_chapter=1, status="completed", actual_chapter=1),
            ArcMilestone(name="Turn", target_chapter=4,
                         proposal=MilestoneProposal(proposed_status="completed", chapter=4,
                                                    evidence="q", reasoning="r")),
            ArcMilestone(name="Fall", target_chapter=5,
                         proposal=MilestoneProposal(proposed_status="not_completed", chapter=5)),
        ]))
        project_service.save_kb("demo", kb)
        self.client = TestClient(create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def _milestones(self):
        return self.client.get("/api/projects/demo/arcs/Drift").json()["milestones"]

    def test_manual_flip_anytime(self):
        # Unflag a previously-faked "completed" milestone.
        r = self.client.put("/api/projects/demo/arcs/Drift/milestones/0",
                            json={"status": "pending", "actual_chapter": None})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._milestones()[0]["status"], "pending")
        # …and reflag it.
        self.client.put("/api/projects/demo/arcs/Drift/milestones/0", json={"status": "completed"})
        self.assertEqual(self._milestones()[0]["status"], "completed")

    def test_accept_completed_proposal(self):
        r = self.client.post("/api/projects/demo/arcs/Drift/milestones/1/proposal",
                             json={"action": "accept"})
        self.assertEqual(r.status_code, 200)
        m = self._milestones()[1]
        self.assertEqual(m["status"], "completed")
        self.assertEqual(m["actual_chapter"], 4)
        self.assertIsNone(m["proposal"])

    def test_accept_not_completed_reopens(self):
        self.client.put("/api/projects/demo/arcs/Drift/milestones/2",
                        json={"status": "completed", "actual_chapter": 5})
        self.client.post("/api/projects/demo/arcs/Drift/milestones/2/proposal",
                         json={"action": "accept"})
        m = self._milestones()[2]
        self.assertEqual(m["status"], "pending")
        self.assertIsNone(m["actual_chapter"])

    def test_reject_clears_proposal_only(self):
        self.client.post("/api/projects/demo/arcs/Drift/milestones/1/proposal",
                         json={"action": "reject"})
        m = self._milestones()[1]
        self.assertEqual(m["status"], "pending")
        self.assertIsNone(m["proposal"])

    def test_add_and_delete_milestone(self):
        r = self.client.post("/api/projects/demo/arcs/Drift/milestones",
                             json={"name": "Coda", "target_chapter": 5})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self._milestones()), 4)
        self.assertEqual(
            self.client.delete("/api/projects/demo/arcs/Drift/milestones/3").status_code, 204)
        self.assertEqual(len(self._milestones()), 3)

    def test_verify_without_targets_422(self):
        r = self.client.post("/api/projects/demo/milestones/verify", json={"chapter": 3})
        self.assertEqual(r.status_code, 422)

    def test_arc_crud_still_works_after_route_reorder(self):
        # The greedy {arc_name:path} routes must not swallow milestone sub-routes — and
        # vice versa: plain arc GET/PUT must still resolve.
        self.assertEqual(self.client.get("/api/projects/demo/arcs/Drift").status_code, 200)
        arc = self.client.get("/api/projects/demo/arcs/Drift").json()
        arc["description"] = "updated"
        self.assertEqual(
            self.client.put("/api/projects/demo/arcs/Drift", json=arc).status_code, 200)


if __name__ == "__main__":
    unittest.main()
