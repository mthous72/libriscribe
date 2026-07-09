# src/libriscribe/agents/style_editor.py

import logging
from pathlib import Path
from typing import Optional

from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.llm_client import LLMClient
from libriscribe.utils.file_utils import read_markdown_file, write_markdown_file

from libriscribe.knowledge_base import ProjectKnowledgeBase

logger = logging.getLogger(__name__)

class StyleEditorAgent(Agent):
    """Refines the writing style of a chapter."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("StyleEditorAgent", llm_client, event_callback)

    def execute(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int) -> None:
        """Refines style based on project settings."""
        chapter_path = str(Path(project_knowledge_base.project_dir) / f"chapter_{chapter_number}.md")
        chapter_content = read_markdown_file(chapter_path)
        if not chapter_content:
            self.emit("log", {"level": "error", "message": f"Chapter file is empty or not found: {chapter_path}"})
            return

        tone = getattr(project_knowledge_base, 'tone', 'Informative')
        target_audience = getattr(project_knowledge_base, 'target_audience', 'General')

        self.emit("log", {"level": "info", "message": f"Polishing writing style for Chapter {chapter_number}..."})
        prompt = f"""
        You are a style editor. Refine the writing style of the following chapter excerpt...

        Target Tone: {tone}
        Target Audience: {target_audience}
        Language: {project_knowledge_base.language}

        Make specific suggestions for changes, and then provide the REVISED text within a Markdown code block.

        ```markdown
        [The full revised chapter content]
        ```

        Chapter Excerpt:
        ---
        {chapter_content}
        ---
        """
        # Same steering stack as the draft — and enough output budget for a FULL chapter
        # (3000 tokens truncated 3-6k-token chapters mid-rewrite).
        from libriscribe.utils.prose_steering import steering_blocks, writing_system_prompt
        steer = steering_blocks(project_knowledge_base)
        if steer:
            prompt = (
                f"{steer}\n\nPRESERVE THE REGISTER: keep the intensity, register, and "
                f"explicitness of the original — polish the style WITHOUT toning it down.\n\n{prompt}"
            )
        try:
            response = self.llm_client.generate_content(
                prompt, max_tokens=8000,
                system_prompt=writing_system_prompt(project_knowledge_base),
            )

            if "```" in response:
                start = response.find("```") + 3
                end = response.rfind("```")
                next_newline = response.find("\n", start)
                if next_newline < end and next_newline != -1:
                    start = next_newline + 1
                revised_text = response[start:end].strip()
            else:
                lines = response.split("\n")
                content_start = 0
                for i, line in enumerate(lines):
                    if line.startswith("#") or line.startswith("Chapter"):
                        content_start = i
                        break
                if content_start > 0:
                    revised_text = "\n".join(lines[content_start:])
                else:
                    revised_text = response

            if revised_text:
                write_markdown_file(chapter_path, revised_text)
                self.emit("log", {"level": "info", "message": f"Style improvements applied to Chapter {chapter_number}!"})
            else:
                self.emit("log", {"level": "error", "message": f"Could not extract revised text for {chapter_path}."})

        except Exception as e:
            self.logger.exception(f"Error during style editing for {chapter_path}: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to edit style for chapter {chapter_path}: {e}"})
