"""Tests for the smart lore intake engine (B12 + B13).

Covers the deterministic foreign-format adapters (SillyTavern card, KoboldAI /
SillyTavern World Info, native bundle), proposal annotation (new/update), and the
smart-merge apply (preserve untouched fields, coerce typed fields).
"""
import unittest

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, Location
from libriscribe.services import lore_intake


def _kb():
    return ProjectKnowledgeBase(project_name="t", title="Book", genre="Fantasy")


class AdapterTests(unittest.TestCase):
    def test_sillytavern_v2_card_to_character_plus_book(self):
        data = {
            "spec": "chara_card_v2",
            "data": {
                "name": "Tya",
                "description": "A wiry rogue with quick hands.",
                "personality": "sly, loyal",
                "scenario": "The thieves' guild of Vell.",
                "first_mes": "Hey there.",
                "character_book": {"entries": [
                    {"keys": ["Vell"], "comment": "City of Vell", "content": "A canal city."},
                ]},
            },
        }
        cats, label = lore_intake.detect_and_adapt(data)
        self.assertIn("SillyTavern", label)
        self.assertEqual(len(cats["characters"]), 1)
        ch = cats["characters"][0]
        self.assertEqual(ch["name"], "Tya")
        self.assertEqual(ch["fields"]["personality_traits"], "sly, loyal")
        self.assertIn("wiry rogue", ch["fields"]["background"])
        self.assertIn("Scenario:", ch["fields"]["background"])
        # Embedded character_book becomes a lore entry.
        self.assertEqual(len(cats["lore"]), 1)
        self.assertEqual(cats["lore"][0]["name"], "City of Vell")

    def test_v1_flat_card_detected(self):
        data = {"name": "Bran", "description": "A guard.", "first_mes": "Halt!"}
        cats, label = lore_intake.detect_and_adapt(data)
        self.assertEqual(cats["characters"][0]["name"], "Bran")

    def test_world_info_object_keyed_entries(self):
        data = {"entries": {
            "0": {"uid": 0, "key": ["dragon", "wyrm"], "comment": "Dragons", "content": "Ancient fire-breathers."},
            "1": {"uid": 1, "keys": ["guild"], "content": "The thieves' guild."},
        }}
        cats, label = lore_intake.detect_and_adapt(data)
        self.assertIn("World Info", label)
        self.assertEqual(len(cats["lore"]), 2)
        names = {r["name"] for r in cats["lore"]}
        self.assertIn("Dragons", names)        # comment used as name
        self.assertIn("guild", names)          # falls back to first key
        dragons = next(r for r in cats["lore"] if r["name"] == "Dragons")
        self.assertIn("dragon", dragons["fields"]["tags"])

    def test_world_info_list_entries(self):
        data = {"entries": [
            {"keys": ["moon"], "comment": "The Twin Moons", "content": "Two moons orbit."},
        ]}
        cats, _ = lore_intake.detect_and_adapt(data)
        self.assertEqual(cats["lore"][0]["name"], "The Twin Moons")

    def test_native_bundle_passthrough(self):
        data = {"characters": [{"name": "Ada", "role": "hero"}], "locations": [{"name": "Keep", "desc": "stone"}]}
        cats, label = lore_intake.detect_and_adapt(data)
        self.assertEqual(label, "lore JSON")
        self.assertEqual(cats["characters"][0]["name"], "Ada")
        self.assertEqual(cats["locations"][0]["name"], "Keep")

    def test_unrecognized_returns_none(self):
        self.assertIsNone(lore_intake.detect_and_adapt({"foo": "bar", "baz": 1}))


class ProposalTests(unittest.TestCase):
    def test_status_new_vs_update_case_insensitive(self):
        kb = _kb()
        kb.add_character(Character(name="Tya", role="rogue"))
        cats = {
            "characters": [
                {"name": "tya", "fields": {"motivations": "freedom"}},   # matches existing (ci)
                {"name": "Mira", "fields": {"role": "mage"}},            # new
            ],
            "locations": [], "lore": [], "arcs": [],
        }
        prop = lore_intake.build_proposal(kb, cats)
        by_name = {r["name"]: r for r in prop["characters"]}
        self.assertEqual(by_name["Tya"]["status"], "update")   # resolves to existing key casing
        self.assertEqual(by_name["Mira"]["status"], "new")

    def test_fields_stringified_for_review(self):
        kb = _kb()
        cats = {"characters": [], "locations": [
            {"name": "Keep", "fields": {"tags": ["stone", "old"], "associated_characters": ["Ada"]}},
        ], "lore": [], "arcs": []}
        prop = lore_intake.build_proposal(kb, cats)
        loc = prop["locations"][0]
        self.assertEqual(loc["fields"]["tags"], "stone, old")  # list rendered as editable string


class MergeApplyTests(unittest.TestCase):
    def test_merge_preserves_untouched_fields(self):
        kb = _kb()
        kb.add_character(Character(name="Tya", role="rogue", background="Born in Vell."))
        records = {"characters": [{"name": "Tya", "fields": {"motivations": "freedom"}}]}
        summary = lore_intake.merge_apply(kb, records)
        self.assertEqual(summary["characters"], 1)
        tya = kb.characters["Tya"]
        self.assertEqual(tya.motivations, "freedom")   # added
        self.assertEqual(tya.role, "rogue")            # preserved
        self.assertEqual(tya.background, "Born in Vell.")  # preserved

    def test_empty_field_does_not_wipe(self):
        kb = _kb()
        kb.add_character(Character(name="Tya", role="rogue"))
        lore_intake.merge_apply(kb, {"characters": [{"name": "Tya", "fields": {"role": ""}}]})
        self.assertEqual(kb.characters["Tya"].role, "rogue")  # blank ignored

    def test_creates_new_entity(self):
        kb = _kb()
        summary = lore_intake.merge_apply(kb, {"locations": [{"name": "Cove", "fields": {"description": "hidden"}}]})
        self.assertEqual(summary["locations"], 1)
        self.assertEqual(kb.locations["Cove"].description, "hidden")

    def test_string_to_list_field_coercion(self):
        kb = _kb()
        lore_intake.merge_apply(kb, {"locations": [{"name": "Cove", "fields": {"tags": "hidden, coastal"}}]})
        self.assertEqual(kb.locations["Cove"].tags, ["hidden", "coastal"])

    def test_case_insensitive_update_keeps_existing_key(self):
        kb = _kb()
        kb.add_location(Location(name="Vell", description="city"))
        lore_intake.merge_apply(kb, {"locations": [{"name": "vell", "fields": {"significance": "capital"}}]})
        self.assertEqual(set(kb.locations.keys()), {"Vell"})           # no duplicate key
        self.assertEqual(kb.locations["Vell"].significance, "capital")

    def test_worldbuilding_merge(self):
        kb = _kb()
        summary = lore_intake.merge_apply(kb, {"worldbuilding": {"fields": {"magic_system": "rune-based"}}})
        self.assertEqual(summary["worldbuilding"], 1)
        self.assertEqual(kb.worldbuilding.magic_system, "rune-based")


if __name__ == "__main__":
    unittest.main()
