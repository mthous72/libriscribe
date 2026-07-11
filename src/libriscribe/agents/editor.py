# src/libriscribe/agents/editor.py

import logging
from pathlib import Path
from typing import Optional

from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils import prompts_context as prompts
from libriscribe.utils.file_utils import read_markdown_file, write_markdown_file
from libriscribe.knowledge_base import ProjectKnowledgeBase
from libriscribe.utils.llm_client import LLMClient
from libriscribe.agents.content_reviewer import ContentReviewerAgent

logger = logging.getLogger(__name__)

class EditorAgent(Agent):
    """Edits and refines chapters."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("EditorAgent", llm_client, event_callback)

    def execute(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int) -> None:
        """Edits a chapter and saves the revised version."""
        chapter_path = f"chapter_{chapter_number}.md"
        try:
            chapter_path = str(Path(project_knowledge_base.project_dir) / f"chapter_{chapter_number}.md")
            chapter_content = read_markdown_file(chapter_path)
            if not chapter_content:
                self.emit("log", {"level": "error", "message": f"Chapter file is empty: {chapter_path}"})
                return
            chapter_title = self.extract_chapter_title(chapter_content)

            reviewer_agent = ContentReviewerAgent(self.llm_client, self.event_callback)
            review_results = reviewer_agent.execute(chapter_path)

            # B39: scene delimiters are structural markers ("### Scene N"), not reader-facing
            # titles. Preserve them verbatim; never invent titles or summary-fragment headings.
            scene_markers = self.extract_scene_markers(chapter_content)
            scene_titles_instruction = ""
            if scene_markers:
                markers_str = "\n".join(f"- {m}" for m in scene_markers)
                scene_titles_instruction = f"""
                    IMPORTANT: This chapter is divided into scenes by delimiter lines. Keep each
                    delimiter line EXACTLY as written, on its own line, at the same scene break:

                    {markers_str}

                    Do NOT add any other scene titles, headings, or labels, and do not turn the
                    delimiters into prose.
                    """
            prompt_data = {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "book_title": project_knowledge_base.title,
                "genre": project_knowledge_base.genre,
                "language": project_knowledge_base.language,
                "chapter_content": chapter_content,
                "review_feedback": review_results.get("review", "")
            }

            self.emit("log", {"level": "info", "message": f"Editing Chapter {chapter_number} based on feedback..."})
            prompt = prompts.EDITOR_PROMPT.format(**prompt_data) + scene_titles_instruction

            # B40: name the chapter's overused phrases so the edit pass actively varies them.
            from libriscribe.utils.repetition_guard import repetition_report_block
            report = repetition_report_block(chapter_content)
            if report:
                prompt += f"\n\n{report}"

            # The edit pass must carry the SAME steering as the draft (register + canon +
            # writing system prompt) — a bare rewrite normalizes the prose back to generic.
            from libriscribe.utils.prose_steering import steering_blocks, writing_system_prompt
            steer = steering_blocks(project_knowledge_base)
            if steer:
                prompt = (
                    f"{steer}\n\nPRESERVE THE REGISTER: your edit must keep the intensity, "
                    f"register, and explicitness of the original — improve the prose WITHOUT "
                    f"toning it down.\n\n{prompt}"
                )
            edited_response = self.llm_client.generate_content(
                prompt, max_tokens=8000,
                system_prompt=writing_system_prompt(project_knowledge_base),
            )
            if "```" in edited_response:
                start = edited_response.find("```") + 3
                end = edited_response.rfind("```")
                next_newline = edited_response.find("\n", start)
                if next_newline < end and next_newline != -1:
                    start = next_newline + 1
                revised_chapter = edited_response[start:end].strip()
            else:
                lines = edited_response.split("\n")
                content_start = 0
                for i, line in enumerate(lines):
                    if line.startswith("#") or line.startswith("Chapter"):
                        content_start = i
                        break
                if content_start > 0:
                    revised_chapter = "\n".join(lines[content_start:])
                else:
                    revised_chapter = edited_response

            if revised_chapter:
                from libriscribe.utils.prose_sanitizer import sanitize_prose
                revised_chapter = sanitize_prose(revised_chapter)
                revised_chapter_path = str(Path(project_knowledge_base.project_dir) / f"chapter_{chapter_number}_revised.md")
                write_markdown_file(revised_chapter_path, revised_chapter)
                self.emit("log", {"level": "info", "message": f"Edited chapter {chapter_number} saved!"})
            else:
                self.emit("log", {"level": "error", "message": "Could not extract revised chapter from editor output."})
                self.logger.error(f"Raw editor response: {edited_response}")

        except Exception as e:
            self.logger.exception(f"Error editing chapter {chapter_path}: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to edit chapter: {e}"})

    def extract_chapter_number(self, chapter_path: str) -> int:
        try:
            return int(chapter_path.split("_")[1].split(".")[0])
        except Exception:
            return -1

    def extract_chapter_title(self, chapter_content: str) -> str:
        lines = chapter_content.split("\n")
        for line in lines:
            if line.startswith("#"):
                return line.replace("#", "").strip()
        return "Untitled Chapter"

    def extract_scene_markers(self, chapter_content: str) -> list[str]:
        """Extracts scene delimiter lines: '### Scene N' (current) or the legacy
        '**Scene X: ...**' bold titles still present in older chapter files."""
        import re
        markers = []
        for line in chapter_content.split("\n"):
            stripped = line.strip()
            if re.match(r'#{1,6}\s*Scene\s+\d+\s*$', stripped) or re.match(r'\*\*Scene\s+\d+:.*\*\*$', stripped):
                markers.append(stripped)
        return markers
