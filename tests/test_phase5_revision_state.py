"""Phase 5 — B34 revision (no silent save), B33 character-state/timeline, B31 knows-too-early hook."""
import json
import tempfile
import unittest
from pathlib import Path

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, CharacterState
from libriscribe.services import revision, char_state


class RevisionTests(unittest.TestCase):
    class _Client:
        def __init__(self):
            self.prompt = None
        def generate_content(self, prompt, **kw):
            self.prompt = prompt
            self.system_prompt = kw.get("system_prompt")
            return "Revised chapter prose."

    def test_revise_returns_pair_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            pdir = Path(td)
            (pdir / "chapter_1.md").write_text("Original prose.", encoding="utf-8")
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F",
                                      canon_rules=["Past tense throughout."])
            c = self._Client()
            out = revision.revise_chapter(c, kb, pdir, 1, "tighten the middle")
            self.assertEqual(out, {"original": "Original prose.", "revised": "Revised chapter prose."})
            # File untouched — keeping is the author's explicit action.
            self.assertEqual((pdir / "chapter_1.md").read_text(encoding="utf-8"), "Original prose.")
            # Guidance + canon bind the rewrite.
            self.assertIn("tighten the middle", c.prompt)
            self.assertIn("CANON RULES", c.prompt)

    def test_missing_chapter_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
            self.assertIsNone(revision.revise_chapter(self._Client(), kb, Path(td), 9, "x"))


class CharStateTests(unittest.TestCase):
    class _Client:
        def generate_content_with_json_repair(self, prompt, **kw):
            # Chapter number is in the prompt; answer accordingly.
            n = 1 if "Chapter 1 " in prompt or "CHAPTER 1 " in prompt else 2
            return json.dumps({
                "states": [{"character_name": "Maren", "emotional_state": f"tense{n}",
                            "knowledge": [f"secret {n}"], "location": "the Keep", "physical_state": ""}],
                "events": [{"description": f"Event {n}", "characters_involved": ["Maren"]}],
            })

    def _project(self, td):
        pdir = Path(td)
        (pdir / "chapter_1.md").write_text("Maren sneaks in.", encoding="utf-8")
        (pdir / "chapter_2.md").write_text("Maren learns more.", encoding="utf-8")
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        kb.add_character(Character(name="Maren"))
        return pdir, kb

    def test_states_and_timeline_populated_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            pdir, kb = self._project(td)
            summary = char_state.track_states(self._Client(), kb, pdir, max_workers=2)
            self.assertEqual(summary["chapters_scanned"], 2)
            states = kb.character_states["Maren"]
            self.assertEqual([s.chapter_number for s in states], [1, 2])
            self.assertEqual(states[0].knowledge, ["secret 1"])
            self.assertEqual([e.chapter_number for e in kb.timeline_events], [1, 2])

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            pdir, kb = self._project(td)
            char_state.track_states(self._Client(), kb, pdir, max_workers=1)
            char_state.track_states(self._Client(), kb, pdir, max_workers=1)
            self.assertEqual(len(kb.character_states["Maren"]), 2)   # not duplicated
            self.assertEqual(len(kb.timeline_events), 2)

    def test_knowledge_timeline_block_feeds_b31(self):
        kb = ProjectKnowledgeBase(project_name="t", title="T", genre="F")
        kb.character_states["Maren"] = [CharacterState(
            character_name="Maren", chapter_number=3, knowledge=["Tya betrayed her"])]
        block = char_state.knowledge_timeline_block(kb)
        self.assertIn("Ch 3: Maren learns: Tya betrayed her", block)
        self.assertIn("knows_too_early", block)
        # Empty when no states.
        self.assertEqual(char_state.knowledge_timeline_block(
            ProjectKnowledgeBase(project_name="t", title="T", genre="F")), "")


if __name__ == "__main__":
    unittest.main()
