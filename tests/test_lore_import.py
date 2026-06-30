"""Tests for the lore-import JSON parsing helpers."""
import unittest

from libriscribe.knowledge_base import Character, Location
from libriscribe.api.routers.lorebook import (
    _pick,
    _iter_entities,
    _coerce,
    _CATEGORY_KEYS,
)


class LoreImportParseTests(unittest.TestCase):
    def test_pick_is_case_insensitive_and_aliased(self):
        data = {"Lore_Entries": [{"name": "X"}]}
        self.assertIsNotNone(_pick(data, _CATEGORY_KEYS["lore"]))
        self.assertIsNone(_pick({"unrelated": 1}, _CATEGORY_KEYS["characters"]))

    def test_iter_entities_from_list(self):
        names = [n for n, _ in _iter_entities([{"name": "A"}, {"name": "B"}, {"no": "name"}])]
        self.assertEqual(names, ["A", "B"])

    def test_iter_entities_from_dict_keyed_by_name(self):
        out = dict(_iter_entities({"A": {"description": "d"}, "ignored": {"name": "BB"}}))
        self.assertIn("A", out)          # key used as name
        self.assertIn("BB", out)         # name in object overrides key

    def test_coerce_filters_unknown_and_applies_aliases(self):
        char = _coerce({"role": "rogue", "bogus_field": "x"}, Character, "Tya")
        self.assertEqual(char.name, "Tya")
        self.assertEqual(char.role, "rogue")

        loc = _coerce({"desc": "a hidden cove"}, Location, "Cove")
        self.assertEqual(loc.name, "Cove")
        self.assertEqual(loc.description, "a hidden cove")  # 'desc' -> 'description'


if __name__ == "__main__":
    unittest.main()
