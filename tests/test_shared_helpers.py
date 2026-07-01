"""Tests for the shared helpers extracted during the Tier-1 refactor."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from libriscribe.utils.token_utils import estimate_tokens
from libriscribe.utils.file_utils import resolve_chapter_path
from libriscribe.retrieval.models import RetrievalChunk, RetrievalConfig, mode_str, matches_filters, chunk_to_result
from libriscribe.services.retrieval_service import get_retrieval_config


def _chunk(source_type="lore", chapter=None, characters=None):
    return RetrievalChunk(
        chunk_id="c", document_id="d", project_name="t", text="x", source_type=source_type,
        chunk_index=0, hash="c", chapter_number=chapter, characters=characters or [],
    )


class TokenUtilsTests(unittest.TestCase):
    def test_empty_and_nonempty(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens(None), 0)
        self.assertGreater(estimate_tokens("one two three four five"), 0)


class ResolveChapterPathTests(unittest.TestCase):
    def test_prefers_revised_when_present(self):
        d = Path(tempfile.mkdtemp())
        (d / "chapter_1.md").write_text("base", encoding="utf-8")
        self.assertEqual(resolve_chapter_path(d, 1).name, "chapter_1.md")
        (d / "chapter_1_revised.md").write_text("rev", encoding="utf-8")
        self.assertEqual(resolve_chapter_path(d, 1).name, "chapter_1_revised.md")


class ModelHelperTests(unittest.TestCase):
    def test_mode_str(self):
        self.assertEqual(mode_str("Hybrid"), "hybrid")
        self.assertEqual(mode_str(SimpleNamespace(value="SEMANTIC")), "semantic")

    def test_matches_filters(self):
        self.assertTrue(matches_filters(_chunk("lore"), None))
        self.assertTrue(matches_filters(_chunk("lore"), {"source_type": ["lore", "prose"]}))
        self.assertFalse(matches_filters(_chunk("reference"), {"source_type": "lore"}))
        self.assertFalse(matches_filters(_chunk("reference"), {"exclude_source_type": ["reference"]}))
        self.assertFalse(matches_filters(_chunk(chapter=3), {"chapter_number": 5}))
        self.assertTrue(matches_filters(_chunk(characters=["Ada"]), {"characters": ["Ada", "Bo"]}))

    def test_chunk_to_result_labels_score(self):
        r = chunk_to_result(_chunk("lore"), 1.5, "semantic")
        self.assertEqual(r.score, 1.5)
        self.assertEqual(r.score_breakdown, {"semantic_score": 1.5})


class RetrievalConfigHelperTests(unittest.TestCase):
    def test_returns_enabled_config_or_default(self):
        kb_off = SimpleNamespace(retrieval=None)
        cfg = get_retrieval_config(kb_off, "hybrid")
        self.assertTrue(cfg.enabled)
        self.assertEqual(mode_str(cfg.mode), "hybrid")

        existing = RetrievalConfig(enabled=True, mode="semantic")
        kb_on = SimpleNamespace(retrieval=existing)
        self.assertIs(get_retrieval_config(kb_on), existing)

        kb_disabled = SimpleNamespace(retrieval=RetrievalConfig(enabled=False))
        self.assertTrue(get_retrieval_config(kb_disabled).enabled)  # falls back to enabled default


if __name__ == "__main__":
    unittest.main()
