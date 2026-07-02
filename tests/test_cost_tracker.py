"""Cost logging must never break an LLM call (it did on installed builds: a relative log path in a
read-only CWD raised, bubbled up through _generate_once, and made every completion return "")."""
import unittest
from pathlib import Path

from libriscribe.utils.cost_tracker import CostTracker
from libriscribe.utils.paths import get_app_data_dir


class CostTrackerTests(unittest.TestCase):
    def test_default_path_is_writable_app_data(self):
        ct = CostTracker()
        self.assertEqual(Path(ct.log_file).parent, get_app_data_dir())

    def test_log_usage_never_raises_on_bad_path(self):
        # A path that cannot be opened must be swallowed, not raised.
        ct = CostTracker(log_file="Z:/nonexistent-drive/does/not/exist/usage.jsonl")
        try:
            ct.log_usage("local", "m", "generate_content", 10, 20, 0.0)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"log_usage raised on a bad path: {exc!r}")

    def test_log_usage_writes_when_path_ok(self):
        import tempfile
        d = tempfile.mkdtemp()
        f = str(Path(d) / "usage.jsonl")
        CostTracker(log_file=f).log_usage("local", "m", "op", 1, 2, 0.0)
        self.assertTrue(Path(f).exists())


if __name__ == "__main__":
    unittest.main()
