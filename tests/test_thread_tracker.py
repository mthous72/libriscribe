"""Tests for F2: Thread Tracker."""

import unittest

from libriscribe.knowledge_base import (
    NarrativeThread,
    ProjectKnowledgeBase,
)


class TestNarrativeThread(unittest.TestCase):
    """Tests for the NarrativeThread model and KB integration."""

    def test_narrative_thread_model(self):
        t = NarrativeThread(
            name="Lost Sword",
            thread_type="item",
            description="The hero's sword was left in the cave.",
            opened_chapter=3,
            characters_involved=["Hero"],
        )
        self.assertEqual(t.name, "Lost Sword")
        self.assertEqual(t.thread_type, "item")
        self.assertEqual(t.status, "open")
        self.assertEqual(t.opened_chapter, 3)
        self.assertIsNone(t.resolved_chapter)

    def test_pkb_add_and_get_thread(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        thread = NarrativeThread(
            name="Mystery Letter",
            thread_type="question",
            description="Who sent the letter?",
            opened_chapter=1,
        )
        pkb.add_narrative_thread(thread)
        self.assertIn("Mystery Letter", pkb.narrative_threads)
        retrieved = pkb.get_narrative_thread("Mystery Letter")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.thread_type, "question")

    def test_thread_resolve(self):
        t = NarrativeThread(name="Promise", thread_type="promise", status="open")
        t.status = "resolved"
        t.resolved_chapter = 7
        self.assertEqual(t.status, "resolved")
        self.assertEqual(t.resolved_chapter, 7)

    def test_pkb_thread_serialization(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        pkb.add_narrative_thread(NarrativeThread(
            name="Thread1",
            thread_type="setup",
            opened_chapter=2,
            characters_involved=["Alice", "Bob"],
        ))
        json_str = pkb.to_json()
        restored = ProjectKnowledgeBase.from_json(json_str)
        self.assertIn("Thread1", restored.narrative_threads)
        t = restored.narrative_threads["Thread1"]
        self.assertEqual(t.thread_type, "setup")
        self.assertEqual(t.characters_involved, ["Alice", "Bob"])

    def test_backward_compat_no_threads(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        self.assertEqual(pkb.narrative_threads, {})


if __name__ == "__main__":
    unittest.main()
