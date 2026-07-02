"""Tests for parse_llm_json — the fenced/preamble-tolerant JSON extractor that fixed the lore
intake bug (local models wrap JSON in ```json fences, which json.loads() cannot parse)."""
import unittest

from libriscribe.utils.file_utils import parse_llm_json


class ParseLlmJsonTests(unittest.TestCase):
    def test_json_fenced_dict(self):
        self.assertEqual(parse_llm_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_plain_fenced_dict(self):
        self.assertEqual(parse_llm_json('```\n{"a": 1}\n```'), {"a": 1})

    def test_bare_dict(self):
        self.assertEqual(parse_llm_json('{"a": 1}'), {"a": 1})

    def test_preamble_then_json_fence(self):
        text = 'Sure! Here is the JSON:\n```json\n{"role": "hero"}\n```'
        self.assertEqual(parse_llm_json(text), {"role": "hero"})

    def test_preamble_then_bare_json(self):
        text = "Reasoning: this is a character.\n{\n  \"role\": \"hero\"\n}\nDone."
        self.assertEqual(parse_llm_json(text), {"role": "hero"})

    def test_fenced_list(self):
        self.assertEqual(parse_llm_json('```json\n[1, 2, 3]\n```'), [1, 2, 3])

    def test_brace_inside_string_not_a_false_close(self):
        # The balanced scan must ignore braces that live inside a JSON string value.
        self.assertEqual(parse_llm_json('prefix {"a": "has } brace"} suffix'), {"a": "has } brace"})

    def test_escaped_quote_inside_string(self):
        self.assertEqual(parse_llm_json('{"a": "she said \\"hi\\""}'), {"a": 'she said "hi"'})

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_llm_json("no json here at all"))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_llm_json(""))
        self.assertIsNone(parse_llm_json("   "))


if __name__ == "__main__":
    unittest.main()
