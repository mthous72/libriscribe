# src/libriscribe/agents/character_generator.py

import json
import logging
from typing import Optional
from pathlib import Path

from libriscribe.utils.llm_client import LLMClient
from libriscribe.utils import prompts_context as prompts
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.file_utils import write_json_file, extract_json_from_markdown

from libriscribe.knowledge_base import ProjectKnowledgeBase, Character, VoiceProfile

logger = logging.getLogger(__name__)

class CharacterGeneratorAgent(Agent):
    """Generates character profiles."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("CharacterGeneratorAgent", llm_client, event_callback)

    def execute(self, project_knowledge_base: ProjectKnowledgeBase, output_path: Optional[str] = None) -> None:
        try:
            self.emit("log", {"level": "info", "message": "Creating character profiles..."})
            prompt = prompts.CHARACTER_PROMPT.format(
                title=project_knowledge_base.title,
                genre=project_knowledge_base.genre,
                category=project_knowledge_base.category,
                language=project_knowledge_base.language,
                description=project_knowledge_base.description,
                num_characters=project_knowledge_base.num_characters
            )

            character_json_str = self.llm_client.generate_content_with_json_repair(prompt, max_tokens=4000, temperature=0.5)

            if not character_json_str:
                self.emit("log", {"level": "error", "message": "Character generation failed."})
                return
            try:
                characters = extract_json_from_markdown(character_json_str)
                if not characters or not isinstance(characters, list):
                    self.emit("log", {"level": "error", "message": "Failed to parse character data."})
                    return

                processed_characters = []
                for char_data in characters:
                    try:
                        char_data = {k.lower(): v for k, v in char_data.items()}

                        relationships = char_data.get("relationships", {}) or char_data.get("relationships with other characters", {})
                        if isinstance(relationships, str):
                            relationships = {"general": relationships}
                        elif isinstance(relationships, dict):
                            flattened_relationships = {}
                            for rel_key, rel_value in relationships.items():
                                if isinstance(rel_value, str):
                                    flattened_relationships[rel_key] = rel_value
                                elif isinstance(rel_value, dict):
                                    flat_rel_value = ""
                                    for sub_key, sub_value in rel_value.items():
                                        if isinstance(sub_value,str):
                                            flat_rel_value += f"{sub_key}: {sub_value} "
                                        else:
                                            flat_rel_value += f"{sub_key}: {json.dumps(sub_value)} "
                                    flattened_relationships[rel_key] = flat_rel_value.strip()
                                else:
                                    flattened_relationships[rel_key] = json.dumps(rel_value)
                            relationships = flattened_relationships

                        flattened_char_data = {}
                        for key, value in char_data.items():
                            if isinstance(value, dict) and key != "relationships":
                                flattened_value = ""
                                for sub_key, sub_value in value.items():
                                    if isinstance(sub_value,str):
                                        flattened_value += f"{sub_key}: {sub_value} "
                                    else:
                                        flattened_value += f"{sub_key} : {json.dumps(sub_value)} "
                                flattened_char_data[key] = flattened_value.strip()

                            elif isinstance(value, str):
                                flattened_char_data[key] = value
                            elif isinstance(value, list):
                                flattened_char_data[key] = [item.strip() if isinstance(item, str) else item for item in value]
                            else:
                                flattened_char_data[key] = json.dumps(value)

                        personality_traits = flattened_char_data.get("personality_traits", "")

                        if isinstance(personality_traits, list):
                            personality_traits = ", ".join([str(trait).strip() for trait in personality_traits if trait])
                        elif isinstance(personality_traits, str):
                            personality_traits = personality_traits.strip()

                        if not personality_traits:
                            personality_traits = "Resourceful, Cautious, Determined"

                        character = Character(
                            name=flattened_char_data.get("name", ""),
                            age=str(flattened_char_data.get("age", "")),
                            physical_description=flattened_char_data.get("physical description", ""),
                            personality_traits=personality_traits,
                            background=flattened_char_data.get("background", "") or flattened_char_data.get("background/backstory", ""),
                            motivations=flattened_char_data.get("motivations", ""),
                            relationships=relationships,
                            role=flattened_char_data.get("role", "") or flattened_char_data.get("role in the story", ""),
                            internal_conflicts=flattened_char_data.get("internal conflicts", "") or flattened_char_data.get("internal_conflicts", ""),
                            external_conflicts=flattened_char_data.get("external conflicts", "") or flattened_char_data.get("external_conflicts", ""),
                            character_arc=flattened_char_data.get("character arc", "") or flattened_char_data.get("character_arc", ""),
                        )

                        existing_character = project_knowledge_base.get_character(character.name)
                        if existing_character:
                            for key, value in character.model_dump().items():
                                if hasattr(existing_character, key):
                                    setattr(existing_character, key, value)
                        else:
                            project_knowledge_base.add_character(character)

                        # Generate voice profile for this character
                        self._generate_voice_profile(character, project_knowledge_base)

                        processed_characters.append(character.model_dump())
                        self.emit("log", {"level": "info", "message": f"Created character: {character.name}"})

                    except Exception as e:
                        logger.warning(f"Skipping a character due to error: {str(e)}")
                        continue
            except json.JSONDecodeError:
                self.emit("log", {"level": "error", "message": "Invalid JSON data received after repair attempts."})
                return
            except Exception as e:
                self.emit("log", {"level": "error", "message": f"Error processing characters: {e}"})
                return
            if output_path is None:
                output_path = str(Path(project_knowledge_base.project_dir) / "characters.json")
            write_json_file(output_path, processed_characters)
            self.emit("log", {"level": "info", "message": "Character profiles saved!"})

        except Exception as e:
            self.logger.exception(f"Error generating character profiles: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to generate character profiles: {e}"})

    def _generate_voice_profile(self, character: Character, pkb: ProjectKnowledgeBase) -> None:
        """Generates a voice profile for a character using an LLM call."""
        try:
            prompt = f"""Create a dialogue voice profile for the character "{character.name}" from the {pkb.genre} book "{pkb.title}".

Character details:
- Role: {character.role}
- Age: {character.age}
- Personality: {character.personality_traits}
- Background: {character.background}

Return a JSON object with these fields:
- speech_patterns: How they structure sentences (e.g., "short clipped sentences", "formal with subordinate clauses", "rambling with digressions")
- vocabulary_level: Their word choice level (e.g., "street slang", "academic", "simple and direct", "archaic formal")
- verbal_tics: Recurring speech habits (e.g., "says 'right?' after statements", "clears throat before speaking", "uses nautical metaphors")
- avoids: Words or patterns this character would NEVER use (e.g., "never swears", "avoids contractions", "never uses slang")
- example_dialogue: Array of 2-3 example lines this character might say, demonstrating their voice

Return ONLY valid JSON, no markdown wrapper."""

            response = self.llm_client.generate_content_with_json_repair(prompt, max_tokens=1000, temperature=0.6)
            if not response:
                return

            voice_data = extract_json_from_markdown(response)
            if not voice_data or not isinstance(voice_data, dict):
                return

            character.voice_profile = VoiceProfile(
                speech_patterns=voice_data.get("speech_patterns", ""),
                vocabulary_level=voice_data.get("vocabulary_level", ""),
                verbal_tics=voice_data.get("verbal_tics", ""),
                avoids=voice_data.get("avoids", ""),
                example_dialogue=voice_data.get("example_dialogue", []),
            )
            self.emit("log", {"level": "info", "message": f"Generated voice profile for {character.name}"})
        except Exception as e:
            logger.warning(f"Failed to generate voice profile for {character.name}: {e}")
