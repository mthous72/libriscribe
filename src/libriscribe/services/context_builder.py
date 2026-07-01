"""Context assembly for scene prompts — injects character profiles, worldbuilding,
location details, lore entries, previous chapter summaries, and retrieval results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from libriscribe.utils.token_utils import estimate_tokens

if TYPE_CHECKING:
    from libriscribe.knowledge_base import (
        Chapter,
        ProjectKnowledgeBase,
        Scene,
    )

logger = logging.getLogger(__name__)


class TokenBudget:
    """Tracks remaining token budget for context assembly."""

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.used = 0

    def remaining(self) -> int:
        return self.max_tokens - self.used

    def consume(self, text: str) -> str:
        """Returns text truncated to fit budget, updates used count."""
        est_tokens = estimate_tokens(text)
        if est_tokens <= self.remaining():
            self.used += est_tokens
            return text
        allowed_words = int(self.remaining() / 1.3)
        if allowed_words <= 0:
            return ""
        truncated = " ".join(text.split()[:allowed_words])
        self.used = self.max_tokens
        return truncated + "..."

    def exhausted(self) -> bool:
        return self.used >= self.max_tokens


class ContextBuilder:
    """Assembles a rich context block for each scene prompt."""

    MAX_CONTEXT_TOKENS = 2000

    def __init__(self, kb: ProjectKnowledgeBase, search_service=None):
        self.kb = kb
        self.search_service = search_service

    def build_scene_context(
        self, chapter_number: int, scene: Scene, chapter: Chapter
    ) -> str:
        budget = TokenBudget(self.MAX_CONTEXT_TOKENS)

        # Reserve a bounded slice for imported reference material (B19) first, so it isn't
        # crowded out by canon context; it is appended last (background source material).
        reference_section = self._build_reference_context(scene, budget, max_ref_tokens=450)

        sections: list[str] = []

        # Priority order (highest first):
        sections.append(self._build_character_profiles(scene.characters, budget))
        sections.append(self._build_chapter_recaps(chapter_number, budget))
        sections.append(self._build_location_context(scene.setting, budget))
        sections.append(self._build_worldbuilding_context(budget))
        sections.append(self._build_lore_context(scene, budget))
        sections.append(self._build_arc_context(chapter_number, budget))
        sections.append(self._build_thread_context(scene.characters, chapter_number, budget))
        sections.append(self._build_character_states(scene.characters, chapter_number, budget))
        sections.append(self._build_retrieval_context(scene, chapter_number, budget))
        sections.append(reference_section)

        return "\n\n".join(s for s in sections if s)

    def _build_character_profiles(
        self, character_names: list[str], budget: TokenBudget
    ) -> str:
        if budget.exhausted() or not character_names:
            return ""

        profiles: list[str] = []
        for char_name in character_names:
            char = self.kb.characters.get(char_name)
            if not char:
                continue

            lines = [f"**{char.name}** ({char.role})"]
            if char.personality_traits:
                lines.append(f"  Personality: {char.personality_traits}")
            if char.motivations:
                lines.append(f"  Motivations: {char.motivations}")
            if char.background:
                # Truncate background to ~2 sentences
                bg_sentences = char.background.split(".")
                short_bg = ".".join(bg_sentences[:2]).strip()
                if short_bg:
                    lines.append(f"  Background: {short_bg}.")

            # Show relationships with other scene characters
            relevant_rels = {
                k: v for k, v in char.relationships.items() if k in character_names
            }
            if relevant_rels:
                rel_strs = [f"{k}: {v}" for k, v in relevant_rels.items()]
                lines.append(f"  Relationships: {'; '.join(rel_strs)}")

            # Voice profile (F3)
            vp = getattr(char, "voice_profile", None)
            if vp:
                if vp.speech_patterns:
                    lines.append(f"  Speech: {vp.speech_patterns}")
                if vp.vocabulary_level:
                    lines.append(f"  Vocabulary: {vp.vocabulary_level}")
                if vp.verbal_tics:
                    lines.append(f"  Verbal tics: {vp.verbal_tics}")
                if vp.avoids:
                    lines.append(f"  Avoids: {vp.avoids}")
                if vp.example_dialogue:
                    lines.append(f"  Sample dialogue: {' | '.join(vp.example_dialogue[:2])}")

            profiles.append("\n".join(lines))

        if not profiles:
            return ""

        section = "=== CHARACTER PROFILES ===\n" + "\n\n".join(profiles)
        return budget.consume(section)

    def _build_chapter_recaps(
        self, chapter_number: int, budget: TokenBudget
    ) -> str:
        if budget.exhausted():
            return ""

        recaps: list[str] = []
        start = max(1, chapter_number - 3)
        for ch_num in range(start, chapter_number):
            ch = self.kb.chapters.get(ch_num)
            if ch and ch.summary and ch.summary.strip():
                recaps.append(f"Chapter {ch_num} ({ch.title}): {ch.summary}")

        if not recaps:
            return ""

        section = "=== PREVIOUS CHAPTERS ===\n" + "\n".join(recaps)
        return budget.consume(section)

    def _build_location_context(
        self, setting: str, budget: TokenBudget
    ) -> str:
        if budget.exhausted() or not setting:
            return ""

        # Fuzzy match: check if setting string contains any location name or vice versa
        setting_lower = setting.lower()
        matched_location = None
        for loc_name, loc in self.kb.locations.items():
            if loc_name.lower() in setting_lower or setting_lower in loc_name.lower():
                matched_location = loc
                break

        if not matched_location:
            return ""

        lines = [f"**{matched_location.name}**"]
        if matched_location.description:
            lines.append(f"  {matched_location.description}")
        if matched_location.significance:
            lines.append(f"  Significance: {matched_location.significance}")
        if matched_location.associated_characters:
            lines.append(
                f"  Associated Characters: {', '.join(matched_location.associated_characters)}"
            )

        section = "=== LOCATION ===\n" + "\n".join(lines)
        return budget.consume(section)

    def _build_worldbuilding_context(self, budget: TokenBudget) -> str:
        if budget.exhausted() or not self.kb.worldbuilding:
            return ""

        category = self.kb.category.lower()
        if category == "fiction":
            fields = [
                "geography", "magic_system", "culture_and_society",
                "technology_level", "rules_and_laws",
            ]
        elif category == "non-fiction":
            fields = ["setting_context", "key_figures", "key_concepts"]
        elif category == "business":
            fields = ["industry_overview", "target_audience"]
        else:
            fields = []

        wb_lines: list[str] = []
        for field in fields:
            value = getattr(self.kb.worldbuilding, field, "")
            if value and value.strip():
                label = field.replace("_", " ").title()
                # Truncate each field aggressively
                words = value.split()
                if len(words) > 40:
                    value = " ".join(words[:40]) + "..."
                wb_lines.append(f"{label}: {value}")

        if not wb_lines:
            return ""

        section = "=== WORLDBUILDING ===\n" + "\n".join(wb_lines)
        return budget.consume(section)

    def _build_lore_context(self, scene: Scene, budget: TokenBudget) -> str:
        if budget.exhausted():
            return ""

        scene_chars = set(c.lower() for c in scene.characters)
        setting_lower = scene.setting.lower() if scene.setting else ""
        goal_lower = scene.goal.lower() if scene.goal else ""

        matched_entries: list[str] = []
        for entry in self.kb.lore_entries.values():
            # Check if related entities overlap with scene characters
            entity_overlap = any(
                e.lower() in scene_chars for e in entry.related_entities
            )
            # Check if tags match scene setting or goal
            tag_match = any(
                t.lower() in setting_lower or t.lower() in goal_lower
                for t in entry.tags
            )
            if entity_overlap or tag_match:
                desc = entry.description
                if len(desc.split()) > 30:
                    desc = " ".join(desc.split()[:30]) + "..."
                matched_entries.append(f"- {entry.name} ({entry.entry_type}): {desc}")

        if not matched_entries:
            return ""

        section = "=== RELEVANT LORE ===\n" + "\n".join(matched_entries[:5])
        return budget.consume(section)

    def _build_arc_context(
        self, chapter_number: int, budget: TokenBudget
    ) -> str:
        if budget.exhausted():
            return ""

        story_arcs = getattr(self.kb, "story_arcs", {})
        if not story_arcs:
            return ""

        arc_lines: list[str] = []
        for arc in story_arcs.values():
            milestones = getattr(arc, "milestones", [])
            if not milestones:
                continue
            relevant = [
                m for m in milestones
                if m.target_chapter == chapter_number or (
                    m.status == "in_progress"
                )
            ]
            if not relevant:
                continue
            arc_lines.append(f"**{arc.name}** ({arc.arc_type}): {arc.description}")
            for m in relevant:
                status_marker = f"[{m.status.upper()}]"
                arc_lines.append(
                    f"  {status_marker} {m.name} ({m.milestone_type}): {m.description}"
                )

        if not arc_lines:
            return ""

        section = "=== ARC MILESTONES ===\n" + "\n".join(arc_lines)
        return budget.consume(section)

    def _build_thread_context(
        self,
        character_names: list[str],
        chapter_number: int,
        budget: TokenBudget,
    ) -> str:
        if budget.exhausted():
            return ""

        threads = getattr(self.kb, "narrative_threads", {})
        if not threads:
            return ""

        scene_chars = set(c.lower() for c in character_names)
        thread_lines: list[str] = []

        for thread in threads.values():
            if thread.status != "open":
                continue
            # Show threads involving scene characters or targeting this chapter
            chars_overlap = any(
                c.lower() in scene_chars for c in thread.characters_involved
            )
            targets_chapter = (
                thread.target_resolution_chapter == chapter_number
            )
            if chars_overlap or targets_chapter:
                opened = f"(opened Ch.{thread.opened_chapter})" if thread.opened_chapter else ""
                target = f"-> resolve by Ch.{thread.target_resolution_chapter}" if thread.target_resolution_chapter else ""
                thread_lines.append(
                    f"- [{thread.thread_type.upper()}] {thread.name}: {thread.description} {opened} {target}"
                )

        if not thread_lines:
            return ""

        section = "=== OPEN NARRATIVE THREADS ===\n" + "\n".join(thread_lines[:5])
        return budget.consume(section)

    def _build_character_states(
        self,
        character_names: list[str],
        chapter_number: int,
        budget: TokenBudget,
    ) -> str:
        if budget.exhausted():
            return ""

        character_states = getattr(self.kb, "character_states", {})
        if not character_states:
            return ""

        state_lines: list[str] = []
        for char_name in character_names:
            states = character_states.get(char_name, [])
            if not states:
                continue
            # Get most recent state before this chapter
            relevant = [s for s in states if s.chapter_number < chapter_number]
            if not relevant:
                continue
            latest = max(relevant, key=lambda s: s.chapter_number)

            parts = [f"**{char_name}** (as of Ch. {latest.chapter_number}):"]
            if latest.emotional_state:
                parts.append(f"  Feeling: {latest.emotional_state}")
            if latest.knowledge:
                parts.append(f"  Knows: {'; '.join(latest.knowledge[:3])}")
            if latest.relationships:
                rel_strs = [f"{k}: {v}" for k, v in list(latest.relationships.items())[:3]]
                parts.append(f"  Relations: {'; '.join(rel_strs)}")
            if latest.physical_state:
                parts.append(f"  Physical: {latest.physical_state}")

            state_lines.append("\n".join(parts))

        if not state_lines:
            return ""

        section = "=== CHARACTER STATES ===\n" + "\n\n".join(state_lines)
        return budget.consume(section)

    def _build_retrieval_context(
        self,
        scene: Scene,
        chapter_number: int,
        budget: TokenBudget,
    ) -> str:
        if budget.exhausted() or not self.search_service:
            return ""

        # Build query from scene summary + character names
        query_parts = []
        if scene.summary:
            query_parts.append(scene.summary)
        if scene.characters:
            query_parts.append(" ".join(scene.characters))
        query = " ".join(query_parts)
        if not query.strip():
            return ""

        try:
            results = self.search_service.search(
                query,
                mode="keyword",
                top_k=4,
                filters={"exclude_source_type": ["reference"]},  # keep refs out of canon band
            )
        except Exception:
            logger.debug("Retrieval search failed during context building", exc_info=True)
            return ""

        if not results:
            return ""

        # Filter to only results from chapters before current
        snippets: list[str] = []
        for r in results:
            # Skip results from current or later chapters
            if hasattr(r, "chapter_number") and r.chapter_number and r.chapter_number >= chapter_number:
                continue
            text = r.text if hasattr(r, "text") else str(r)
            # Truncate snippet
            words = text.split()
            if len(words) > 50:
                text = " ".join(words[:50]) + "..."
            snippets.append(f"- {text}")
            if len(snippets) >= 3:
                break

        if not snippets:
            return ""

        section = "=== PREVIOUSLY ESTABLISHED ===\n" + "\n".join(snippets)
        return budget.consume(section)

    def _build_reference_context(
        self,
        scene: Scene,
        budget: TokenBudget,
        max_ref_tokens: int = 450,
    ) -> str:
        """Imported reference material (B19), retrieved and clearly marked as source
        material rather than canon. Bounded to `max_ref_tokens` of the shared budget."""
        if budget.exhausted() or not self.search_service:
            return ""

        query_parts = []
        if scene.summary:
            query_parts.append(scene.summary)
        if scene.setting:
            query_parts.append(scene.setting)
        if scene.characters:
            query_parts.append(" ".join(scene.characters))
        query = " ".join(query_parts).strip()
        if not query:
            return ""

        try:
            results = self.search_service.search(
                query,
                mode="keyword",
                top_k=4,
                filters={"source_type": "reference"},
            )
        except Exception:
            logger.debug("Reference retrieval failed during context building", exc_info=True)
            return ""

        if not results:
            return ""

        used_before = budget.used
        lines: list[str] = []
        for r in results:
            if budget.used - used_before >= max_ref_tokens or budget.exhausted():
                break
            text = r.text if hasattr(r, "text") else str(r)
            words = text.split()
            if len(words) > 60:
                text = " ".join(words[:60]) + "..."
            clipped = budget.consume(text)
            if clipped:
                lines.append(f"- {clipped}")

        if not lines:
            return ""

        return (
            "=== REFERENCE MATERIAL (imported source — use as background/citation, NOT canon) ===\n"
            + "\n".join(lines)
        )
