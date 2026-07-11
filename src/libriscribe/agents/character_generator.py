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

            # B42: ground in the author's lore (Phase-0 pattern, extended to this stage).
            # Existing characters are established canon — the model must build AROUND them.
            existing_names = [n for n in project_knowledge_base.characters.keys() if n.strip()]
            if existing_names:
                prompt = (
                    "=== EXISTING CHARACTERS (established by the author — do NOT recreate, rename, "
                    "or redefine them; create only NEW characters that complete the cast around "
                    f"them) ===\n{', '.join(existing_names)}\n\n{prompt}"
                )
            from libriscribe.services.lore_digest import grounding_block
            lore = grounding_block(project_knowledge_base)
            if lore:
                prompt = f"{lore}\n\n{prompt}"

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
                staged_updates = []
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
                            sex=flattened_char_data.get("sex", "") or flattened_char_data.get("gender", ""),
                            sexual_orientation=flattened_char_data.get("sexual orientation", "") or flattened_char_data.get("sexual_orientation", ""),
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
                            # B42: NEVER overwrite an author-established character. The
                            # generated variant becomes a pending sandbox suggestion the
                            # author can review and accept — or ignore.
                            staged_updates.append(character)
                            self.emit("log", {"level": "info", "message": (
                                f"'{character.name}' already exists in the lorebook — staged the "
                                "generated profile as a suggestion (not applied)."
                            )})
                            continue

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
            if staged_updates:
                self._stage_character_suggestions(project_knowledge_base, staged_updates)

            if output_path is None:
                output_path = str(Path(project_knowledge_base.project_dir) / "characters.json")
            write_json_file(output_path, processed_characters)
            self.emit("log", {"level": "info", "message": "Character profiles saved!"})

        except Exception as e:
            self.logger.exception(f"Error generating character profiles: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to generate character profiles: {e}"})

    def _stage_character_suggestions(self, pkb: ProjectKnowledgeBase, characters: list[Character]) -> None:
        """B42: name collisions land in the B27 sandbox as pending update-candidates —
        applied only when the author explicitly accepts them (never auto)."""
        try:
            from libriscribe.services import sandbox

            candidates = []
            for ch in characters:
                fields = {
                    k: v for k, v in ch.model_dump().items()
                    if k not in ("name", "voice_profile", "relationships")
                    and isinstance(v, str) and v.strip()
                }
                candidates.append(sandbox.new_candidate(
                    "characters", ch.name, fields, op="update",
                    source="character_generator",
                    rationale="Generation produced a profile for an existing lorebook character.",
                ))
            if candidates:
                run = sandbox.create_run(
                    pkb.project_name, {"kind": "generation_characters"}, candidates)
                self.emit("log", {"level": "info", "message": (
                    f"{len(candidates)} character suggestion(s) staged for review "
                    f"(sandbox run {run['id']})."
                )})
        except Exception as e:
            logger.warning(f"Failed to stage character suggestions: {e}")

    def _generate_voice_profile(self, character: Character, pkb: ProjectKnowledgeBase) -> None:
        """Generates and ATTACHES a voice profile (batch path). The reusable single-character
        primitive lives at module level (B45: also exposed as a per-character lore action)."""
        try:
            vp = generate_voice_profile(self.llm_client, character, pkb)
            if vp is None:
                return
            character.voice_profile = vp
            self.emit("log", {"level": "info", "message": f"Generated voice profile for {character.name}"})
        except Exception as e:
            logger.warning(f"Failed to generate voice profile for {character.name}: {e}")


def generate_voice_profile(llm_client, character: Character, pkb: ProjectKnowledgeBase) -> VoiceProfile | None:
    """One LLM call → a VoiceProfile for one character. Returns None on failure; never saves."""
    prompt = f"""Create a dialogue voice profile for the character "{character.name}" from the {pkb.genre} book "{pkb.title}".

Character details:
- Role: {character.role}
- Age: {character.age}
- Sex: {character.sex}
- Sexual orientation: {character.sexual_orientation}
- Personality: {character.personality_traits}
- Background: {character.background}

Return a JSON object with these fields:
- speech_patterns: How they structure sentences (e.g., "short clipped sentences", "formal with subordinate clauses", "rambling with digressions")
- vocabulary_level: Their word choice level (e.g., "street slang", "academic", "simple and direct", "archaic formal")
- verbal_tics: Recurring speech habits (e.g., "says 'right?' after statements", "clears throat before speaking", "uses nautical metaphors")
- avoids: Words or patterns this character would NEVER use (e.g., "never swears", "avoids contractions", "never uses slang")
- example_dialogue: Array of 2-3 example lines this character might say, demonstrating their voice

Return ONLY valid JSON, no markdown wrapper."""

    response = llm_client.generate_content_with_json_repair(prompt, max_tokens=1000, temperature=0.6)
    if not response:
        return None
    voice_data = extract_json_from_markdown(response)
    if not voice_data or not isinstance(voice_data, dict):
        return None
    return VoiceProfile(
        speech_patterns=voice_data.get("speech_patterns", ""),
        vocabulary_level=voice_data.get("vocabulary_level", ""),
        verbal_tics=voice_data.get("verbal_tics", ""),
        avoids=voice_data.get("avoids", ""),
        example_dialogue=voice_data.get("example_dialogue", []),
    )
