"""Structural gap-finder (B28) — deterministic invariant checks over a KB."""
import unittest

from libriscribe.knowledge_base import (
    ProjectKnowledgeBase, Character, Location, LoreEntry, StoryArc, ArcMilestone,
    NarrativeThread, VoiceProfile,
)
from libriscribe.services import gap_finder


def _kb(**kw):
    return ProjectKnowledgeBase(project_name="t", title="Book", genre="Fantasy", num_chapters=10, **kw)


def _types(result):
    return [g["type"] for g in result["gaps"]]


class GapFinderTests(unittest.TestCase):
    def test_clean_project_has_no_gaps(self):
        kb = _kb()
        kb.add_character(Character(name="Maren", motivations="freedom", character_arc="grows up",
                                   voice_profile=VoiceProfile(speech_patterns="clipped")))
        result = gap_finder.find_gaps(kb)
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["counts"]["total"], 0)

    def test_dangling_reference_to_unknown_entity(self):
        kb = _kb()
        kb.add_character(Character(name="Maren", motivations="x", character_arc="y",
                                   voice_profile=VoiceProfile(speech_patterns="s"),
                                   relationships={"Ghost Who Doesn't Exist": "old rival"}))
        g = [x for x in gap_finder.find_gaps(kb)["gaps"] if x["type"] == "dangling_reference"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["entity_name"], "Maren")
        self.assertIn("Ghost Who Doesn't Exist", g[0]["message"])
        self.assertEqual(g[0]["target"], {"type": "character", "name": "Maren"})

    def test_known_reference_is_not_flagged(self):
        kb = _kb()
        kb.add_character(Character(name="Maren", motivations="x", character_arc="y",
                                   voice_profile=VoiceProfile(speech_patterns="s"),
                                   relationships={"Tya": "ally"}))
        kb.add_character(Character(name="Tya", motivations="x", character_arc="y",
                                   voice_profile=VoiceProfile(speech_patterns="s")))
        self.assertNotIn("dangling_reference", _types(gap_finder.find_gaps(kb)))

    def test_reference_match_is_case_insensitive(self):
        kb = _kb()
        kb.add_location(Location(name="The Keep", description="d", significance="s",
                                 associated_characters=["maren"]))
        kb.add_character(Character(name="Maren", motivations="x", character_arc="y",
                                   voice_profile=VoiceProfile(speech_patterns="s")))
        self.assertNotIn("dangling_reference", _types(gap_finder.find_gaps(kb)))

    def test_out_of_range_and_negative_chapters(self):
        kb = _kb()  # num_chapters=10
        kb.add_location(Location(name="Keep", description="d", significance="s", first_appearance=99))
        kb.narrative_threads["T"] = NarrativeThread(name="T", opened_chapter=0)
        g = [x for x in gap_finder.find_gaps(kb)["gaps"] if x["type"] == "out_of_range_chapter"]
        self.assertEqual(len(g), 2)  # ch 99 (> ceiling) and ch 0 (< 1)

    def test_in_range_chapter_ok(self):
        kb = _kb()
        kb.add_location(Location(name="Keep", description="d", significance="s", first_appearance=3))
        self.assertNotIn("out_of_range_chapter", _types(gap_finder.find_gaps(kb)))

    def test_unknown_num_chapters_skips_upper_bound(self):
        kb = ProjectKnowledgeBase(project_name="t", title="B", genre="F", num_chapters=0)
        kb.add_location(Location(name="Keep", description="d", significance="s", first_appearance=50))
        # ceiling unknown -> only < 1 is invalid; 50 is allowed.
        self.assertNotIn("out_of_range_chapter", _types(gap_finder.find_gaps(kb)))

    def test_open_thread_and_unresolved_arc_flagged(self):
        kb = _kb()
        kb.narrative_threads["Loose"] = NarrativeThread(name="Loose", opened_chapter=1, status="open")
        kb.story_arcs["Main"] = StoryArc(name="Main", status="active")
        types = _types(gap_finder.find_gaps(kb))
        self.assertIn("unresolved_thread", types)
        self.assertIn("unresolved_arc", types)

    def test_resolved_thread_and_arc_not_flagged(self):
        kb = _kb()
        kb.narrative_threads["Done"] = NarrativeThread(name="Done", opened_chapter=1, resolved_chapter=9)
        kb.story_arcs["Closed"] = StoryArc(name="Closed", status="resolved")
        kb.story_arcs["Noted"] = StoryArc(name="Noted", status="active", resolution_notes="wraps in ch 10")
        types = _types(gap_finder.find_gaps(kb))
        self.assertNotIn("unresolved_thread", types)
        self.assertNotIn("unresolved_arc", types)

    def test_thin_character_missing_motivations_or_arc(self):
        kb = _kb()
        kb.add_character(Character(name="Flat", voice_profile=VoiceProfile(speech_patterns="s")))
        g = [x for x in gap_finder.find_gaps(kb)["gaps"] if x["type"] == "thin_character"]
        self.assertEqual(len(g), 1)
        self.assertIn("motivations", g[0]["message"])
        self.assertIn("character arc", g[0]["message"])

    def test_missing_voice_is_info_level(self):
        kb = _kb()
        kb.add_character(Character(name="Voiceless", motivations="x", character_arc="y"))
        g = [x for x in gap_finder.find_gaps(kb)["gaps"] if x["type"] == "missing_voice"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["severity"], "info")

    def test_warnings_sort_before_info(self):
        kb = _kb()
        kb.story_arcs["Main"] = StoryArc(name="Main", status="active")  # info
        kb.add_character(Character(name="Flat", voice_profile=VoiceProfile(speech_patterns="s")))  # warn (thin)
        sev = [g["severity"] for g in gap_finder.find_gaps(kb)["gaps"]]
        self.assertEqual(sev, sorted(sev, key=lambda s: 0 if s == "warn" else 1))


class DeepScanTests(unittest.TestCase):
    """AI referenced-but-undefined pass (uses a fake client — no network)."""

    class _NER:
        """Fake client: returns named entities parsed from the passage via a fixed map."""
        def __init__(self, by_text):
            self.by_text = by_text
            self.calls = 0
        def generate_content_with_json_repair(self, prompt, **kw):
            import json
            self.calls += 1
            # The passage text is appended after "TEXT:\n" in the prompt.
            body = prompt.split("TEXT:\n", 1)[-1]
            ents = []
            for needle, entity in self.by_text.items():
                if needle in body:
                    ents.append(entity)
            return json.dumps({"entities": ents})

    def test_undefined_entity_surfaced_known_one_ignored(self):
        kb = _kb()
        kb.add_character(Character(name="Maren", motivations="x", character_arc="y",
                                   voice_profile=VoiceProfile(speech_patterns="s")))
        # Two source texts; "Ashfall" appears in both (undefined), "Maren" is known → ignored.
        texts = [("Chapter 1", "Maren fled toward the Ashfall."),
                 ("Chapter 2", "The Ashfall glowed.")]
        client = self._NER({"Ashfall": {"name": "the Ashfall", "type": "lore"},
                            "Maren": {"name": "Maren", "type": "character"}})
        out = gap_finder.find_undefined_entities(client, kb, texts, max_workers=2)
        names = [g["entity_name"] for g in out["gaps"]]
        self.assertEqual(names, ["the Ashfall"])
        g = out["gaps"][0]
        self.assertEqual(g["type"], "undefined_entity")
        self.assertEqual(g["entity_type"], "lore")
        self.assertIn("2×", g["message"])   # counted across both chapters
        self.assertIsNone(g["target"])
        self.assertEqual(out["scanned"], 2)

    def test_no_client_or_no_texts_is_empty(self):
        kb = _kb()
        self.assertEqual(gap_finder.find_undefined_entities(None, kb, [("a", "b")], 2)["gaps"], [])
        self.assertEqual(gap_finder.find_undefined_entities(object(), kb, [], 2)["gaps"], [])

    def test_gather_source_texts_includes_lore_freetext(self):
        kb = _kb()
        kb.add_character(Character(name="Maren", background="Raised in the Deepvault.",
                                   motivations="m", character_arc="a"))
        kb.add_location(Location(name="Keep", description="A stone tower.", significance="s"))
        texts = gap_finder.gather_source_texts(kb, project_dir=None)  # no prose dir
        labels = [t[0] for t in texts]
        self.assertIn("character:Maren", labels)
        self.assertIn("location:Keep", labels)
        joined = "\n".join(t[1] for t in texts)
        self.assertIn("Deepvault", joined)


if __name__ == "__main__":
    unittest.main()
