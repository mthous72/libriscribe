# src/libriscribe/agents/concept_generator.py
import logging
from typing import Optional

from libriscribe.utils.llm_client import LLMClient
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.file_utils import extract_json_from_markdown
from libriscribe.knowledge_base import ProjectKnowledgeBase

logger = logging.getLogger(__name__)


class ConceptGeneratorAgent(Agent):
    """Generates book concepts."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("ConceptGeneratorAgent", llm_client, event_callback)

    def execute(
        self,
        project_knowledge_base: ProjectKnowledgeBase,
        output_path: Optional[str] = None,
    ) -> None:
        """Generates a book concept, with critique and refinement."""
        try:
            # Phase 0b: ground the concept in the author's established lore (if any) so it
            # extends THEIR world instead of inventing one. Empty lorebook -> no block.
            from libriscribe.services.lore_digest import grounding_block

            lore_block = grounding_block(project_knowledge_base)

            # --- Step 1: Initial Concept Generation (Simplified) ---
            if project_knowledge_base.book_length == "Short Story":
                initial_prompt = f"""Generate a concise book concept for a {project_knowledge_base.genre} {project_knowledge_base.category} short story.
                    The book should be written in {project_knowledge_base.language}.

                    Initial ideas: {project_knowledge_base.description}.

                    Return a JSON object within a Markdown code block.  Include:
                    - "title":  A compelling title.
                    - "logline": A one-sentence summary.
                    - "description": A short description (around 100-150 words).

                    ```json
                    {{{{
                        "title": "...",
                        "logline": "...",
                        "description": "..."
                    }}}}
                    ```"""
            else:
                initial_prompt = f"""Generate a book concept for a {project_knowledge_base.genre} {project_knowledge_base.category} ({project_knowledge_base.book_length}).
                The book should be written in {project_knowledge_base.language}.

                Initial ideas: {project_knowledge_base.description}.

                Return a JSON object within a Markdown code block. Include:
                - "title": A title.
                - "logline": A one-sentence summary.
                - "description": A description (around 200 words).

                ```json
                {{{{{{{{
                    "title": "...",
                    "logline": "...",
                    "description": "..."
                }}}}}}}}
                ```"""

            if lore_block:
                initial_prompt = f"{lore_block}\n\n{initial_prompt}"

            self.emit("log", {"level": "info", "message": "Generating initial concept..."})
            initial_concept_md = self.llm_client.generate_content_with_json_repair(
                initial_prompt
            )

            if not initial_concept_md:
                logger.error("Initial concept generation failed.")
                return None

            initial_concept_json = extract_json_from_markdown(initial_concept_md)
            if not initial_concept_json:
                logger.error("Initial concept parsing failed.")
                return None

            # --- Step 2: Critique the Concept ---
            critique_prompt = f"""Critique the following book concept:

            ```json
            {{{{json.dumps(initial_concept_json)}}}}
            ```
            The book should be written in {project_knowledge_base.language}.

            Evaluate:
            - **Title:** Is it compelling and relevant?
            - **Logline:** Is it concise and does it capture the core conflict?
            - **Description:** Is it well-written, engaging, and does it provide a clear sense of the story?  Are there any obvious weaknesses or areas for improvement? Be specific and constructive.
            """
            self.emit("log", {"level": "info", "message": "Evaluating concept quality..."})
            critique = self.llm_client.generate_content(critique_prompt)
            if not critique:
                logger.error("Critique generation failed.")
                return None

            # --- Step 3: Refine the Concept ---
            refine_prompt = f"""Refine the book concept based on the critique.  Address the weaknesses and improve the concept.
            The book should be written in {project_knowledge_base.language}.

            Original Concept:
            ```json
            {{{{json.dumps(initial_concept_json)}}}}
            ```

            Critique:
            {critique}

            Return the REFINED concept as a JSON object within a Markdown code block:
             ```json
            {{{{{{{{
                "title": "...",
                "logline": "...",
                "description": "..."
            }}}}}}}}
            ```
            """
            if lore_block:
                refine_prompt = f"{lore_block}\n\n{refine_prompt}"
            self.emit("log", {"level": "info", "message": "Refining concept..."})
            refined_concept_md = self.llm_client.generate_content_with_json_repair(
                refine_prompt
            )
            if not refined_concept_md:
                logger.error("Refined concept generation failed.")
                return None

            refined_concept_json = extract_json_from_markdown(refined_concept_md)
            if not refined_concept_json:
                logger.error("Refined concept parsing failed")
                return None

            # --- Step 4: SUGGEST (never overwrite) the user's title/logline/description (Phase 0) ---
            # The author's title/logline/description are theirs; the concept stage only proposes.
            # The UI surfaces suggested_* with an Apply button.
            if refined_concept_json.get("title"):
                project_knowledge_base.suggested_title = refined_concept_json["title"]
            if refined_concept_json.get("logline"):
                project_knowledge_base.suggested_logline = refined_concept_json["logline"]
            if refined_concept_json.get("description"):
                project_knowledge_base.suggested_description = refined_concept_json["description"]

            logger.info(
                "Concept generated (refined) — suggested title: %s, suggested logline: %s",
                project_knowledge_base.suggested_title, project_knowledge_base.suggested_logline,
            )

        except Exception as e:
            self.logger.exception(f"Error generating concept: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to generate concept: {e}"})
            return None
