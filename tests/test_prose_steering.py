"""Prose-quality fixes: scene continuity (anti-repetition), steering in polish passes,
and the style pass no longer truncating chapters."""
import os
import tempfile
import unittest
from pathlib import Path

from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene
from libriscribe.utils import prose_steering


class ContinuityBlockTests(unittest.TestCase):
    def test_empty_prior_yields_empty(self):
        self.assertEqual(prose_steering.continuity_block(""), "")

    def test_tail_and_rules(self):
        prior = "word " * 2000 + "the final distinctive phrase"
        b = prose_steering.continuity_block(prior, max_words=50)
        self.assertIn("the final distinctive phrase", b)
        self.assertNotIn("word " * 100, b)                 # truncated to the tail
        self.assertIn("CONTINUITY RULES", b)
        self.assertIn("Do NOT reuse distinctive imagery", b)


class _CaptureClient:
    def __init__(self):
        self.prompts = []
        self.kwargs = []
        self.n = 0
    def generate_content(self, prompt, **kw):
        self.prompts.append(prompt)
        self.kwargs.append(kw)
        self.n += 1
        # Distinct prose per scene — near-identical outputs would (correctly) trip the
        # B40 freshness enforcement and add a retry call.
        openings = {
            1: "Unique scene prose number 1 with the emberlight motif.",
            2: "A cold wind scoured the parapet while the sentries changed.",
        }
        return openings.get(self.n, f"Entirely different passage number {self.n} in the cellars.")


class SceneContinuityTests(unittest.TestCase):
    def _kb(self, tmp):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        kb.project_dir = Path(tmp)
        ch = Chapter(chapter_number=1, title="One", scenes=[
            Scene(scene_number=1, summary="Arrival", characters=["A"], setting="Keep"),
            Scene(scene_number=2, summary="Confrontation", characters=["A"], setting="Keep"),
        ])
        kb.add_chapter(ch)
        return kb

    def test_second_scene_sees_first_scene_prose(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent
        with tempfile.TemporaryDirectory() as tmp:
            kb = self._kb(tmp)
            client = _CaptureClient()
            agent = ChapterWriterAgent(client)
            agent.execute(kb, 1, output_path=str(Path(tmp) / "chapter_1.md"))
            self.assertEqual(len(client.prompts), 2)
            self.assertNotIn("CONTINUITY RULES", client.prompts[0])   # nothing before scene 1 / ch 1
            self.assertIn("CONTINUITY RULES", client.prompts[1])
            self.assertIn("Unique scene prose number 1", client.prompts[1])  # sees scene 1's text

    def test_chapter_two_sees_previous_chapter_tail(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent
        with tempfile.TemporaryDirectory() as tmp:
            kb = self._kb(tmp)
            kb.add_chapter(Chapter(chapter_number=2, title="Two", scenes=[
                Scene(scene_number=1, summary="Aftermath", characters=["A"], setting="Keep")]))
            (Path(tmp) / "chapter_1.md").write_text(
                "Chapter one prose ending with the ashfall settling.", encoding="utf-8")
            client = _CaptureClient()
            ChapterWriterAgent(client).execute(kb, 2, output_path=str(Path(tmp) / "chapter_2.md"))
            self.assertIn("THE STORY SO FAR", client.prompts[0])
            self.assertIn("ashfall settling", client.prompts[0])


class PolishSteeringTests(unittest.TestCase):
    def setUp(self):
        os.environ["PROSE_REGISTER_ENABLED"] = "true"

    def tearDown(self):
        os.environ.pop("PROSE_REGISTER_ENABLED", None)

    def test_style_pass_carries_register_canon_system_prompt_and_budget(self):
        from libriscribe.agents.style_editor import StyleEditorAgent
        with tempfile.TemporaryDirectory() as tmp:
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F",
                                      canon_rules=["Past tense throughout."], prose_register=4)
            kb.project_dir = Path(tmp)
            (Path(tmp) / "chapter_1.md").write_text("Original chapter prose.", encoding="utf-8")
            client = _CaptureClient()
            StyleEditorAgent(client).execute(kb, 1)
            p = client.prompts[0]
            self.assertIn("PROSE REGISTER 4", p)             # register survives the polish pass
            self.assertIn("CANON RULES", p)
            self.assertIn("PRESERVE THE REGISTER", p)         # explicit no-toning-down instruction
            self.assertIsNotNone(client.kwargs[0].get("system_prompt"))
            self.assertEqual(client.kwargs[0].get("max_tokens"), 8000)   # was 3000 -> truncated chapters

    def test_steering_blocks_empty_when_nothing_set(self):
        os.environ.pop("PROSE_REGISTER_ENABLED", None)
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        self.assertEqual(prose_steering.steering_blocks(kb), "")


if __name__ == "__main__":
    unittest.main()
