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

            # Continuity (anti-repetition): each scene sees the tail of the prose written just
            # before it — earlier scenes of this chapter, or the previous chapter's ending for
            # scene 1. Without this, every scene was generated blind to prior prose, and small
            # models re-invent the same imagery over and over.
            prev_chapter_tail = ""
            if chapter_number > 1 and project_knowledge_base.project_dir:
                pdir = Path(project_knowledge_base.project_dir)
                for cand in (pdir / f"chapter_{chapter_number - 1}_revised.md",
                             pdir / f"chapter_{chapter_number - 1}.md"):
                    if cand.exists():
                        try:
                            prev_chapter_tail = cand.read_text(encoding="utf-8")
                        except OSError:
                            pass
                        break

            for scene in ordered_scenes:
                self.emit("log", {"level": "info", "message": f"Creating Scene/Section {scene.scene_number} of {len(ordered_scenes)}..."})

                scene_title = f"Scene {scene.scene_number}: {scene.summary[:30]}..." if len(scene.summary) > 30 else f"Scene {scene.scene_number}: {scene.summary}"

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
                    total_scenes=len(ordered_scenes),
                )

                max_gen_tokens = 2000
                if self.context_builder:
                    context_block = self.context_builder.build_scene_context(chapter_number, scene, chapter)
                    scene_prompt = prompts.ENRICHED_SCENE_PROMPT.format(context_block=context_block, **prompt_kwargs)
                    max_gen_tokens = 3500
                else:
                    scene_prompt = prompts.SCENE_PROMPT.format(**prompt_kwargs)

                # F4: Pacing instructions based on scene type
                if scene.scene_type and scene.scene_type in PACING_INSTRUCTIONS:
                    scene_prompt += f"\n\nPACING: {PACING_INSTRUCTIONS[scene.scene_type]}"
                if scene.target_word_count:
                    scene_prompt += f"\n\nTARGET LENGTH: Aim for approximately {scene.target_word_count} words for this scene."

                scene_prompt += f"\n\nIMPORTANT: Begin the scene with the title: **{scene_title}**"

                # Prior-prose continuity block (see utils/prose_steering.continuity_block).
                from libriscribe.utils.prose_steering import continuity_block
                prior = "\n\n".join(scene_contents) if scene_contents else prev_chapter_tail
                cont = continuity_block(prior)
                if cont:
                    scene_prompt = f"{cont}\n\n{scene_prompt}"

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

                sys_prompt = self._get_system_prompt(project_knowledge_base)
                scene_content = self.llm_client.generate_content(scene_prompt, max_tokens=max_gen_tokens, system_prompt=sys_prompt)
                if not scene_content:
                    self.emit("log", {"level": "warning", "message": f"Failed to generate content for Scene {scene.scene_number}. Using placeholder."})
                    scene_content = f"[Scene {scene.scene_number} content unavailable]"

                if not scene_content.startswith(f"**{scene_title}**") and not scene_content.startswith(f"# {scene_title}"):
                    scene_content = f"**{scene_title}**\n\n{scene_content}"

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

            for scene in ordered_scenes:
                self.emit("log", {"level": "info", "message": f"Streaming Scene {scene.scene_number} of {len(ordered_scenes)}..."})

                scene_title = f"Scene {scene.scene_number}: {scene.summary[:30]}..." if len(scene.summary) > 30 else f"Scene {scene.scene_number}: {scene.summary}"

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
                    total_scenes=len(ordered_scenes),
                )

                max_gen_tokens = 2000
                if self.context_builder:
                    context_block = self.context_builder.build_scene_context(chapter_number, scene, chapter)
                    scene_prompt = prompts.ENRICHED_SCENE_PROMPT.format(context_block=context_block, **prompt_kwargs)
                    max_gen_tokens = 3500
                else:
                    scene_prompt = prompts.SCENE_PROMPT.format(**prompt_kwargs)

                # F4: Pacing instructions based on scene type
                if scene.scene_type and scene.scene_type in PACING_INSTRUCTIONS:
                    scene_prompt += f"\n\nPACING: {PACING_INSTRUCTIONS[scene.scene_type]}"
                if scene.target_word_count:
                    scene_prompt += f"\n\nTARGET LENGTH: Aim for approximately {scene.target_word_count} words for this scene."

                scene_prompt += f"\n\nIMPORTANT: Begin the scene with the title: **{scene_title}**"

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

                if not scene_content:
                    scene_content = f"[Scene {scene.scene_number} content unavailable]"

                if not scene_content.startswith(f"**{scene_title}**") and not scene_content.startswith(f"# {scene_title}"):
                    scene_content = f"**{scene_title}**\n\n{scene_content}"

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
