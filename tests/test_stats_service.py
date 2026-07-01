"""Tests for readability & manuscript statistics (B14)."""
import unittest

from libriscribe.services import stats_service


class TextStatsTests(unittest.TestCase):
    def test_empty_text(self):
        s = stats_service.compute_text_stats("")
        self.assertEqual(s["word_count"], 0)
        self.assertEqual(s["flesch_reading_ease"], 0.0)

    def test_counts(self):
        s = stats_service.compute_text_stats("The cat sat. The dog ran fast!")
        self.assertEqual(s["word_count"], 7)
        self.assertEqual(s["sentence_count"], 2)
        self.assertGreaterEqual(s["reading_time_min"], 0.0)
        # A longer passage registers a non-zero reading time.
        long_stats = stats_service.compute_text_stats(" ".join(["word"] * 500))
        self.assertGreater(long_stats["reading_time_min"], 0.0)

    def test_adverb_and_dialogue_ratios(self):
        s = stats_service.compute_text_stats('She ran quickly. "Hello there," he said softly.')
        self.assertGreater(s["adverb_ratio"], 0.0)     # quickly, softly
        self.assertGreater(s["dialogue_ratio"], 0.0)   # "Hello there,"

    def test_reading_ease_simple_vs_complex(self):
        simple = stats_service.compute_text_stats("The cat sat on the mat. The dog ran.")
        complex_ = stats_service.compute_text_stats(
            "Consequently, the extraordinarily sophisticated methodology necessitated "
            "comprehensive reconsideration of fundamental epistemological assumptions."
        )
        self.assertGreater(simple["flesch_reading_ease"], complex_["flesch_reading_ease"])

    def test_syllable_heuristic(self):
        self.assertEqual(stats_service._syllables("cat"), 1)
        self.assertGreaterEqual(stats_service._syllables("beautiful"), 3)


if __name__ == "__main__":
    unittest.main()
