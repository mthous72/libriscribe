"""Per-entity lore analysis with suggestion generation.
Analyzes chapters to suggest entity updates. Per-entity, manual trigger."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libriscribe.knowledge_base import ProjectKnowledgeBase
    from libriscribe.utils.llm_client import LLMClient

from libriscribe.knowledge_base import CharacterState, ContinuityNote, LoreSuggestion

logger = logging.getLogger(__name__)

# ─── Prompts ─────────────────────────────────────────────────────

CHARACTER_ANALYSIS_PROMPT = """
Analyze how the character "{character_name}" has developed across the following chapter(s).

Current Character Profile:
{character_profile}

Previous Character State (as of Chapter {last_state_chapter}):
{previous_state}

Chapter Text(s):
{chapter_texts}

For each field below, compare the current profile/state with what happens in the chapters.
Return JSON with suggested updates ONLY for fields that have changed:

{{
  "field_updates": [
    {{
      "field": "emotional_state",
      "current_value": "...",
      "proposed_value": "...",
      "reason": "In Chapter X, the character..."
    }}
  ],
  "new_knowledge": ["list of new things the character learned"],
  "relationship_changes": {{"other_character": "new relationship status"}},
  "physical_state_update": null,
  "continuity_issues": []
}}

Only suggest changes that are clearly supported by the text. Do not speculate.
"""

LOCATION_ANALYSIS_PROMPT = """
Analyze how the location "{location_name}" has been depicted across the following chapter(s).

Current Location Profile:
{location_profile}

Chapter Text(s):
{chapter_texts}

Compare the current profile with what happens in the chapters.
Return JSON with suggested updates ONLY for fields that have changed:

{{
  "field_updates": [
    {{
      "field": "description",
      "current_value": "...",
      "proposed_value": "...",
      "reason": "In Chapter X, the location..."
    }}
  ],
  "new_associated_characters": [],
  "continuity_issues": []
}}

Only suggest changes that are clearly supported by the text. Do not speculate.
"""

LORE_ANALYSIS_PROMPT = """
Analyze how the lore entry "{entry_name}" relates to the following chapter(s).

Current Lore Entry:
{lore_profile}

Chapter Text(s):
{chapter_texts}

Compare the current entry with what happens in the chapters.
Return JSON with suggested updates ONLY for fields that have changed:

{{
  "field_updates": [
    {{
      "field": "description",
      "current_value": "...",
      "proposed_value": "...",
      "reason": "In Chapter X..."
    }}
  ],
  "new_related_entities": [],
  "continuity_issues": []
}}

Only suggest changes that are clearly supported by the text. Do not speculate.
"""

CONTINUITY_CHECK_PROMPT = """
Given the following character profiles, worldbuilding, and chapter texts,
identify any continuity errors, contradictions, or inconsistencies.

{context}

Return JSON:
{{
  "issues": [
    {{
      "note_type": "inconsistency",
      "description": "...",
      "entities_involved": ["..."],
      "chapter_number": 0
    }}
  ]
}}

Only report clear issues. Do not speculate or flag stylistic differences.
"""


class LoreSyncService:
    """Analyzes chapters to suggest entity updates. Per-entity, manual trigger."""

    def __init__(
        self,
        llm_client: LLMClient,
        kb: ProjectKnowledgeBase,
        project_dir: Path,
    ):
        self.llm_client = llm_client
        self.kb = kb
        self.project_dir = project_dir

    def _read_chapter_texts(
        self, chapter_range: tuple[int, int] | None = None
    ) -> dict[int, str]:
        """Reads chapter markdown files, optionally filtered by range."""
        texts: dict[int, str] = {}
        if not self.project_dir.exists():
            return texts

        for path in sorted(self.project_dir.glob("chapter_*.md")):
            filename = path.name
            if "revised" in filename or "original" in filename:
                continue
            parts = filename.split("_")
            try:
                ch_num = int(parts[1].split(".")[0])
            except (ValueError, IndexError):
                continue

            if chapter_range:
                if ch_num < chapter_range[0] or ch_num > chapter_range[1]:
                    continue

            try:
                texts[ch_num] = path.read_text(encoding="utf-8")
            except Exception:
                continue
        return texts

    def _chapters_with_character(
        self, character_name: str, chapter_range: tuple[int, int] | None = None
    ) -> dict[int, str]:
        """Returns chapter texts where the character name appears."""
        all_texts = self._read_chapter_texts(chapter_range)
        return {
            ch: text
            for ch, text in all_texts.items()
            if character_name.lower() in text.lower()
        }

    def _format_character_profile(self, char_name: str) -> str:
        char = self.kb.characters.get(char_name)
        if not char:
            return f"Character '{char_name}' not found in knowledge base."
        lines = [
            f"Name: {char.name}",
            f"Role: {char.role}",
            f"Personality: {char.personality_traits}",
            f"Background: {char.background}",
            f"Motivations: {char.motivations}",
            f"Internal Conflicts: {char.internal_conflicts}",
            f"External Conflicts: {char.external_conflicts}",
            f"Character Arc: {char.character_arc}",
        ]
        if char.relationships:
            for k, v in char.relationships.items():
                lines.append(f"Relationship with {k}: {v}")
        return "\n".join(lines)

    def _get_latest_state(self, char_name: str) -> tuple[int, str]:
        """Returns (chapter_number, formatted_state) for the latest state."""
        states = getattr(self.kb, "character_states", {}).get(char_name, [])
        if not states:
            return (0, "No previous state recorded.")
        latest = max(states, key=lambda s: s.chapter_number)
        parts = [f"Emotional State: {latest.emotional_state}"]
        if latest.knowledge:
            parts.append(f"Knows: {', '.join(latest.knowledge)}")
        if latest.relationships:
            for k, v in latest.relationships.items():
                parts.append(f"Relationship with {k}: {v}")
        if latest.physical_state:
            parts.append(f"Physical: {latest.physical_state}")
        return (latest.chapter_number, "\n".join(parts))

    def analyze_character(
        self,
        character_name: str,
        chapter_range: tuple[int, int] | None = None,
    ) -> list[LoreSuggestion]:
        """Analyzes chapters for a specific character, returns suggested updates."""
        relevant_texts = self._chapters_with_character(character_name, chapter_range)
        if not relevant_texts:
            return []

        profile = self._format_character_profile(character_name)
        last_ch, prev_state = self._get_latest_state(character_name)

        # Combine chapter texts (truncated)
        combined = ""
        for ch_num in sorted(relevant_texts.keys()):
            text = relevant_texts[ch_num]
            # Truncate each chapter to ~2000 words
            words = text.split()
            if len(words) > 2000:
                text = " ".join(words[:2000]) + "..."
            combined += f"\n--- Chapter {ch_num} ---\n{text}\n"

        prompt = CHARACTER_ANALYSIS_PROMPT.format(
            character_name=character_name,
            character_profile=profile,
            last_state_chapter=last_ch if last_ch else "N/A",
            previous_state=prev_state,
            chapter_texts=combined,
        )

        response = self.llm_client.generate_content_with_json_repair(
            prompt, max_tokens=2000
        )
        if not response:
            return []

        return self._parse_character_suggestions(
            character_name, response, max(relevant_texts.keys())
        )

    def _parse_character_suggestions(
        self, char_name: str, response: str, source_chapter: int
    ) -> list[LoreSuggestion]:
        """Parses LLM JSON response into LoreSuggestion objects."""
        suggestions: list[LoreSuggestion] = []
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse character analysis JSON")
            return []

        for update in data.get("field_updates", []):
            suggestions.append(
                LoreSuggestion(
                    entity_type="character",
                    entity_name=char_name,
                    field=update.get("field", ""),
                    current_value=str(update.get("current_value", "")),
                    proposed_value=str(update.get("proposed_value", "")),
                    reason=update.get("reason", ""),
                    source_chapter=source_chapter,
                )
            )

        # New knowledge -> character state suggestion
        new_knowledge = data.get("new_knowledge", [])
        if new_knowledge:
            suggestions.append(
                LoreSuggestion(
                    entity_type="character",
                    entity_name=char_name,
                    field="knowledge",
                    current_value="",
                    proposed_value=json.dumps(new_knowledge),
                    reason="New information learned by the character",
                    source_chapter=source_chapter,
                )
            )

        # Relationship changes
        rel_changes = data.get("relationship_changes", {})
        if rel_changes:
            for other, status in rel_changes.items():
                current_rel = self.kb.characters.get(char_name, None)
                current_val = ""
                if current_rel:
                    current_val = current_rel.relationships.get(other, "")
                suggestions.append(
                    LoreSuggestion(
                        entity_type="character",
                        entity_name=char_name,
                        field=f"relationship:{other}",
                        current_value=current_val,
                        proposed_value=str(status),
                        reason=f"Relationship with {other} changed",
                        source_chapter=source_chapter,
                    )
                )

        # Physical state
        phys = data.get("physical_state_update")
        if phys:
            suggestions.append(
                LoreSuggestion(
                    entity_type="character",
                    entity_name=char_name,
                    field="physical_state",
                    current_value="",
                    proposed_value=str(phys),
                    reason="Physical state change observed",
                    source_chapter=source_chapter,
                )
            )

        return suggestions

    def analyze_location(
        self,
        location_name: str,
        chapter_range: tuple[int, int] | None = None,
    ) -> list[LoreSuggestion]:
        """Analyzes chapters for a specific location."""
        all_texts = self._read_chapter_texts(chapter_range)
        relevant = {
            ch: text
            for ch, text in all_texts.items()
            if location_name.lower() in text.lower()
        }
        if not relevant:
            return []

        loc = self.kb.locations.get(location_name)
        if not loc:
            return []

        loc_profile = (
            f"Name: {loc.name}\nDescription: {loc.description}\n"
            f"Significance: {loc.significance}\n"
            f"Associated Characters: {', '.join(loc.associated_characters)}"
        )

        combined = ""
        for ch_num in sorted(relevant.keys()):
            text = relevant[ch_num]
            words = text.split()
            if len(words) > 2000:
                text = " ".join(words[:2000]) + "..."
            combined += f"\n--- Chapter {ch_num} ---\n{text}\n"

        prompt = LOCATION_ANALYSIS_PROMPT.format(
            location_name=location_name,
            location_profile=loc_profile,
            chapter_texts=combined,
        )

        response = self.llm_client.generate_content_with_json_repair(
            prompt, max_tokens=1500
        )
        if not response:
            return []

        return self._parse_location_suggestions(
            location_name, response, max(relevant.keys())
        )

    def _parse_location_suggestions(
        self, loc_name: str, response: str, source_chapter: int
    ) -> list[LoreSuggestion]:
        suggestions: list[LoreSuggestion] = []
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return []

        for update in data.get("field_updates", []):
            suggestions.append(
                LoreSuggestion(
                    entity_type="location",
                    entity_name=loc_name,
                    field=update.get("field", ""),
                    current_value=str(update.get("current_value", "")),
                    proposed_value=str(update.get("proposed_value", "")),
                    reason=update.get("reason", ""),
                    source_chapter=source_chapter,
                )
            )

        return suggestions

    def analyze_lore_entry(
        self,
        entry_name: str,
        chapter_range: tuple[int, int] | None = None,
    ) -> list[LoreSuggestion]:
        """Analyzes chapters for a specific lore entry."""
        all_texts = self._read_chapter_texts(chapter_range)
        relevant = {
            ch: text
            for ch, text in all_texts.items()
            if entry_name.lower() in text.lower()
        }
        if not relevant:
            return []

        entry = self.kb.lore_entries.get(entry_name)
        if not entry:
            return []

        lore_profile = (
            f"Name: {entry.name}\nType: {entry.entry_type}\n"
            f"Description: {entry.description}\n"
            f"Significance: {entry.significance}\n"
            f"Related Entities: {', '.join(entry.related_entities)}"
        )

        combined = ""
        for ch_num in sorted(relevant.keys()):
            text = relevant[ch_num]
            words = text.split()
            if len(words) > 2000:
                text = " ".join(words[:2000]) + "..."
            combined += f"\n--- Chapter {ch_num} ---\n{text}\n"

        prompt = LORE_ANALYSIS_PROMPT.format(
            entry_name=entry_name,
            lore_profile=lore_profile,
            chapter_texts=combined,
        )

        response = self.llm_client.generate_content_with_json_repair(
            prompt, max_tokens=1500
        )
        if not response:
            return []

        return self._parse_lore_suggestions(
            entry_name, response, max(relevant.keys())
        )

    def _parse_lore_suggestions(
        self, entry_name: str, response: str, source_chapter: int
    ) -> list[LoreSuggestion]:
        suggestions: list[LoreSuggestion] = []
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return []

        for update in data.get("field_updates", []):
            suggestions.append(
                LoreSuggestion(
                    entity_type="lore_entry",
                    entity_name=entry_name,
                    field=update.get("field", ""),
                    current_value=str(update.get("current_value", "")),
                    proposed_value=str(update.get("proposed_value", "")),
                    reason=update.get("reason", ""),
                    source_chapter=source_chapter,
                )
            )

        return suggestions

    def detect_continuity_issues(
        self, chapter_range: tuple[int, int] | None = None
    ) -> list[ContinuityNote]:
        """Scans chapter texts for inconsistencies against KB."""
        texts = self._read_chapter_texts(chapter_range)
        if not texts:
            return []

        # Build context from KB
        context_parts: list[str] = []

        # Characters
        for char in self.kb.characters.values():
            context_parts.append(self._format_character_profile(char.name))

        # Worldbuilding
        if self.kb.worldbuilding:
            for field, value in self.kb.worldbuilding.model_dump().items():
                if value and isinstance(value, str) and value.strip():
                    context_parts.append(f"{field}: {value}")

        # Chapter texts (truncated)
        for ch_num in sorted(texts.keys()):
            text = texts[ch_num]
            words = text.split()
            if len(words) > 1500:
                text = " ".join(words[:1500]) + "..."
            context_parts.append(f"--- Chapter {ch_num} ---\n{text}")

        context = "\n\n".join(context_parts)

        prompt = CONTINUITY_CHECK_PROMPT.format(context=context)
        response = self.llm_client.generate_content_with_json_repair(
            prompt, max_tokens=2000
        )
        if not response:
            return []

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return []

        notes: list[ContinuityNote] = []
        for issue in data.get("issues", []):
            notes.append(
                ContinuityNote(
                    chapter_number=issue.get("chapter_number", 0),
                    note_type=issue.get("note_type", "inconsistency"),
                    description=issue.get("description", ""),
                    entities_involved=issue.get("entities_involved", []),
                )
            )
        return notes

    def apply_suggestion(self, suggestion_index: int) -> None:
        """Applies an accepted suggestion to the KB."""
        suggestions = getattr(self.kb, "lore_suggestions", [])
        if suggestion_index < 0 or suggestion_index >= len(suggestions):
            return
        suggestion = suggestions[suggestion_index]
        suggestion.status = "accepted"

        if suggestion.entity_type == "character":
            self._apply_character_suggestion(suggestion)
        elif suggestion.entity_type == "location":
            self._apply_location_suggestion(suggestion)
        elif suggestion.entity_type == "lore_entry":
            self._apply_lore_suggestion(suggestion)

    def _apply_character_suggestion(self, suggestion: LoreSuggestion) -> None:
        char = self.kb.characters.get(suggestion.entity_name)
        if not char:
            return

        field = suggestion.field

        # Handle relationship fields
        if field.startswith("relationship:"):
            other_char = field.split(":", 1)[1]
            char.relationships[other_char] = suggestion.proposed_value
            return

        # Handle knowledge -> create/update character state
        if field == "knowledge":
            try:
                knowledge_list = json.loads(suggestion.proposed_value)
            except json.JSONDecodeError:
                knowledge_list = [suggestion.proposed_value]

            states = self.kb.character_states.setdefault(suggestion.entity_name, [])
            states.append(
                CharacterState(
                    character_name=suggestion.entity_name,
                    chapter_number=suggestion.source_chapter,
                    knowledge=knowledge_list,
                )
            )
            return

        # Handle character state fields
        if field in ("emotional_state", "physical_state"):
            states = self.kb.character_states.setdefault(suggestion.entity_name, [])
            # Check if there's already a state for this chapter
            existing = None
            for s in states:
                if s.chapter_number == suggestion.source_chapter:
                    existing = s
                    break
            if existing:
                setattr(existing, field, suggestion.proposed_value)
            else:
                new_state = CharacterState(
                    character_name=suggestion.entity_name,
                    chapter_number=suggestion.source_chapter,
                )
                setattr(new_state, field, suggestion.proposed_value)
                states.append(new_state)
            return

        # Direct character profile field
        if hasattr(char, field):
            setattr(char, field, suggestion.proposed_value)

    def _apply_location_suggestion(self, suggestion: LoreSuggestion) -> None:
        loc = self.kb.locations.get(suggestion.entity_name)
        if not loc:
            return
        if hasattr(loc, suggestion.field):
            setattr(loc, suggestion.field, suggestion.proposed_value)

    def _apply_lore_suggestion(self, suggestion: LoreSuggestion) -> None:
        entry = self.kb.lore_entries.get(suggestion.entity_name)
        if not entry:
            return
        if hasattr(entry, suggestion.field):
            setattr(entry, suggestion.field, suggestion.proposed_value)

    def reject_suggestion(self, suggestion_index: int) -> None:
        suggestions = getattr(self.kb, "lore_suggestions", [])
        if 0 <= suggestion_index < len(suggestions):
            suggestions[suggestion_index].status = "rejected"
