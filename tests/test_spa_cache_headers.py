"""B45 follow-up: SPA cache policy — index.html must never be cached (stale-bundle trap),
hashed assets may be cached forever."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class SpaCacheHeaderTests(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("LIBRISCRIBE_PROJECTS_DIR")
        os.environ["LIBRISCRIBE_PROJECTS_DIR"] = tempfile.mkdtemp()
        # A fake dist so the SPA mount activates regardless of local build state.
        self.dist = Path(tempfile.mkdtemp())
        (self.dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
        (self.dist / "assets").mkdir()
        (self.dist / "assets" / "index-abc123.js").write_text("//js", encoding="utf-8")

        from fastapi.testclient import TestClient
        import libriscribe.api.app as app_module
        with mock.patch.object(app_module, "get_frontend_dist", return_value=self.dist):
            self.client = TestClient(app_module.create_app())

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LIBRISCRIBE_PROJECTS_DIR", None)
        else:
            os.environ["LIBRISCRIBE_PROJECTS_DIR"] = self._prev

    def test_index_and_spa_fallback_never_cached(self):
        for path in ("/", "/projects/anything"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertEqual(r.headers.get("cache-control"), "no-cache", path)

    def test_hashed_assets_cached_forever(self):
        r = self.client.get("/assets/index-abc123.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("immutable", r.headers.get("cache-control", ""))

    def test_api_404_untouched(self):
        r = self.client.get("/api/projects/nope")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
