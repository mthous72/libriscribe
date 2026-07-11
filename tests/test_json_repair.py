"""B43 — auto-repair for damaged import JSON.

Fixtures model the real defects from a user's hand-merged bundle (2026-07-09): orphan
duplicate chapter blocks that over-close the document ("Extra data"), a missing comma
after the chapters object, plus the common BOM / trailing-comma / mojibake cases.
"""
import json
import unittest

from libriscribe.utils.json_repair import repair_json

# An orphan duplicate "summary"+"scenes" block dangling after chapter "1" closed —
# the exact shape that broke the real file (extra closing brace ends the document early).
ORPHAN_BLOCK = """{
  "chapters": {
    "1": {
      "title": "One",
      "summary": "New summary.",
      "scenes": [
        {"scene_number": 1, "summary": "New scene."}
      ]
    },
      "summary": "Old stale summary.",
      "scenes": [
        {"scene_number": 1, "summary": "Old scene."}
      ]
    },
    "2": {
      "title": "Two",
      "summary": "Chapter two.",
      "scenes": []
    }
  },
  "outline": "text"
}"""

MISSING_COMMA = """{
  "chapters": {
    "1": {"title": "One", "scenes": []}
  }
  "outline": "text"
}"""


class RepairJsonTests(unittest.TestCase):
    def test_valid_json_untouched(self):
        data, repairs = repair_json('{"a": 1, "b": [2, 3]}')
        self.assertEqual(data, {"a": 1, "b": [2, 3]})
        self.assertEqual(repairs, [])

    def test_orphan_duplicate_block_removed(self):
        data, repairs = repair_json(ORPHAN_BLOCK)
        self.assertEqual(data["chapters"]["1"]["summary"], "New summary.")
        self.assertEqual(data["chapters"]["2"]["title"], "Two")
        self.assertEqual(data["outline"], "text")
        self.assertTrue(any("orphan" in r for r in repairs), repairs)

    def test_missing_comma_inserted(self):
        data, repairs = repair_json(MISSING_COMMA)
        self.assertEqual(data["outline"], "text")
        self.assertTrue(any("comma" in r for r in repairs), repairs)

    def test_trailing_comma_removed(self):
        data, repairs = repair_json('{"a": 1, "b": [1, 2,], }')
        self.assertEqual(data, {"a": 1, "b": [1, 2]})
        self.assertTrue(any("trailing comma" in r for r in repairs), repairs)

    def test_bom_stripped(self):
        data, repairs = repair_json('﻿{"a": 1}')
        self.assertEqual(data, {"a": 1})
        self.assertTrue(any("byte-order mark" in r for r in repairs))

    def test_mojibake_in_strings_fixed(self):
        # em dash mangled by a cp1252 round-trip inside a string value
        moji = "CEE—a unit".encode("utf-8").decode("cp1252", errors="replace")
        data, repairs = repair_json(json.dumps({"description": moji}, ensure_ascii=False))
        self.assertEqual(data["description"], "CEE—a unit")
        self.assertTrue(any("mojibake" in r for r in repairs), repairs)

    def test_trailing_whitespace_extra_data_ok(self):
        data, repairs = repair_json('{"a": 1}   \n\n')
        self.assertEqual(data, {"a": 1})

    def test_unrepairable_raises_original_error(self):
        with self.assertRaises(json.JSONDecodeError):
            repair_json('{"a": totally not json ###')

    def test_strings_containing_braces_not_confused(self):
        # brace-counting must ignore braces inside string values
        src = '{"a": "text with } and { inside", "b": 2}'
        data, repairs = repair_json(src)
        self.assertEqual(data["a"], "text with } and { inside")
        self.assertEqual(repairs, [])


class ImportEndpointRepairTests(unittest.TestCase):
    def setUp(self):
        import os, tempfile
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"PROJECTS_DIR": self.tmp.name}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self.tmp.cleanup()

    def _client(self):
        from fastapi.testclient import TestClient
        from libriscribe.api.app import create_app
        return TestClient(create_app())

    def test_import_raw_with_repairs(self):
        bundle = {
            "app": "libriscribe", "schema_version": 1,
            "project_name": "fixit",
            "project_data": {"project_name": "fixit", "title": "T", "genre": "F"},
            "files": {},
        }
        # break it: trailing comma before final brace
        raw = json.dumps(bundle, indent=2)
        raw = raw[: raw.rfind("}")].rstrip()
        raw = raw.rstrip("}").rstrip().rstrip(",") + ",\n}\n}"  # mangled tail
        client = self._client()
        r = client.post("/api/projects/import", json={"raw": '﻿' + json.dumps(bundle)})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["project_name"], "fixit")
        self.assertTrue(any("byte-order mark" in x for x in body["repairs"]))

    def test_import_unrepairable_raw_400(self):
        client = self._client()
        r = client.post("/api/projects/import", json={"raw": "not json at all {{{"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("could not be auto-repaired", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()
