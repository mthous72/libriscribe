"""Thread tracker -- detects narrative promises, setups, and payoffs after each chapter."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libriscribe.knowledge_base import ProjectKnowledgeBase
    from libriscribe.utils.llm_client import LLMClient

from libriscribe.knowledge_base import NarrativeThread
from libriscribe.utils.file_utils import extract_json_from_markdown, read_markdown_file

logger = logging.getLogger(__name__)


class ThreadTracker:
    """Analyzes chapters for narrative threads -- new and resolved."""

    def __init__(
        self,
        llm_client: LLMClient,
        kb: ProjectKnowledgeBase,
        project_dir: Path,
    ):
        self.llm_client = llm_client
        self.kb = kb
        self.project_dir = project_dir

    def analyze_chapter(self, chapter_number: int) -> None:
        """Reads a chapter, identifies new threads and resolves existing ones."""
        chapter_path = self.project_dir / f"chapter_{chapter_number}.md"
        if not chapter_path.exists():
            return

        chapter_text = read_markdown_file(str(chapter_path))
        if not chapter_text or not chapter_text.strip():
            return

        # Truncate for prompt size
        words = chapter_text.split()
        if len(words) > 2000:
            chapter_text = " ".join(words[:2000]) + "..."

        open_threads = [
            {"name": t.name, "type": t.thread_type, "description": t.description}
            for t in self.kb.narrative_threads.values()
            if t.status == "open"
        ]

        import json
        open_threads_json = json.dumps(open_threads, indent=2) if open_threads else "[]"

        prompt = f"""Analyze this chapter for narrative threads (promises, setups, questions, important items).

Chapter {chapter_number} text:
{chapter_text}

Currently open threads:
{open_threads_json}

Return a JSON object with two fields:
- new_threads: array of new threads found in this chapter. Each has:
  - name: short descriptive name
  - thread_type: "promise", "setup", "question", or "item"
  - description: what was set up or promised
  - characters_involved: list of character names involved
- resolved_thread_names: array of names from the open threads list that are resolved in this chapter

Return ONLY valid JSON, no markdown wrapper."""

        response = self.llm_client.generate_content_with_json_repair(
            prompt, max_tokens=1500, temperature=0.4
        )
        if not response:
            return

        data = extract_json_from_markdown(response)
        if not data or not isinstance(data, dict):
            return

        # Process new threads
        for t in data.get("new_threads", []):
            name = t.get("name", "")
            if not name or name in self.kb.narrative_threads:
                continue
            thread = NarrativeThread(
                name=name,
                thread_type=t.get("thread_type", "promise"),
                description=t.get("description", ""),
                opened_chapter=chapter_number,
                characters_involved=t.get("characters_involved", []),
                status="open",
            )
            self.kb.add_narrative_thread(thread)

        # Process resolved threads
        for resolved_name in data.get("resolved_thread_names", []):
            thread = self.kb.get_narrative_thread(resolved_name)
            if thread and thread.status == "open":
                thread.status = "resolved"
                thread.resolved_chapter = chapter_number

    def check_unresolved(self) -> list[NarrativeThread]:
        """Returns all open threads."""
        return [
            t for t in self.kb.narrative_threads.values()
            if t.status == "open"
        ]
