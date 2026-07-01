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
        other["created_at"] = "2099-01-01T00:00:00+00:00"  # explicitly newer than the seeded default
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


class RollingMemoryTests(unittest.TestCase):
    class _FakeClient:
        def __init__(self):
            self.calls = 0
        def generate_content(self, prompt, **kw):
            self.calls += 1
            return "MEMORY: prior + new folded together"

    def setUp(self):
        from libriscribe.knowledge_base import ProjectKnowledgeBase
        self.tmp = Path(tempfile.mkdtemp())
        self._orig = chat.get_projects_dir
        chat.get_projects_dir = lambda: self.tmp
        (self.tmp / "demo").mkdir(parents=True, exist_ok=True)
        self.kb = ProjectKnowledgeBase(project_name="demo", title="Demo", genre="Fantasy")

    def tearDown(self):
        chat.get_projects_dir = self._orig

    def test_window_start_drops_old_and_build_from_start(self):
        history = [{"role": "user", "content": "word " * 150} for _ in range(20)]
        start = chat._window_start_index(history, 3000)
        self.assertGreater(start, 0)
        self.assertLess(start, len(history))
        convo = chat._build_conversation(history, start)
        self.assertTrue(convo.strip().endswith("Assistant:"))

    def test_summarizes_when_batch_reached(self):
        s = chat._new_session("Plot")
        s["messages"] = [{"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 150} for i in range(20)]
        chat._save_session("demo", s)
        client = self._FakeClient()
        orig = chat._RECENT_WINDOW_TOKENS
        try:
            summary, start = chat._manage_session_memory("demo", self.kb, s, client)
        finally:
            chat._RECENT_WINDOW_TOKENS = orig
        self.assertTrue(summary)                       # a running summary was produced
        self.assertGreaterEqual(client.calls, 1)
        self.assertEqual(s["summarized_upto"], start)
        # persisted
        self.assertEqual(chat._load_session("demo", s["id"])["summary"], summary)

    def test_no_summary_for_short_session(self):
        s = chat._new_session("Plot")
        s["messages"] = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]
        chat._save_session("demo", s)
        client = self._FakeClient()
        summary, start = chat._manage_session_memory("demo", self.kb, s, client)
        self.assertEqual(summary, "")
        self.assertEqual(client.calls, 0)              # nothing old enough to summarize
        self.assertEqual(start, 0)

    def test_new_session_has_memory_fields(self):
        s = chat._new_session("X")
        self.assertEqual(s["summary"], "")
        self.assertEqual(s["summarized_upto"], 0)


if __name__ == "__main__":
    unittest.main()
