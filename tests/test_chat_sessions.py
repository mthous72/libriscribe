"""Tests for multi-session brainstorm storage + migration (B18)."""
import json
import tempfile
import unittest
from pathlib import Path

import libriscribe.api.routers.chat as chat


class ChatSessionStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = chat.get_projects_dir
        chat.get_projects_dir = lambda: self.tmp
        (self.tmp / "demo").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        chat.get_projects_dir = self._orig

    def test_seeds_default_general_session(self):
        sessions = chat._list_sessions("demo")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "General")

    def test_migrates_legacy_history(self):
        # A legacy single-thread history exists.
        (self.tmp / "demo" / "chat_history.json").write_text(
            json.dumps([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]),
            encoding="utf-8",
        )
        sessions = chat._list_sessions("demo")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "General")
        self.assertEqual(len(sessions[0]["messages"]), 2)

    def test_create_and_resolve_and_append(self):
        s = chat._new_session("Villain arc", focus={"type": "character", "name": "Mordecai"})
        chat._save_session("demo", s)
        chat._append_message("demo", s, "user", "what's his weakness?")
        loaded = chat._load_session("demo", s["id"])
        self.assertEqual(loaded["title"], "Villain arc")
        self.assertEqual(loaded["focus"]["name"], "Mordecai")
        self.assertEqual(loaded["messages"][0]["content"], "what's his weakness?")

    def test_resolve_specific_vs_default(self):
        default = chat._list_sessions("demo")[0]
        other = chat._new_session("Plot")
        chat._save_session("demo", other)
        self.assertEqual(chat._resolve_session("demo", other["id"])["id"], other["id"])
        # Unknown id falls back to the default (oldest) session.
        self.assertEqual(chat._resolve_session("demo", "nope1234")["id"], default["id"])

    def test_meta_strips_messages_and_counts(self):
        s = chat._new_session("X")
        chat._append_message("demo", s, "user", "a")
        meta = chat._session_meta(s)
        self.assertNotIn("messages", meta)
        self.assertEqual(meta["message_count"], 1)


if __name__ == "__main__":
    unittest.main()
