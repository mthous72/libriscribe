"""Reasoning-model support: adaptive budget retry, think-tag stripping, stream filtering.

Repro: qwen3.6-35b-a3b (Hermes-style reasoner) via LM Studio spent the ENTIRE max_tokens
budget in its private think channel — content empty, finish_reason=length, all completion
tokens counted as reasoning_tokens — so every LibriScribe stage failed with empty_response.
"""
import unittest
from types import SimpleNamespace

from libriscribe.utils.llm_client import LLMClient


def _resp(content, finish="stop", reasoning_tokens=0, reasoning_content=None):
    msg = SimpleNamespace(content=content, reasoning_content=reasoning_content)
    choice = SimpleNamespace(message=msg, finish_reason=finish)
    details = SimpleNamespace(reasoning_tokens=reasoning_tokens)
    usage = SimpleNamespace(completion_tokens_details=details)
    return SimpleNamespace(choices=[choice], usage=usage)


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


def _client_with(responses):
    c = LLMClient("local")
    fake = _FakeClient(responses)
    c._get_client_for_provider = lambda provider: fake
    c._log_usage = lambda *a, **k: None
    return c, fake


class StripReasoningTests(unittest.TestCase):
    def test_strips_think_blocks_and_orphan_closers(self):
        self.assertEqual(LLMClient._strip_reasoning("<think>plan plan</think>\nThe prose."), "The prose.")
        self.assertEqual(LLMClient._strip_reasoning("leaked thinking...</think>The prose."), "The prose.")
        self.assertEqual(LLMClient._strip_reasoning("Just prose."), "Just prose.")
        self.assertEqual(LLMClient._strip_reasoning(""), "")


class AdaptiveBudgetTests(unittest.TestCase):
    def test_thinking_ate_budget_retries_with_headroom(self):
        c, fake = _client_with([
            _resp("", finish="length", reasoning_tokens=300),
            _resp("The actual outline text."),
        ])
        out = c.generate_content("prompt", max_tokens=300)
        self.assertEqual(out, "The actual outline text.")
        self.assertEqual(len(fake.chat.completions.calls), 2)
        self.assertGreaterEqual(fake.chat.completions.calls[1]["max_tokens"], 300 + 6144)

    def test_escalates_twice_when_model_thinks_very_long(self):
        c, fake = _client_with([
            _resp("", finish="length", reasoning_tokens=300),
            _resp("", finish="length", reasoning_tokens=6444),
            _resp("Finally, the answer."),
        ])
        out = c.generate_content("prompt", max_tokens=300)
        self.assertEqual(out, "Finally, the answer.")
        self.assertEqual(len(fake.chat.completions.calls), 3)
        self.assertGreaterEqual(fake.chat.completions.calls[2]["max_tokens"], 300 + 16384)

    def test_thinking_truncated_content_also_retries(self):
        c, fake = _client_with([
            _resp("Half an outl", finish="length", reasoning_tokens=1500),
            _resp("The full outline text, much longer than before."),
        ])
        out = c.generate_content("prompt", max_tokens=2000)
        self.assertEqual(out, "The full outline text, much longer than before.")
        self.assertEqual(fake.chat.completions.calls[1]["max_tokens"], 2000 + 6144)

    def test_learned_allowance_applies_preemptively(self):
        c, fake = _client_with([
            _resp("", finish="length", reasoning_tokens=300),
            _resp("Answer.", finish="stop", reasoning_tokens=2496),
            _resp("Second call answer."),
        ])
        c.generate_content("first", max_tokens=300)
        out = c.generate_content("second", max_tokens=500)
        self.assertEqual(out, "Second call answer.")
        # third API call = second generate_content; budget carries observed 2496 + margin
        self.assertEqual(fake.chat.completions.calls[2]["max_tokens"], 500 + 2496 + 1024)

    def test_ordinary_truncation_not_retried(self):
        # Scenes hit max_tokens by design on non-reasoning models — no retry, no extra cost.
        c, fake = _client_with([_resp("A full scene that just ran long", finish="length")])
        out = c.generate_content("prompt", max_tokens=2000)
        self.assertEqual(out, "A full scene that just ran long")
        self.assertEqual(len(fake.chat.completions.calls), 1)

    def test_empty_with_reasoning_content_but_no_usage_details(self):
        c, fake = _client_with([
            _resp("", finish="length", reasoning_content="x" * 600),
            _resp("Recovered."),
        ])
        out = c.generate_content("prompt", max_tokens=300)
        self.assertEqual(out, "Recovered.")

    def test_inline_think_block_stripped_from_content(self):
        c, _ = _client_with([_resp("<think>let me plan</think>The prose answer.")])
        self.assertEqual(c.generate_content("prompt", max_tokens=300), "The prose answer.")


class ThinkStreamFilterTests(unittest.TestCase):
    def _run(self, chunks):
        f = LLMClient._ThinkStreamFilter()
        out = "".join(f.feed(c) for c in chunks)
        return out + f.flush()

    def test_passthrough(self):
        self.assertEqual(self._run(["Hello ", "world."]), "Hello world.")

    def test_drops_think_span(self):
        self.assertEqual(self._run(["<think>secret</think>Prose."]), "Prose.")

    def test_tag_split_across_chunks(self):
        self.assertEqual(self._run(["<thi", "nk>secret</th", "ink>Prose ", "here."]), "Prose here.")

    def test_unclosed_think_yields_nothing(self):
        self.assertEqual(self._run(["<think>never stops thinking"]), "")

    def test_angle_bracket_prose_not_eaten(self):
        self.assertEqual(self._run(["a < b and c<d", " done."]), "a < b and c<d done.")


class SanitizerThinkStripTests(unittest.TestCase):
    def test_sanitize_prose_removes_think_blocks(self):
        from libriscribe.utils.prose_sanitizer import sanitize_prose
        self.assertEqual(sanitize_prose("<think>beat plan</think>The scene text."), "The scene text.")


if __name__ == "__main__":
    unittest.main()
