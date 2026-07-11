# src/libriscribe/agents/chapter_writer.py

import logging
from pathlib import Path
from typing import Optional
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils import prompts_context as prompts
from libriscribe.utils.file_utils import write_markdown_file
from libriscribe.utils.system_prompts import CREATIVE_WRITING_SYSTEM_PROMPT
from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene
from libriscribe.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

PACING_INSTRUCTIONS = {
    "action": "Write this scene with rapid pacing. Use short, punchy sentences. Focus on physical movement, urgency, and tension. Minimize introspection. Keep dialogue brief and clipped.",
    "dialogue": "This is a dialogue-driven scene. Let the conversation carry the story. Use distinct voices for each character. Include beats and body language between lines. Minimize narration.",
    "introspective": "Write this scene with slow, reflective pacing. Go deep into the character's thoughts and feelings. Use longer sentences and internal monologue. Allow space for emotional processing.",
    "exposition": "Weave necessary information naturally into the narrative. Avoid info-dumps -- reveal details through character interaction, observation, or discovery. Keep the reader engaged.",
    "transition": "Write a brief, efficient scene that bridges two parts of the story. Focus on movement, time passage, or a shift in mood. Keep it concise but atmospheric.",
}


class ChapterWriterAgent(Agent):
    """Writes chapters."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("ChapterWriterAgent", llm_client, event_callback)
        self.context_builder = None

    def _get_system_prompt(self, pkb: ProjectKnowledgeBase) -> str | None:
        """Returns the writing system prompt, with per-project override > global override > default."""
        if pkb.writing_system_prompt:
            return pkb.writing_system_prompt
        from libriscribe.settings import Settings
        settings = Settings()
        if settings.writing_system_prompt:
            return settings.writing_system_prompt
        return CREATIVE_WRITING_SYSTEM_PROMPT

    def _read_chapter_text(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int) -> str:
        """A written chapter's prose (revised preferred); empty when missing."""
        if chapter_number < 1 or not project_knowledge_base.project_dir:
            return ""
        pdir = Path(project_knowledge_base.project_dir)
        for cand in (pdir / f"chapter_{chapter_number}_revised.md",
                     pdir / f"chapter_{chapter_number}.md"):
            if cand.exists():
                try:
                    return cand.read_text(encoding="utf-8")
                except OSError:
                    return ""
        return ""

    def _prev_chapter_tail(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int) -> str:
        """Prose context for scene 1: the previous chapter's text (revised preferred)."""
        return self._read_chapter_text(project_knowledge_base, chapter_number - 1)

    def _prev_chapters_recap_entries(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int) -> list[tuple[str, str, str]]:
        """B40: (label, planned beat, prose) for EVERY scene of EVERY previous chapter, so the
        recap covers the whole book so far. Chapters whose files can't be split into scenes
        fall back to one chapter-summary entry. ~45 tokens/scene — even 20 chapters × 5 scenes
        stays a few k tokens, well inside the local-model sweet spot."""
        import re
        entries: list[tuple[str, str, str]] = []
        for n in sorted(k for k in (project_knowledge_base.chapters or {}) if k < chapter_number):
            ch = project_knowledge_base.get_chapter(n)
            text = self._read_chapter_text(project_knowledge_base, n)
            scenes = sorted(ch.scenes, key=lambda s: s.scene_number) if ch else []
            bodies = re.split(r"^#{1,6}\s*Scene\s+\d+.*$", text, flags=re.M)[1:] if text else []
            if scenes and bodies:
                for sc, body in zip(scenes, bodies):
                    entries.append((f"Chapter {n}, Scene {sc.scene_number}", sc.summary or "", body))
            elif ch and (ch.summary or "").strip():
                entries.append((f"Chapter {n}", ch.summary.strip().replace("\n", " "), text))
        return entries

    def _build_scene_prompt(
        self,
        project_knowledge_base: ProjectKnowledgeBase,
        chapter: Chapter,
        scene: Scene,
        total_scenes: int,
        prior_prose: str,
        recap_entries: Optional[list[tuple[str, str, str]]] = None,
        guard_prose: Optional[str] = None,
        streaming: bool = False,
    ) -> tuple[str, int]:
        """ONE steering stack for both write paths — register > canon > all-scenes recap >
        verbatim continuity tail > B40 ban list > scene brief. (The streaming path previously
        assembled a bare prompt and silently missed the continuity/canon/register blocks.)
        Returns (prompt, max_tokens)."""
        chapter_number = chapter.chapter_number
        prompt_kwargs = dict(
            chapter_number=chapter_number,
            chapter_title=chapter.title,
            book_title=project_knowledge_base.title,
            genre=project_knowledge_base.genre,
            category=project_knowledge_base.category,
            language=project_knowledge_base.language,
            chapter_summary=chapter.summary,
            scene_number=scene.scene_number,
            scene_summary=scene.summary,
            characters=", ".join(scene.characters) if scene.characters else "None specified",
            setting=scene.setting if scene.setting else "None specified",
            goal=scene.goal if scene.goal else "None specified",
            emotional_beat=scene.emotional_beat if scene.emotional_beat else "None specified",
            total_scenes=total_scenes,
        )

        max_gen_tokens = 2000
        if self.context_builder:
            context_block = self.context_builder.build_scene_context(chapter_number, scene, chapter)
            scene_prompt = prompts.ENRICHED_SCENE_PROMPT.format(context_block=context_block, **prompt_kwargs)
            max_gen_tokens = 3500 if streaming else 5000
        else:
            scene_prompt = prompts.SCENE_PROMPT.format(**prompt_kwargs)

        # F4: Pacing instructions based on scene type
        if scene.scene_type and scene.scene_type in PACING_INSTRUCTIONS:
            scene_prompt += f"\n\nPACING: {PACING_INSTRUCTIONS[scene.scene_type]}"
        if scene.target_word_count:
            scene_prompt += f"\n\nTARGET LENGTH: Aim for approximately {scene.target_word_count} words for this scene."

        # B40: named ban list of overused phrases/openings — small models obey explicit
        # bans far better than abstract "don't reuse imagery" rules. Derived from all
        # recent prose (previous chapter + everything written this chapter).
        from libriscribe.utils.repetition_guard import repetition_guard_block
        guard = repetition_guard_block(guard_prose if guard_prose is not None else prior_prose)
        if guard:
            scene_prompt = f"{guard}\n\n{scene_prompt}"

        # Prior-prose continuity block (see utils/prose_steering.continuity_block).
        from libriscribe.utils.prose_steering import continuity_block, scene_recap_block
        cont = continuity_block(prior_prose)
        if cont:
            scene_prompt = f"{cont}\n\n{scene_prompt}"

        # B40: rolling recap of EVERY scene already written — all previous chapters plus
        # this one — so late scenes can't blindly re-run beats the tail no longer shows.
        recap = scene_recap_block(recap_entries or [])
        if recap:
            scene_prompt = f"{recap}\n\n{scene_prompt}"

        # B32: the author's inviolable canon rules bind every scene.
        from libriscribe.services.lore_digest import canon_block
        canon = canon_block(project_knowledge_base)
        if canon:
            scene_prompt = f"{canon}\n\n{scene_prompt}"

        # B36 (gated): optional prose-register directive — only when the feature is
        # enabled in Advanced settings AND the project sets a level.
        try:
            from libriscribe.settings import Settings
            from libriscribe.utils.style_register import active_register_directive
            reg = active_register_directive(project_knowledge_base, Settings())
            if reg:
                scene_prompt = f"{reg}\n\n{scene_prompt}"
        except Exception:
            pass

        return scene_prompt, max_gen_tokens

    def _enforce_freshness(
        self,
        scene_content: str,
        scene: Scene,
        scene_prompt: str,
        sys_prompt: Optional[str],
        guard_context: str,
        max_tokens: int,
    ) -> str:
        """B40 enforcement half: the ban list in the prompt is advisory to a small model.
        Deterministically check the generated scene against it; on real violations (an
        opening that mirrors an earlier scene, or 2+ banned-phrase reuses), regenerate ONCE
        with the violations named. Keeps the retry only if it's measurably fresher."""
        from libriscribe.utils.repetition_guard import find_violations
        from libriscribe.utils.prose_sanitizer import sanitize_prose, strip_summary_echo

        if not guard_context.strip():
            return scene_content
        violations = find_violations(scene_content, guard_context)
        opening_violation = any(v.startswith("opened") for v in violations)
        if len(violations) < 2 and not opening_violation:
            return scene_content

        self.emit("log", {"level": "warning", "message": (
            f"Scene {scene.scene_number} repeated earlier language "
            f"({len(violations)} violation(s)) — regenerating once."
        )})
        retry_prompt = (
            scene_prompt
            + "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED because it repeated earlier scenes:\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\nWrite the scene again from scratch with entirely fresh wording and imagery, "
            "and open it a completely different way."
        )
        retry = self.llm_client.generate_content(retry_prompt, max_tokens=max_tokens, system_prompt=sys_prompt)
        if not retry:
            return scene_content
        retry = sanitize_prose(strip_summary_echo(retry, scene.summary))
        if len(find_violations(retry, guard_context)) < len(violations):
            return retry
        return scene_content


    def execute(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int, output_path: Optional[str] = None) -> None:
        """Writes a chapter scene by scene."""
        try:
            # Get chapter data
            chapter = project_knowledge_base.get_chapter(chapter_number)
            if not chapter:
                self.emit("log", {"level": "warning", "message": f"Chapter {chapter_number} not found in knowledge base. Creating default."})
                chapter = Chapter(
                    chapter_number=chapter_number,
                    title=f"Chapter {chapter_number}",
                    summary="A new chapter in the unfolding story."
                )
                default_scene = Scene(
                    scene_number=1,
                    summary="The story continues with new developments.",
                    characters=["Shade"],
                    setting="Neo-London",
                    goal="Advance the plot",
                    emotional_beat="Tension"
                )
                chapter.scenes.append(default_scene)
                project_knowledge_base.add_chapter(chapter)

            self.emit("log", {"level": "info", "message": f"Writing Chapter {chapter_number}: {chapter.title}"})

            # Make sure there's at least one scene
            if not chapter.scenes:
                self.emit("log", {"level": "warning", "message": f"No scenes found for Chapter {chapter_number}. Creating a default scene."})
                default_scene = Scene(
                    scene_number=1,
                    summary="The story continues with new developments.",
                    characters=["Shade"],
                    setting="Neo-London",
                    goal="Advance the plot",
                    emotional_beat="Tension"
                )
                chapter.scenes.append(default_scene)

            ordered_scenes = sorted(chapter.scenes, key=lambda s: s.scene_number)
            scene_contents = []

            # Continuity (anti-repetition): each scene sees the prose written just before it —
            # earlier scenes of this chapter, or the previous chapter's ending for scene 1 —
            # plus a recap of EVERY scene of the book so far and a ban list (B40).
            prev_chapter_tail = self._prev_chapter_tail(project_knowledge_base, chapter_number)
            prev_recap = self._prev_chapters_recap_entries(project_knowledge_base, chapter_number)

            for scene in ordered_scenes:
                self.emit("log", {"level": "info", "message": f"Creating Scene/Section {scene.scene_number} of {len(ordered_scenes)}..."})

                written = "\n\n".join(scene_contents)
                prior = written if scene_contents else prev_chapter_tail
                guard_context = f"{prev_chapter_tail}\n\n{written}".strip()
                recap = prev_recap + [
                    (f"Scene {sc.scene_number}", sc.summary or "", body)
                    for sc, body in zip(ordered_scenes, scene_contents)
                ]
                scene_prompt, max_gen_tokens = self._build_scene_prompt(
                    project_knowledge_base, chapter, scene, len(ordered_scenes), prior,
                    recap_entries=recap,
                    guard_prose=guard_context,
                )

                sys_prompt = self._get_system_prompt(project_knowledge_base)
                scene_content = self.llm_client.generate_content(scene_prompt, max_tokens=max_gen_tokens, system_prompt=sys_prompt)
                if not scene_content:
                    self.emit("log", {"level": "warning", "message": f"Failed to generate content for Scene {scene.scene_number}. Using placeholder."})
                    scene_content = f"[Scene {scene.scene_number} content unavailable]"

                # B39: outline scaffolding never reaches the reader — strip any echoed
                # title/summary, sanitize model tics, delimit scenes in code.
                from libriscribe.utils.prose_sanitizer import sanitize_prose, strip_summary_echo
                scene_content = sanitize_prose(strip_summary_echo(scene_content, scene.summary))
                scene_content = self._enforce_freshness(
                    scene_content, scene, scene_prompt, sys_prompt, guard_context, max_gen_tokens)
                scene_content = f"### Scene {scene.scene_number}\n\n{scene_content}"

                scene_contents.append(scene_content)
                self.emit("stream_complete", {
                    "stage": "chapters",
                    "chapter": chapter_number,
                    "scene": scene.scene_number,
                    "word_count": len(scene_content.split()),
                })

            chapter_content = f"## Chapter {chapter_number}: {chapter.title}\n\n"
            chapter_content += "\n\n".join(scene_contents)

            if output_path is None:
                output_path = str(Path(project_knowledge_base.project_dir) / f"chapter_{chapter_number}.md")
            write_markdown_file(output_path, chapter_content)

            self.emit("chapter_complete", {
                "chapter": chapter_number,
                "scenes_written": len(ordered_scenes),
                "word_count": len(chapter_content.split()),
            })

        except Exception as e:
            self.logger.exception(f"Error writing chapter {chapter_number}: {e}")
            self.emit("error", {
                "stage": "chapters",
                "chapter": chapter_number,
                "message": str(e),
                "recoverable": False,
            })

    def execute_streaming(self, project_knowledge_base: ProjectKnowledgeBase, chapter_number: int, output_path: Optional[str] = None) -> None:
        """Writes a chapter scene by scene with streaming output."""
        try:
            chapter = project_knowledge_base.get_chapter(chapter_number)
            if not chapter:
                self.emit("log", {"level": "warning", "message": f"Chapter {chapter_number} not found. Creating default."})
                chapter = Chapter(
                    chapter_number=chapter_number,
                    title=f"Chapter {chapter_number}",
                    summary="A new chapter in the unfolding story."
                )
                default_scene = Scene(
                    scene_number=1,
                    summary="The story continues with new developments.",
                    characters=["Shade"],
                    setting="Neo-London",
                    goal="Advance the plot",
                    emotional_beat="Tension"
                )
                chapter.scenes.append(default_scene)
                project_knowledge_base.add_chapter(chapter)

            self.emit("log", {"level": "info", "message": f"Writing Chapter {chapter_number}: {chapter.title} (streaming)"})

            if not chapter.scenes:
                default_scene = Scene(
                    scene_number=1,
                    summary="The story continues with new developments.",
                    characters=["Shade"],
                    setting="Neo-London",
                    goal="Advance the plot",
                    emotional_beat="Tension"
                )
                chapter.scenes.append(default_scene)

            ordered_scenes = sorted(chapter.scenes, key=lambda s: s.scene_number)
            scene_contents = []
            prev_chapter_tail = self._prev_chapter_tail(project_knowledge_base, chapter_number)
            prev_recap = self._prev_chapters_recap_entries(project_knowledge_base, chapter_number)

            for scene in ordered_scenes:
                self.emit("log", {"level": "info", "message": f"Streaming Scene {scene.scene_number} of {len(ordered_scenes)}..."})

                written = "\n\n".join(scene_contents)
                prior = written if scene_contents else prev_chapter_tail
                guard_context = f"{prev_chapter_tail}\n\n{written}".strip()
                recap = prev_recap + [
                    (f"Scene {sc.scene_number}", sc.summary or "", body)
                    for sc, body in zip(ordered_scenes, scene_contents)
                ]
                scene_prompt, max_gen_tokens = self._build_scene_prompt(
                    project_knowledge_base, chapter, scene, len(ordered_scenes), prior,
                    recap_entries=recap,
                    guard_prose=guard_context,
                    streaming=True,
                )

                # Try streaming; fall back to non-streaming
                sys_prompt = self._get_system_prompt(project_knowledge_base)
                scene_content = ""
                try:
                    for chunk in self.llm_client.generate_content_streaming(scene_prompt, max_tokens=max_gen_tokens, system_prompt=sys_prompt):
                        scene_content += chunk
                        self.emit("stream_chunk", {
                            "text": chunk,
                            "stage": "chapters",
                            "chapter": chapter_number,
                            "scene": scene.scene_number,
                        })
                except (AttributeError, NotImplementedError):
                    scene_content = self.llm_client.generate_content(scene_prompt, max_tokens=max_gen_tokens, system_prompt=sys_prompt)

                if not scene_content.strip():
                    # A reasoning model can spend the whole streamed budget thinking and emit
                    # zero prose; the non-streaming path carries the adaptive budget retry.
                    self.emit("log", {"level": "warning", "message": (
                        f"Scene {scene.scene_number} streamed no prose — retrying non-streamed."
                    )})
                    scene_content = self.llm_client.generate_content(
                        scene_prompt, max_tokens=max_gen_tokens, system_prompt=sys_prompt)

                if not scene_content:
                    scene_content = f"[Scene {scene.scene_number} content unavailable]"

                # B39: same de-scaffold + sanitation as the non-streaming path (chunks stream
                # to the UI raw; the STORED text is clean). The freshness retry regenerates
                # non-streamed — the preview shows the first attempt, the file gets the keeper.
                from libriscribe.utils.prose_sanitizer import sanitize_prose, strip_summary_echo
                scene_content = sanitize_prose(strip_summary_echo(scene_content, scene.summary))
                scene_content = self._enforce_freshness(
                    scene_content, scene, scene_prompt, sys_prompt, guard_context, max_gen_tokens)
                scene_content = f"### Scene {scene.scene_number}\n\n{scene_content}"

                scene_contents.append(scene_content)
                self.emit("stream_complete", {
                    "stage": "chapters",
                    "chapter": chapter_number,
                    "scene": scene.scene_number,
                    "word_count": len(scene_content.split()),
                })

            chapter_content = f"## Chapter {chapter_number}: {chapter.title}\n\n"
            chapter_content += "\n\n".join(scene_contents)

            if output_path is None:
                output_path = str(Path(project_knowledge_base.project_dir) / f"chapter_{chapter_number}.md")
            write_markdown_file(output_path, chapter_content)

            self.emit("chapter_complete", {
                "chapter": chapter_number,
                "scenes_written": len(ordered_scenes),
                "word_count": len(chapter_content.split()),
            })

        except Exception as e:
            self.logger.exception(f"Error writing chapter {chapter_number}: {e}")
            self.emit("error", {
                "stage": "chapters",
                "chapter": chapter_number,
                "message": str(e),
                "recoverable": False,
            })
