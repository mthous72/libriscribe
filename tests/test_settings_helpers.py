"""Tests for settings helpers: placeholder-key detection and base-URL normalization."""
import unittest

from libriscribe.utils.model_routing import normalize_openai_base_url
from libriscribe.api.routers.settings import _is_real_key, _mask_key


class NormalizeBaseUrlTests(unittest.TestCase):
    def test_appends_v1_for_bare_host(self):
        self.assertEqual(normalize_openai_base_url("http://localhost:1234"), "http://localhost:1234/v1")
        self.assertEqual(normalize_openai_base_url("http://localhost:1234/"), "http://localhost:1234/v1")
        self.assertEqual(normalize_openai_base_url("http://192.168.1.5:8080"), "http://192.168.1.5:8080/v1")

    def test_leaves_existing_path(self):
        self.assertEqual(normalize_openai_base_url("http://localhost:1234/v1"), "http://localhost:1234/v1")
        self.assertEqual(normalize_openai_base_url("https://openrouter.ai/api/v1"), "https://openrouter.ai/api/v1")

    def test_empty(self):
        self.assertEqual(normalize_openai_base_url(""), "")


class KeyHelperTests(unittest.TestCase):
    def test_placeholders_are_not_real(self):
        for value in ["", "your_api_key_here", "YOUR_API_KEY_HERE", "changeme", "   "]:
            self.assertFalse(_is_real_key(value), value)

    def test_real_key(self):
        self.assertTrue(_is_real_key("sk-abc123def456ghi"))

    def test_mask_hides_placeholder_and_short(self):
        self.assertEqual(_mask_key("your_api_key_here"), "")
        self.assertEqual(_mask_key(""), "")
        masked = _mask_key("sk-abcdefghijklmnop")
        self.assertIn("...", masked)
        self.assertTrue(masked.startswith("sk-a"))


if __name__ == "__main__":
    unittest.main()
