"""Tests for F4: Scene Pacing Controls."""

import unittest

from libriscribe.knowledge_base import Scene, ProjectKnowledgeBase, Chapter
from libriscribe.agents.chapter_writer import PACING_INSTRUCTIONS


class TestScenePacing(unittest.TestCase):
    """Tests for scene pacing controls."""

    def test_scene_type_field(self):
        scene = Scene(scene_number=1, scene_type="action")
        self.assertEqual(scene.scene_type, "action")

    def test_scene_target_word_count(self):
        scene = Scene(scene_number=1, target_word_count=500)
        self.assertEqual(scene.target_word_count, 500)

    def test_scene_defaults(self):
        scene = Scene(scene_number=1)
        self.assertEqual(scene.scene_type, "")
        self.assertIsNone(scene.target_word_count)

    def test_pacing_instructions_dict(self):
        self.assertIn("action", PACING_INSTRUCTIONS)
        self.assertIn("dialogue", PACING_INSTRUCTIONS)
        self.assertIn("introspective", PACING_INSTRUCTIONS)
        self.assertIn("exposition", PACING_INSTRUCTIONS)
        self.assertIn("transition", PACING_INSTRUCTIONS)

    def test_scene_serialization(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        ch = Chapter(chapter_number=1, title="Test Chapter")
        ch.scenes.append(Scene(
            scene_number=1,
            summary="Action scene",
            scene_type="action",
            target_word_count=800,
        ))
        pkb.add_chapter(ch)
        json_str = pkb.to_json()
        restored = ProjectKnowledgeBase.from_json(json_str)
        scene = restored.chapters[1].scenes[0]
        self.assertEqual(scene.scene_type, "action")
        self.assertEqual(scene.target_word_count, 800)

    def test_backward_compat_no_scene_type(self):
        """Old scenes without scene_type should load fine."""
        scene = Scene(scene_number=1, summary="Old scene")
        self.assertEqual(scene.scene_type, "")
        self.assertIsNone(scene.target_word_count)


if __name__ == "__main__":
    unittest.main()
