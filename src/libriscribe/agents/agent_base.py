# src/libriscribe/agents/agent_base.py
import logging
from typing import Any, Callable, Optional

from libriscribe.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Event callback type: (event_type: str, payload: dict) -> None
EventCallback = Callable[[str, Any], None]


def _noop_callback(event_type: str, payload: Any) -> None:
    """Default no-op callback when no event callback is set."""
    pass


class Agent:
    """Base class for all agents."""

    def __init__(self, name: str, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        self.name = name
        self.llm_client = llm_client
        self.logger = logging.getLogger(self.name)
        self.event_callback: EventCallback = event_callback or _noop_callback

    def emit(self, event_type: str, payload: Any = None) -> None:
        """Emits an event via the callback."""
        if payload is None:
            payload = {}
        if isinstance(payload, str):
            payload = {"message": payload, "agent": self.name}
        elif isinstance(payload, dict) and "agent" not in payload:
            payload["agent"] = self.name
        self.event_callback(event_type, payload)

    def execute(self, *args, **kwargs) -> Any:
        """Executes the agent's main task. Must be implemented by subclasses."""
        raise NotImplementedError
