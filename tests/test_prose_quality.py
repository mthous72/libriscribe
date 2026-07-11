"""B39 — first-draft prose quality: sanitizer, de-scaffolding, scene-outline validation.

Fixture strings are the exact artifacts from a real chapter-1 export
("The Helix Chronicles") that motivated the epic.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from libriscribe.utils.prose_sanitizer import (
    fix_mojibake,
    sanitize_prose,
    strip_summary_echo,
)
from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene

HELIX_SUMMARY = (
    "Maren navigates the claustrophobic, neon-drenched slums of the lower sectors, "
    "battling sensory overload and a growing sense of dread."
)


class FakeLLM:
    """Returns queued responses; records every prompt."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_content(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if not self.responses:
            return ""
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


class SanitizerTests(unittest.TestCase):
    def test_mojibake_roundtrip(self):
        orig = "the scrap—the scraping ‘quoted’ “said” café …end"
        moji = orig.encode("utf-8").decode("cp1252", errors="replace")
        self.assertEqual(fix_mojibake(moji), orig)

    def test_lone_a_circumflex_between_words_is_em_dash(self):
        # the draft's "scrapâthe" (em-dash bytes partially stripped in transit)
        self.assertEqual(fix_mojibake("scrapâthe scraping"), "scrap—the scraping")

    def test_double_hyphen_becomes_em_dash(self):
        out = sanitize_prose("designed this way--aggressive, and systems -- began")
        self.assertEqual(out, "designed this way—aggressive, and systems—began")

    def test_markdown_structures_untouched_by_dash_rule(self):
        text = "---\n\n- a list item\n\n### Scene 2\n\nprose--here"
        out = sanitize_prose(text)
        self.assertIn("---", out)
        self.assertIn("- a list item", out)
        self.assertIn("### Scene 2", out)
        self.assertIn("prose—here", out)

    def test_stray_leading_hyphen_stripped_but_lists_kept(self):
        self.assertEqual(sanitize_prose("-No scuffs, no seam lines"), "No scuffs, no seam lines")
        self.assertEqual(sanitize_prose("- a real list item"), "- a real list item")

    def test_caps_possessive(self):
        self.assertEqual(sanitize_prose("CEE'S eyes snapped open"), "CEE's eyes snapped open")

    def test_idempotent(self):
        once = sanitize_prose("a--b\n\n\n\nc  \nCEE'S")
        self.assertEqual(sanitize_prose(once), once)

    def test_empty_and_none_safe(self):
        self.assertEqual(sanitize_prose(""), "")


class SummaryEchoTests(unittest.TestCase):
    def test_drops_truncated_label_and_full_summary_echo(self):
        text = (
            "**Scene 1: Maren navigates the claustroph...**\n\n"
            f"Scene 1: {HELIX_SUMMARY}\n\n"
            "The air in Sector Six tasted like copper."
        )
        out = strip_summary_echo(text, HELIX_SUMMARY)
        self.assertEqual(out, "The air in Sector Six tasted like copper.")

    def test_drops_bare_summary_restatement(self):
        text = f"{HELIX_SUMMARY}\n\nThe air tasted like copper."
        out = strip_summary_echo(text, HELIX_SUMMARY)
        self.assertEqual(out, "The air tasted like copper.")

    def test_keeps_real_prose_opening(self):
        text = "The air in Sector Six tasted like copper and scorched insulation."
        self.assertEqual(strip_summary_echo(text, HELIX_SUMMARY), text)


class ChapterWriterDeScaffoldTests(unittest.TestCase):
    def test_scene_output_is_delimited_and_clean(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        scaffolded = (
            f"**Scene 1: {HELIX_SUMMARY[:30]}...**\n\n"
            f"{HELIX_SUMMARY}\n\n"
            "The air tasted of copper. He owed Helix--everything. -She was blank. CEE'S eyes opened."
        )
        with tempfile.TemporaryDirectory() as td:
            pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
            pkb.project_dir = Path(td)
            ch = Chapter(chapter_number=1, title="The Glitch in the Ledger")
            ch.scenes.append(Scene(scene_number=1, summary=HELIX_SUMMARY))
            pkb.add_chapter(ch)

            agent = ChapterWriterAgent(llm_client=FakeLLM([scaffolded]))
            agent.execute(pkb, 1)

            content = (Path(td) / "chapter_1.md").read_text(encoding="utf-8")

        self.assertIn("## Chapter 1: The Glitch in the Ledger", content)
        self.assertIn("### Scene 1", content)
        self.assertNotIn("**Scene", content)
        self.assertNotIn(HELIX_SUMMARY, content)          # summary echo removed
        self.assertIn("Helix—everything", content)         # dash normalized
        self.assertIn("She was blank", content)
        self.assertNotIn("-She was blank", content)        # stray hyphen removed
        self.assertIn("CEE's eyes", content)

    def test_prompt_no_longer_asks_for_title(self):
        from libriscribe.agents.chapter_writer import ChapterWriterAgent

        with tempfile.TemporaryDirectory() as td:
            pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
            pkb.project_dir = Path(td)
            ch = Chapter(chapter_number=1, title="T")
            ch.scenes.append(Scene(scene_number=1, summary="Something happens."))
            pkb.add_chapter(ch)
            fake = FakeLLM(["Prose."])
            ChapterWriterAgent(llm_client=fake).execute(pkb, 1)

        self.assertTrue(fake.prompts)
        self.assertNotIn("Begin the scene with the title", fake.prompts[0])
        self.assertIn("Never restate, paraphrase", fake.prompts[0])


class StoryExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"PROJECTS_DIR": self.tmp.name}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def test_export_has_single_chapter_header_and_no_scene_markers(self):
        from libriscribe.services.project_service import save_kb, get_projects_dir, export_story_text

        name = "helix"
        (get_projects_dir() / name).mkdir(parents=True, exist_ok=True)
        kb = ProjectKnowledgeBase(project_name=name, title="The Helix Chronicles", genre="SF")
        kb.chapters[1] = Chapter(chapter_number=1, title="The Glitch in the Ledger")
        save_kb(name, kb)
        (get_projects_dir() / name / "chapter_1.md").write_text(
            "## Chapter 1: The Glitch in the Ledger\n\n"
            "### Scene 1\n\n"
            "Prose one about the scrapâthe scraping of metal.\n\n"
            "**Scene 2: While scavenging through a hea...**\n\n"
            "Prose two.",
            encoding="utf-8",
        )

        text = export_story_text(name)
        self.assertEqual(text.count("Chapter 1: The Glitch in the Ledger"), 1)
        self.assertNotIn("Scene", text)
        self.assertNotIn("#", text)
        self.assertIn("scrap—the scraping", text)  # legacy mojibake repaired on export
        self.assertIn("Prose two.", text)


class DocxExportTests(unittest.TestCase):
    def test_scene_markers_never_reach_docx(self):
        import zipfile
        from io import BytesIO
        from libriscribe.services import exporter

        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text(
                "# Chapter 1: The Keep\n\n### Scene 1\n\nMaren crept inside.\n\n"
                "**Scene 2: The vault door...**\n\nIt was cold--freezing.",
                encoding="utf-8",
            )
            kb = ProjectKnowledgeBase(project_name="t", title="My Book", genre="F")
            data = exporter.build_docx(kb, pdir)
        with zipfile.ZipFile(BytesIO(data)) as z:
            doc = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Chapter 1: The Keep", doc)
        self.assertIn("Maren crept inside.", doc)
        self.assertNotIn("Scene 1", doc)
        self.assertNotIn("Scene 2", doc)
        self.assertIn("cold—freezing", doc)


class SceneOutlineValidationTests(unittest.TestCase):
    def _outline(self, scenes):
        blocks = []
        for i, summary in enumerate(scenes, 1):
            blocks.append(
                f"Scene {i}:\n"
                f"    * Summary: {summary}\n"
                f"    * Characters: Maren\n"
                f"    * Setting: Sector Six\n"
                f"    * Goal: advance\n"
                f"    * Emotional Beat: dread\n"
                f"    * Scene Type: action\n"
            )
        return "\n".join(blocks)

    def test_truncated_summary_detection(self):
        from libriscribe.agents.outliner import OutlinerAgent

        self.assertTrue(OutlinerAgent._summary_truncated("Maren realizes that CEE is not..."))
        self.assertTrue(OutlinerAgent._summary_truncated("Maren realizes that CEE is not"))
        self.assertTrue(OutlinerAgent._summary_truncated(""))
        self.assertFalse(OutlinerAgent._summary_truncated("Maren realizes CEE is alive."))

    def test_retry_on_bad_outline_and_invalid_scenes_dropped(self):
        from libriscribe.agents.outliner import OutlinerAgent

        bad = self._outline([
            "Maren finds the synth in the scrap heap.",
            "Maren finds the synth in the scrap heap.",   # duplicate beat
            "Maren realizes that CEE is not...",           # truncated
        ])
        good = self._outline([
            "Maren finds the synth buried in the scrap heap.",
            "Maren smuggles her back to his workshop past a patrol.",
            "The diagnostic scanner finds no ID, and Maren realizes she is factory-blank.",
        ])
        fake = FakeLLM([bad, good])
        agent = OutlinerAgent(llm_client=fake)
        pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
        chapter = Chapter(chapter_number=1, title="T")

        self.assertTrue(agent.generate_scene_outline(pkb, chapter))
        self.assertEqual(len(fake.prompts), 2)
        self.assertIn("do NOT repeat them", fake.prompts[1])
        self.assertEqual(len(chapter.scenes), 3)
        self.assertEqual([s.scene_number for s in chapter.scenes], [1, 2, 3])
        for s in chapter.scenes:
            self.assertFalse(OutlinerAgent._summary_truncated(s.summary))

    def test_good_first_attempt_does_not_retry(self):
        from libriscribe.agents.outliner import OutlinerAgent

        good = self._outline([
            "Maren finds the synth buried in the scrap heap.",
            "Maren smuggles her back to his workshop past a patrol.",
        ])
        fake = FakeLLM([good])
        agent = OutlinerAgent(llm_client=fake)
        pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
        chapter = Chapter(chapter_number=1, title="T")

        self.assertTrue(agent.generate_scene_outline(pkb, chapter))
        self.assertEqual(len(fake.prompts), 1)
        self.assertEqual(len(chapter.scenes), 2)

    def test_outline_prompt_demands_distinct_beats(self):
        from libriscribe.agents.outliner import OutlinerAgent

        fake = FakeLLM([self._outline(["Maren finds the synth in the scrap heap."])])
        agent = OutlinerAgent(llm_client=fake)
        pkb = ProjectKnowledgeBase(project_name="t", title="Helix", genre="SF")
        chapter = Chapter(chapter_number=1, title="T")
        agent.generate_scene_outline(pkb, chapter)
        self.assertIn("DISTINCT story beat", fake.prompts[0])
        self.assertIn("ellipsis", fake.prompts[0])


class EditorMarkerTests(unittest.TestCase):
    def test_extracts_current_and_legacy_markers(self):
        from libriscribe.agents.editor import EditorAgent

        agent = EditorAgent(llm_client=FakeLLM([""]))
        content = (
            "## Chapter 1: T\n\n### Scene 1\n\nprose\n\n"
            "**Scene 2: While scavenging through a hea...**\n\nprose"
        )
        markers = agent.extract_scene_markers(content)
        self.assertEqual(markers, ["### Scene 1", "**Scene 2: While scavenging through a hea...**"])


if __name__ == "__main__":
    unittest.main()
