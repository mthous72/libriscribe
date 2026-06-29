"""Enhanced editor agent with external prompt support."""
import logging
from typing import Dict, Any
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.llm_client import LLMClient
from libriscribe.utils.prompt_integration import ExternalPromptMixin
from libriscribe.utils import prompts_context as prompts

logger = logging.getLogger(__name__)

class EnhancedEditorAgent(Agent, ExternalPromptMixin):
    """Editor agent with external prompt template support."""

    def __init__(self, llm_client: LLMClient, event_callback: EventCallback | None = None):
        Agent.__init__(self, "EnhancedEditorAgent", llm_client, event_callback=event_callback)
        ExternalPromptMixin.__init__(self)
    
    def execute(self, chapter_number: int, **kwargs) -> Dict[str, Any]:
        """Execute chapter editing with external prompts."""
        try:
            # Get chapter content and review data (simplified for demo)
            prompt_data = {
                "genre": kwargs.get("genre", "fiction"),
                "book_title": kwargs.get("book_title", "Untitled"),
                "language": kwargs.get("language", "English"),
                "chapter_number": chapter_number,
                "chapter_title": f"Chapter {chapter_number}",
                "chapter_content": kwargs.get("chapter_content", "Sample content..."),
                "review_feedback": kwargs.get("review_feedback", "No specific feedback.")
            }
            
            self.emit("log", {"level": "info", "message": f"Editing Chapter {chapter_number} with external prompts..."})
            
            # Use external prompt with fallback to hardcoded
            edited_content = self.generate_with_external_prompt(
                prompt_name="editor",
                fallback_prompt=prompts.EDITOR_PROMPT,
                prompt_data=prompt_data,
                default_max_tokens=8000
            )
            
            self.emit("log", {"level": "info", "message": f"Chapter {chapter_number} edited successfully"})
            return {"edited_content": edited_content}
            
        except Exception as e:
            logger.exception(f"Error editing chapter {chapter_number}: {e}")
            return {"error": str(e)}
