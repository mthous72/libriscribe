"""Bounded parallel runner (B29) — order, isolation, the concurrency cap, and the serial 'off' switch."""
import threading
import time
import unittest

from libriscribe.utils import parallel


class ClampTests(unittest.TestCase):
    def test_clamp_floors_at_one(self):
        self.assertEqual(parallel.clamp_workers(0), 1)
        self.assertEqual(parallel.clamp_workers(-5), 1)
        self.assertEqual(parallel.clamp_workers(4), 4)

    def test_clamp_bad_values_use_default(self):
        self.assertEqual(parallel.clamp_workers(None, default=4), 4)
        self.assertEqual(parallel.clamp_workers("x", default=3), 3)

    def test_resolve_reads_kb_field(self):
        class KB:  # duck-typed
            max_concurrency = 2
        self.assertEqual(parallel.resolve_max_workers(KB()), 2)
        self.assertEqual(parallel.resolve_max_workers(object(), default=4), 4)  # missing -> default


class BoundedMapTests(unittest.TestCase):
    def test_results_preserve_input_order(self):
        # Later items finish sooner, but results must stay aligned to input order.
        def fn(i):
            time.sleep(0.02 * (5 - i))
            return i * 10
        out = parallel.bounded_map(fn, [0, 1, 2, 3, 4], max_workers=4)
        self.assertEqual(out, [0, 10, 20, 30, 40])

    def test_empty_input(self):
        self.assertEqual(parallel.bounded_map(lambda x: x, [], max_workers=4), [])

    def test_exception_isolated_to_none(self):
        def fn(i):
            if i == 2:
                raise ValueError("boom")
            return i
        out = parallel.bounded_map(fn, [0, 1, 2, 3], max_workers=3)
        self.assertEqual(out, [0, 1, None, 3])

    def test_serial_when_one_worker(self):
        # max_workers=1 must run sequentially: peak observed concurrency is exactly 1.
        peak, cur, lock = 0, 0, threading.Lock()

        def fn(i):
            nonlocal peak, cur
            with lock:
                cur += 1
                peak = max(peak, cur)
            time.sleep(0.01)
            with lock:
                cur -= 1
            return i
        out = parallel.bounded_map(fn, list(range(6)), max_workers=1)
        self.assertEqual(out, list(range(6)))
        self.assertEqual(peak, 1)

    def test_respects_worker_cap(self):
        # With cap=2, no more than 2 calls ever run concurrently.
        peak, cur, lock = 0, 0, threading.Lock()

        def fn(i):
            nonlocal peak, cur
            with lock:
                cur += 1
                peak = max(peak, cur)
            time.sleep(0.02)
            with lock:
                cur -= 1
            return i
        parallel.bounded_map(fn, list(range(8)), max_workers=2)
        self.assertLessEqual(peak, 2)
        self.assertGreaterEqual(peak, 2)  # it did actually parallelize

    def test_progress_callback_fires_per_item(self):
        seen = []
        lock = threading.Lock()

        def on_progress(done, total):
            with lock:
                seen.append((done, total))
        parallel.bounded_map(lambda i: i, list(range(5)), max_workers=3, on_progress=on_progress)
        self.assertEqual(len(seen), 5)
        self.assertEqual(seen[-1][0], 5)          # final done count
        self.assertTrue(all(t == 5 for _, t in seen))
        self.assertEqual(sorted(d for d, _ in seen), [1, 2, 3, 4, 5])  # monotonic, no dupes


if __name__ == "__main__":
    unittest.main()
