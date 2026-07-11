"""B40 — deterministic repetition guard: detector, recap, and prompt wiring."""
import tempfile
import unittest
from pathlib import Path

from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene
from libriscribe.utils.repetition_guard import (
    overused_phrases,
    scene_openings,
    repetition_guard_block,
    repetition_report_block,
)
from libriscribe.utils.prose_steering import scene_recap_block


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0] if self.responses else ""


TICKY_PROSE = (
    "His heart hammered against his ribs. He pulled his hand back as if burned. "
    "The lamp flickered over the bench.\n\n"
    "Maren stared at Sector Six. His heart hammered against his ribs again. "
    "She pulled her hand back as if burned. Maren walked through Sector Six slowly. "
    "He looked at Sector Six one more time."
)


class DetectorTests(unittest.TestCase):
    def test_finds_repeated_tics(self):
        phrases = overused_phrases(TICKY_PROSE)
        self.assertTrue(any("hammered against his ribs" in p for p in phrases))
        self.assertTrue(any("back as if burned" in p for p in phrases))

    def test_names_never_banned(self):
        phrases = overused_phrases(TICKY_PROSE)
        for p in phrases:
            self.assertNotIn("sector six", p)

    def test_subphrases_deduped(self):
        phrases = overused_phrases(TICKY_PROSE)
        for i, a in enumerate(phrases):
            for b in phrases[i + 1:]:
                self.assertNotIn(a, b)
                self.assertNotIn(b, a)

    def test_no_repeats_still_constrains_opening_but_bans_nothing(self):
        block = repetition_guard_block("A single quiet sentence.")
        self.assertNotIn("BANNED", block)
        self.assertIn('"A single quiet sentence."', block)  # opening constraint remains
        self.assertEqual(repetition_guard_block(""), "")
        self.assertEqual(repetition_report_block("A single quiet sentence."), "")

    def test_scene_markers_never_analyzed(self):
        text = "### Scene 1\n\nProse here.\n\n### Scene 2\n\nMore prose here.\n\n### Scene 3\n\nEven more prose."
        for p in overused_phrases(text):
            self.assertNotIn("scene", p)

    def test_openings_skip_headings(self):
        text = (
            "## Chapter 1: T\n\n### Scene 1\n\nThe smell of ozone hit first. More.\n\n"
            "### Scene 2\n\nRain fell on the vents. More."
        )
        self.assertEqual(
            scene_openings(text),
            ["The smell of ozone hit first.", "Rain fell on the vents."],
        )

    def test_block_contains_bans_and_openings(self):
        text = "### Scene 1\n\n" + TICKY_PROSE
        block = repetition_guard_block(text)
        self.assertIn("REPETITION GUARD", block)
        self.assertIn("BANNED", block)
        self.assertIn("must open DIFFERENTLY", block)


class SceneRecapTests(unittest.TestCase):
    def test_recap_lists_beats_openings_endings(self):
        entries = [
            ("Chapter 1, Scene 1", "Maren finds the synth.", "The scrap heap loomed. He dug. He carried her home."),
            ("Scene 1", "Maren scans her.", "The workshop hummed. The scan came back blank."),
        ]
        block = scene_recap_block(entries)
        self.assertIn("Chapter 1, Scene 1: Maren finds the synth.", block)
        self.assertIn('opened with: "The scrap heap loomed."', block)
        self.assertIn('ended with: "He carried her home."', block)
        self.assertIn("Scene 1: Maren scans her.", block)
        self.assertIn("must\nmove the story FORWARD".replace("\n", " "), block.replace("\n", " "))

    def test_empty_entries_no_block(self):
        self.assertEqual(scene_recap_block([]), "")
        self.assertEqual(scene_recap_block(None), "")


class WriterIntegrationTests(unittest.TestCase):
    def _project(self, td):
        pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
        pkb.project_dir = Path(td)
        ch1 = Chapter(chapter_number=1, title="One")
        ch1.scenes.append(Scene(scene_number=1, summary="Maren finds the synth."))
        ch1.scenes.append(Scene(scene_number=2, summary="Maren hides her at the workshop."))
        pkb.add_chapter(ch1)
        return pkb

    FRESH_PROSE = "Rain hissed on the vents while she counted the patrol drones."

    def test_scene2_prompt_carries_recap_guard_and_continuity(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        with tempfile.TemporaryDirectory() as td:
            pkb = self._project(td)
            # scene 2 must return FRESH prose or the enforcement retry fires (by design)
            fake = FakeLLM([TICKY_PROSE, self.FRESH_PROSE])
            ChapterWriterAgent(llm_client=fake).execute(pkb, 1)

        self.assertEqual(len(fake.prompts), 2)
        p2 = fake.prompts[1]
        self.assertIn("EVERY SCENE ALREADY WRITTEN", p2)
        self.assertIn("Scene 1: Maren finds the synth.", p2)
        self.assertIn("THE STORY SO FAR", p2)              # continuity tail
        self.assertIn("REPETITION GUARD", p2)              # ban list from scene 1's tics
        self.assertIn("back as if burned", p2)

    def test_streaming_path_now_carries_full_stack(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        with tempfile.TemporaryDirectory() as td:
            pkb = self._project(td)
            # no generate_content_streaming -> falls back; scene 2 fresh so no retry fires
            fake = FakeLLM([TICKY_PROSE, self.FRESH_PROSE])
            ChapterWriterAgent(llm_client=fake).execute_streaming(pkb, 1)

        self.assertEqual(len(fake.prompts), 2)
        p2 = fake.prompts[1]
        self.assertIn("THE STORY SO FAR", p2)
        self.assertIn("EVERY SCENE ALREADY WRITTEN", p2)
        self.assertIn("REPETITION GUARD", p2)

    def test_chapter2_recap_covers_chapter1_scenes(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        with tempfile.TemporaryDirectory() as td:
            pkb = self._project(td)
            (Path(td) / "chapter_1.md").write_text(
                "## Chapter 1: One\n\n### Scene 1\n\nThe scrap heap loomed. He dug her out.\n\n"
                "### Scene 2\n\nThe workshop hummed. The scan came back blank.",
                encoding="utf-8",
            )
            ch2 = Chapter(chapter_number=2, title="Two")
            ch2.scenes.append(Scene(scene_number=1, summary="A patrol sweeps the sector."))
            pkb.add_chapter(ch2)

            fake = FakeLLM(["Fresh prose."])
            ChapterWriterAgent(llm_client=fake).execute(pkb, 2)

        p1 = fake.prompts[0]
        self.assertIn("Chapter 1, Scene 1: Maren finds the synth.", p1)
        self.assertIn("Chapter 1, Scene 2: Maren hides her at the workshop.", p1)
        self.assertIn('opened with: "The scrap heap loomed."', p1)


class GuardV2Tests(unittest.TestCase):
    def test_staggered_fragments_merge_into_one_phrase(self):
        text = (
            "He pushed aside a heavy sheet of corrugated plastic and stared.\n\n"
            "She pushed aside a heavy sheet of corrugated plastic and sighed."
        )
        phrases = overused_phrases(text)
        joined = [p for p in phrases if "aside a heavy sheet of corrugated plastic" in p]
        self.assertTrue(joined, phrases)
        for p in phrases:
            for q in phrases:
                if p != q:
                    self.assertNotIn(p, q)

    def test_overused_words_detects_and_excludes_names(self):
        from libriscribe.utils.repetition_guard import overused_words
        text = ("Her skin glowed. His skin burned. The skin felt wrong. Skin on skin. "
                "Bare skin shone. " * 3 + "Maren Maren Maren Maren Maren Maren Maren.")
        words = overused_words(text, min_count=5)
        self.assertIn("skin", words)
        self.assertNotIn("maren", words)

    def test_find_violations_flags_reuse_and_openings(self):
        from libriscribe.utils.repetition_guard import find_violations
        prior = "### Scene 1\n\n" + TICKY_PROSE
        bad_scene = (
            "His heart hammered against his ribs. He pulled his hand back as if burned. New stuff."
        )
        violations = find_violations(bad_scene, prior)
        self.assertTrue(any("hammered against his ribs" in v for v in violations))
        fresh_scene = "Rain hissed on the vents while she counted the patrol drones."
        self.assertEqual(find_violations(fresh_scene, prior), [])

    def test_enforce_freshness_retries_once_and_keeps_fresher(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        prior = "### Scene 1\n\n" + TICKY_PROSE
        stale = ("His heart hammered against his ribs. He pulled his hand back as if burned. "
                 "The lamp flickered over the bench again.")
        fresh = "Rain hissed on the vents while she counted the patrol drones."
        fake = FakeLLM([fresh])
        agent = ChapterWriterAgent(llm_client=fake)
        out = agent._enforce_freshness(
            stale, Scene(scene_number=2, summary="Next beat."), "PROMPT", None, prior, 2000)
        self.assertEqual(out, fresh)
        self.assertEqual(len(fake.prompts), 1)
        self.assertIn("REJECTED", fake.prompts[0])
        self.assertIn("hammered against his ribs", fake.prompts[0])

    def test_enforce_freshness_keeps_original_when_clean(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        prior = "### Scene 1\n\n" + TICKY_PROSE
        fresh = "Rain hissed on the vents while she counted the patrol drones."
        fake = FakeLLM(["should never be called"])
        agent = ChapterWriterAgent(llm_client=fake)
        out = agent._enforce_freshness(
            fresh, Scene(scene_number=2, summary="Next beat."), "PROMPT", None, prior, 2000)
        self.assertEqual(out, fresh)
        self.assertEqual(len(fake.prompts), 0)

    def test_guard_block_includes_word_section(self):
        text = ("Her skin glowed. His skin burned. The skin felt wrong. Skin on skin met. "
                "Bare skin shone brightly. Warm skin pressed close. ") * 2
        block = repetition_guard_block(text)
        self.assertIn("Use each AT MOST ONCE", block)
        self.assertIn("skin", block)


class EditorReportTests(unittest.TestCase):
    def test_report_block_framing(self):
        report = repetition_report_block(TICKY_PROSE)
        self.assertIn("OVERUSED PHRASES", report)
        self.assertIn("back as if burned", report)


if __name__ == "__main__":
    unittest.main()
