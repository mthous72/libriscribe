"""Tests for F1: Arc Milestones."""

import unittest

from libriscribe.knowledge_base import (
    ArcMilestone,
    ProjectKnowledgeBase,
    StoryArc,
)


class TestArcMilestones(unittest.TestCase):
    """Tests for the arc milestone models and KB integration."""

    def test_arc_milestone_model(self):
        m = ArcMilestone(
            name="Discovery",
            milestone_type="inciting_incident",
            target_chapter=1,
            description="Hero finds the artifact.",
        )
        self.assertEqual(m.name, "Discovery")
        self.assertEqual(m.milestone_type, "inciting_incident")
        self.assertEqual(m.target_chapter, 1)
        self.assertEqual(m.status, "pending")
        self.assertIsNone(m.actual_chapter)

    def test_story_arc_with_milestones(self):
        arc = StoryArc(
            name="Hero's Journey",
            description="The main quest arc",
            arc_type="main",
            milestones=[
                ArcMilestone(name="Call", milestone_type="inciting_incident", target_chapter=1),
                ArcMilestone(name="Climax", milestone_type="climax", target_chapter=8),
            ],
        )
        self.assertEqual(len(arc.milestones), 2)
        self.assertEqual(arc.milestones[0].name, "Call")
        self.assertEqual(arc.milestones[1].milestone_type, "climax")

    def test_story_arc_backward_compat_no_milestones(self):
        arc = StoryArc(name="Simple Arc", description="No milestones")
        self.assertEqual(arc.milestones, [])

    def test_pkb_story_arc_serialization(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        arc = StoryArc(
            name="Main Arc",
            milestones=[
                ArcMilestone(name="Inciting", milestone_type="inciting_incident", target_chapter=2),
            ],
        )
        pkb.add_story_arc(arc)
        json_str = pkb.to_json()
        restored = ProjectKnowledgeBase.from_json(json_str)
        self.assertIn("Main Arc", restored.story_arcs)
        self.assertEqual(len(restored.story_arcs["Main Arc"].milestones), 1)
        self.assertEqual(
            restored.story_arcs["Main Arc"].milestones[0].name, "Inciting"
        )

    def test_milestone_status_update(self):
        m = ArcMilestone(name="Battle", milestone_type="climax", target_chapter=5)
        self.assertEqual(m.status, "pending")
        m.status = "completed"
        m.actual_chapter = 5
        self.assertEqual(m.status, "completed")
        self.assertEqual(m.actual_chapter, 5)


if __name__ == "__main__":
    unittest.main()
