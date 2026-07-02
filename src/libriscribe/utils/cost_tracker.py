"""Cost tracking for LLM API usage."""
import json
import logging
from datetime import datetime

from libriscribe.utils.paths import get_app_data_dir

logger = logging.getLogger(__name__)


class CostTracker:
    """Track LLM usage and costs."""

    # Pricing per 1K tokens (input/output) - update as needed
    PRICING = {
        "openai/gpt-4o": (0.0025, 0.01),
        "openai/gpt-4o-mini": (0.00015, 0.0006),
        "anthropic/claude-3-5-sonnet": (0.003, 0.015),
        "openrouter/anthropic/claude-3.5-sonnet": (0.003, 0.015),
        "openrouter/openai/gpt-4o": (0.0025, 0.01),
    }

    def __init__(self, log_file: str | None = None):
        # Absolute path in the user-writable app-data dir. A RELATIVE default resolved against the
        # current working directory, which is READ-ONLY in the installed app (Program Files) — the
        # write then raised inside _generate_once and made every LLM completion return "".
        self.log_file = log_file or str(get_app_data_dir() / "llm_usage.jsonl")

    def log_usage(self, provider: str, model: str, operation: str,
                  input_tokens: int, output_tokens: int,
                  cost: float = 0.0) -> None:
        """Log LLM usage to JSONL file. Best-effort — cost logging must NEVER break a generation."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "model": model,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as exc:  # noqa: BLE001 — a logging failure must not abort the LLM call
            logger.warning("Could not write usage log (%s): %s", self.log_file, exc)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        if model in self.PRICING:
            input_cost, output_cost = self.PRICING[model]
            return (input_tokens * input_cost / 1000) + (output_tokens * output_cost / 1000)
        return 0.0
