"""Tests for F0: Writing System Prompt."""

import unittest
from unittest.mock import MagicMock, patch

from libriscribe.utils.system_prompts import CREATIVE_WRITING_SYSTEM_PROMPT
from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene


class TestSystemPrompt(unittest.TestCase):
    """Tests for the system prompt feature."""

    def test_system_prompt_constant_exists(self):
        self.assertIsInstance(CREATIVE_WRITING_SYSTEM_PROMPT, str)
        self.assertIn("ASCII", CREATIVE_WRITING_SYSTEM_PROMPT)
        self.assertIn("delve", CREATIVE_WRITING_SYSTEM_PROMPT.lower())

    def test_pkb_writing_system_prompt_default_empty(self):
        pkb = ProjectKnowledgeBase(project_name="test")
        self.assertEqual(pkb.writing_system_prompt, "")

    def test_pkb_writing_system_prompt_roundtrip(self):
        pkb = ProjectKnowledgeBase(
            project_name="test",
            writing_system_prompt="Custom prompt"
        )
        data = pkb.model_dump()
        self.assertEqual(data["writing_system_prompt"], "Custom prompt")
        restored = ProjectKnowledgeBase(**data)
        self.assertEqual(restored.writing_system_prompt, "Custom prompt")

    def test_chapter_writer_get_system_prompt_default(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent
        mock_client = MagicMock()
        writer = ChapterWriterAgent(mock_client)
        pkb = ProjectKnowledgeBase(project_name="test")
        result = writer._get_system_prompt(pkb)
        self.assertEqual(result, CREATIVE_WRITING_SYSTEM_PROMPT)

    def test_chapter_writer_get_system_prompt_project_override(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent
        mock_client = MagicMock()
        writer = ChapterWriterAgent(mock_client)
        pkb = ProjectKnowledgeBase(
            project_name="test",
            writing_system_prompt="Project custom prompt"
        )
        result = writer._get_system_prompt(pkb)
        self.assertEqual(result, "Project custom prompt")

    def test_no_markdown_artifacts_mentioned(self):
        self.assertIn("Markdown", CREATIVE_WRITING_SYSTEM_PROMPT)
        self.assertIn("straight quotes", CREATIVE_WRITING_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
