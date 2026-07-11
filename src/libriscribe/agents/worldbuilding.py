# src/libriscribe/agents/worldbuilding.py

import json
import logging
from typing import Optional
from pathlib import Path

from libriscribe.utils.llm_client import LLMClient
from libriscribe.utils import prompts_context as prompts
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.file_utils import write_json_file, extract_json_from_markdown
from libriscribe.utils.prompts_context import get_worldbuilding_aspects

from libriscribe.knowledge_base import ProjectKnowledgeBase, Worldbuilding

logger = logging.getLogger(__name__)

class WorldbuildingAgent(Agent):
    """Generates worldbuilding details."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("WorldbuildingAgent", llm_client, event_callback)

    def execute(self, project_knowledge_base: ProjectKnowledgeBase, output_path: Optional[str] = None) -> None:
        try:
            if not project_knowledge_base.worldbuilding_needed:
                self.emit("log", {"level": "info", "message": "Worldbuilding not needed for this project. Skipping."})
                return

            if project_knowledge_base.worldbuilding is None:
                project_knowledge_base.worldbuilding = Worldbuilding()

            aspects = get_worldbuilding_aspects(project_knowledge_base.category)
            self.emit("log", {"level": "info", "message": "Creating world details..."})
            prompt = prompts.WORLDBUILDING_PROMPT.format(
                worldbuilding_aspects=aspects,
                title=project_knowledge_base.title,
                genre=project_knowledge_base.genre,
                category=project_knowledge_base.category,
                language=project_knowledge_base.language,
                description=project_knowledge_base.description
            )

            # B42: ground in the author's established lore (Phase-0 pattern).
            from libriscribe.services.lore_digest import grounding_block
            lore = grounding_block(project_knowledge_base)
            if lore:
                prompt = f"{lore}\n\n{prompt}"

            worldbuilding_json_str = self.llm_client.generate_content_with_json_repair(prompt, max_tokens=4000, temperature=0.7)
            if not worldbuilding_json_str:
                self.emit("log", {"level": "error", "message": "Worldbuilding generation failed."})
                return

            try:
                worldbuilding_data = extract_json_from_markdown(worldbuilding_json_str)
                if worldbuilding_data is None:
                    self.emit("log", {"level": "error", "message": "Invalid worldbuilding data received (could not extract JSON)."})
                    return

                if not isinstance(worldbuilding_data, dict):
                    self.logger.warning("Worldbuilding data is not a dictionary.")
                    worldbuilding_data = {}

                flattened_data = {}
                for key, value in worldbuilding_data.items():
                    if isinstance(value, dict):
                        flattened_value = ""
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str):
                                flattened_value += f"{sub_value} "
                            else:
                                flattened_value += f"{json.dumps(sub_value)} "
                        flattened_data[key] = flattened_value.strip()
                    elif isinstance(value, str):
                        flattened_data[key] = value
                    else:
                        flattened_data[key] = json.dumps(value)

                if project_knowledge_base.category.lower() == "fiction":
                    expected_fields = [
                        "geography", "culture_and_society", "history", "rules_and_laws",
                        "technology_level", "magic_system", "key_locations",
                        "important_organizations", "flora_and_fauna", "languages",
                        "religions_and_beliefs", "economy", "conflicts"
                    ]
                elif project_knowledge_base.category.lower() == "non-fiction":
                    expected_fields = [
                        "setting_context", "key_figures", "major_events", "underlying_causes",
                        "consequences", "relevant_data", "different_perspectives",
                        "key_concepts"
                    ]
                elif project_knowledge_base.category.lower() == "business":
                    expected_fields = [
                        "industry_overview", "target_audience", "market_analysis",
                        "business_model", "marketing_and_sales_strategy", "operations",
                        "financial_projections", "management_team",
                        "legal_and_regulatory_environment", "risks_and_challenges",
                        "opportunities_for_growth"
                    ]
                elif project_knowledge_base.category.lower() == "research paper":
                    expected_fields = [
                        "introduction", "literature_review", "methodology", "results",
                        "discussion", "conclusion", "references", "appendices"
                    ]
                else:
                    expected_fields = []

                clean_worldbuilding = Worldbuilding()

                for key, value in flattened_data.items():
                    normalized_key = key.lower().replace(" ", "_")
                    if normalized_key in expected_fields:
                        if isinstance(value, str) and value.strip():
                            setattr(clean_worldbuilding, normalized_key, value)
                    else:
                        logger.debug(f"Ignoring unexpected field: {key}")

                # B42: NEVER overwrite the author's worldbuilding (this used to replace the
                # whole object). Generated values fill EMPTY fields directly; fields the
                # author already wrote become pending sandbox suggestions instead.
                existing = project_knowledge_base.worldbuilding
                conflicts: dict[str, str] = {}
                filled = 0
                for key in expected_fields:
                    new_val = str(getattr(clean_worldbuilding, key, "") or "").strip()
                    if not new_val:
                        continue
                    current = str(getattr(existing, key, "") or "").strip()
                    if not current:
                        setattr(existing, key, new_val)
                        filled += 1
                    elif current != new_val:
                        conflicts[key] = new_val

                if conflicts:
                    self._stage_worldbuilding_suggestions(project_knowledge_base, conflicts)
                self.emit("log", {"level": "info", "message": (
                    f"World elements created ({filled} field(s) filled"
                    + (f", {len(conflicts)} suggestion(s) staged for review" if conflicts else "")
                    + ")"
                )})
                for key, value in project_knowledge_base.worldbuilding.model_dump().items():
                    if value and isinstance(value, str) and value.strip():
                        self.emit("log", {"level": "info", "message": f"  {key.replace('_', ' ').title()}: {value[:100]}..."})

                if output_path is None:
                    output_path = str(Path(project_knowledge_base.project_dir) / "world.json")

                cleaned_data = {k: v for k, v in project_knowledge_base.worldbuilding.model_dump().items()
                            if k in expected_fields and v}
                write_json_file(output_path, cleaned_data)
                self.emit("log", {"level": "info", "message": "Worldbuilding details generated!"})

            except json.JSONDecodeError:
                self.emit("log", {"level": "error", "message": "Invalid JSON data received from LLM after repair attempts."})
                return
            except Exception as e:
                self.emit("log", {"level": "error", "message": f"Error: {e}"})
                return

        except Exception as e:
            self.logger.exception(f"Error generating worldbuilding details: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to generate worldbuilding details: {e}"})

    def _stage_worldbuilding_suggestions(self, pkb: ProjectKnowledgeBase, conflicts: dict[str, str]) -> None:
        """B42: generated values for fields the author already wrote become ONE pending
        sandbox candidate — applied only on explicit acceptance, never automatically."""
        try:
            from libriscribe.services import sandbox

            candidate = sandbox.new_candidate(
                "worldbuilding", "Worldbuilding", conflicts, op="update",
                source="worldbuilding_generator",
                rationale=(
                    "Generation produced new content for worldbuilding fields the author "
                    "already filled: " + ", ".join(sorted(conflicts))
                ),
            )
            run = sandbox.create_run(pkb.project_name, {"kind": "generation_worldbuilding"}, [candidate])
            self.emit("log", {"level": "info", "message": (
                f"{len(conflicts)} worldbuilding suggestion(s) staged for review "
                f"(sandbox run {run['id']})."
            )})
        except Exception as e:
            logger.warning(f"Failed to stage worldbuilding suggestions: {e}")
