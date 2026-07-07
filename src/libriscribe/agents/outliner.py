# src/libriscribe/agents/outliner.py

import logging
from typing import Optional
from pathlib import Path

from libriscribe.utils.llm_client import LLMClient
from libriscribe.utils import prompts_context as prompts
from libriscribe.agents.agent_base import Agent, EventCallback
from libriscribe.utils.file_utils import write_markdown_file, write_json_file, extract_json_from_markdown
from libriscribe.knowledge_base import ProjectKnowledgeBase, Chapter, Scene, StoryArc, ArcMilestone

logger = logging.getLogger(__name__)


class OutlinerAgent(Agent):
    """Generates book outlines."""

    def __init__(self, llm_client: LLMClient, event_callback: Optional[EventCallback] = None):
        super().__init__("OutlinerAgent", llm_client, event_callback)

    def execute(self, project_knowledge_base: ProjectKnowledgeBase, output_path: Optional[str] = None) -> None:
        """Generates a chapter outline and then iterates to generate scene outlines."""
        try:
            max_chapters = self._get_max_chapters(project_knowledge_base)

            # Phase 0b: ground the outline in the author's established lore (if any).
            from libriscribe.services.lore_digest import grounding_block
            lore_block = grounding_block(project_knowledge_base)

            if project_knowledge_base.book_length == "Short Story":
                initial_prompt = prompts.OUTLINE_PROMPT.format(**project_knowledge_base.model_dump())
                initial_prompt += f"\n\nIMPORTANT: This is a SHORT STORY. Generate EXACTLY {max_chapters} chapters. Do not exceed this limit."
            elif project_knowledge_base.book_length == "Novella":
                initial_prompt = prompts.OUTLINE_PROMPT.format(**project_knowledge_base.model_dump())
                initial_prompt += f"\n\nIMPORTANT: This is a NOVELLA. Generate EXACTLY {max_chapters} chapters. Do not exceed this limit."
            else:
                initial_prompt = prompts.OUTLINE_PROMPT.format(**project_knowledge_base.model_dump())
                initial_prompt += f"\n\nIMPORTANT: Generate at most {max_chapters} chapters."

            if lore_block:
                initial_prompt = f"{lore_block}\n\n{initial_prompt}"

            self.emit("log", {"level": "info", "message": "Creating chapter outline..."})
            initial_outline = self.llm_client.generate_content(initial_prompt, max_tokens=3000, temperature=0.5)
            if not initial_outline:
                logger.error("Initial outline generation failed.")
                return

            self.process_outline(project_knowledge_base, initial_outline, max_chapters)

            if output_path is None:
                output_path = str(project_knowledge_base.project_dir / "outline.md")

            project_knowledge_base.outline = initial_outline
            write_markdown_file(output_path, project_knowledge_base.outline)

            # --- Step 2: Generate scene outlines for each chapter ---
            self.emit("log", {"level": "info", "message": "Creating scene/sections breakdowns for each chapter..."})

            for chapter_num, chapter in project_knowledge_base.chapters.items():
                if chapter_num <= max_chapters:
                    self.emit("log", {"level": "info", "message": f"Working on Chapter {chapter_num}: {chapter.title}"})
                    self.generate_scene_outline(project_knowledge_base, chapter)
                    if chapter.scenes:
                        self.emit("log", {"level": "info", "message": f"Created {len(chapter.scenes)} scenes for Chapter {chapter_num}"})
                    else:
                        self.emit("log", {"level": "warning", "message": f"No scenes were generated for Chapter {chapter_num}"})

            if hasattr(project_knowledge_base, 'project_dir') and project_knowledge_base.project_dir:
                scenes_path = str(Path(project_knowledge_base.project_dir) / "scenes.json")
                scenes_data = {}
                for chapter_num, chapter in project_knowledge_base.chapters.items():
                    scenes_data[str(chapter_num)] = [scene.model_dump() for scene in chapter.scenes]
                write_json_file(scenes_path, scenes_data)

            # Generate arc milestones after outline is complete
            self._generate_arc_milestones(project_knowledge_base)

            self.logger.info(f"Outline and scenes generated and saved to knowledge base and {output_path}")

        except Exception as e:
            self.logger.exception(f"Error generating outline: {e}")
            self.emit("log", {"level": "error", "message": f"Failed to generate outline: {e}"})


    def _get_max_chapters(self, project_knowledge_base: ProjectKnowledgeBase) -> int:
        # Phase 0: respect the user's requested chapter count — do NOT shrink it to a book-length
        # cap. The user's number is the target/cap; the book-length default only applies when they
        # didn't specify one.
        nc = project_knowledge_base.num_chapters
        if isinstance(nc, (tuple, list)) and nc:
            nc = max(nc)
        try:
            nc = int(nc)
        except (TypeError, ValueError):
            nc = 0
        if nc > 1:
            return nc
        book_length = project_knowledge_base.book_length
        if book_length == "Short Story":
            return 2
        elif book_length == "Novella":
            return 8
        else:
            return 20

    def _enforce_chapter_limit(self, project_knowledge_base: ProjectKnowledgeBase, max_chapters: int) -> None:
        if project_knowledge_base.get("num_chapters", 0) > max_chapters:
            logger.info(f"Limiting chapters from {project_knowledge_base.num_chapters} to {max_chapters}")
            chapters_to_keep = {}
            for i in range(1, max_chapters + 1):
                if i in project_knowledge_base.chapters:
                    chapters_to_keep[i] = project_knowledge_base.chapters[i]
            project_knowledge_base.chapters = chapters_to_keep
            project_knowledge_base.num_chapters = max_chapters

    def _update_outline_markdown(self, original_outline: str, max_chapters: int) -> str:
        lines = original_outline.split("\n")
        updated_lines = []
        in_chapter_section = False
        current_chapter = 0
        for line in lines:
            if "Chapter" in line and ("**Chapter" in line or "## Chapter" in line):
                in_chapter_section = True
                current_chapter += 1
                if current_chapter > max_chapters:
                    continue
            if not in_chapter_section or current_chapter <= max_chapters:
                updated_lines.append(line)
        return "\n".join(updated_lines)

    def generate_scene_outline(self, project_knowledge_base: ProjectKnowledgeBase, chapter: Chapter):
        try:
            scene_prompt = f"""
            Create a detailed outline for the scenes in Chapter {chapter.chapter_number}: {chapter.title}
            of a {project_knowledge_base.genre} book titled "{project_knowledge_base.title}"
            which is categorized as {project_knowledge_base.category}.
            The book should be written in {project_knowledge_base.language}.

            Book Description: {project_knowledge_base.description}

            Chapter Summary: {chapter.summary}

            The outline should include a breakdown of 3-6 scenes for this chapter, with EACH scene having:
            * Scene Number: (e.g., Scene 1, Scene 2, etc.)
            * Summary: (A short description of what happens in the scene, 1-2 sentences)
            * Characters: (A list of the characters involved, separated by commas)
            * Setting: (Where the scene takes place)
            * Goal: (The purpose of the scene)
            * Emotional Beat: (The primary emotion conveyed in the scene)
            * Scene Type: (One of: action, dialogue, introspective, exposition, transition)

            IMPORTANT: Format the scene outline using Markdown bullet points, as shown below:

            Scene 1:
                * Summary: [Scene summary here]
                * Characters: [Character 1, Character 2, ...]
                * Setting: [Scene setting]
                * Goal: [Scene goal]
                * Emotional Beat: [Scene emotional beat]
                * Scene Type: [action/dialogue/introspective/exposition/transition]

            Scene 2:
                * Summary: [Scene summary here]
                * Characters: [Character 1, Character 2, ...]
                * Setting: [Scene setting]
                * Goal: [Scene goal]
                * Emotional Beat: [Scene emotional beat]
                * Scene Type: [action/dialogue/introspective/exposition/transition]

            [Repeat for each scene, maintaining the exact same bullet point format]

            Be sure to include all main characters relevant to this chapter and create a natural flow between scenes.
            """

            scene_outline_md = self.llm_client.generate_content(scene_prompt, max_tokens=2000, temperature=0.5)
            if not scene_outline_md:
                logger.error(f"Scene outline generation failed for Chapter {chapter.chapter_number}.")
                return

            chapter.scenes = []
            scene_sections = self._split_into_scene_sections(scene_outline_md)

            for scene_number, scene_section in enumerate(scene_sections, 1):
                scene_data = self._extract_scene_data(scene_section, scene_number)
                if scene_data:
                    scene = Scene(**scene_data)
                    chapter.scenes.append(scene)
                    logger.debug(f"Added Scene {scene_number} to Chapter {chapter.chapter_number}")
                else:
                    logger.warning(f"Failed to extract data for Scene {scene_number} in Chapter {chapter.chapter_number}")

            chapter.scenes.sort(key=lambda s: s.scene_number)
            return True

        except Exception as e:
            logger.exception(f"Error generating scene outline for chapter {chapter.chapter_number}: {e}")
            return False

    def _split_into_scene_sections(self, scene_outline_md: str) -> list:
        scene_outline_md = scene_outline_md.replace('\r\n', '\n').replace('\r', '\n')
        lines = scene_outline_md.split('\n')
        scene_sections = []
        current_section = []
        is_in_scene = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "Scene" in line and (":" in line or line.strip().startswith("Scene")):
                if is_in_scene and current_section:
                    scene_sections.append("\n".join(current_section))
                    current_section = []
                is_in_scene = True
                current_section.append(line)
            elif is_in_scene:
                current_section.append(line)
        if current_section:
            scene_sections.append("\n".join(current_section))
        return scene_sections

    def _extract_scene_data(self, scene_section: str, default_scene_number: int) -> dict:
        scene_data = {
            "scene_number": default_scene_number,
            "summary": "",
            "characters": [],
            "setting": "",
            "goal": "",
            "emotional_beat": "",
            "scene_type": "",
        }
        lines = scene_section.split('\n')
        header_line = lines[0] if lines else ""
        if "Scene" in header_line and ":" in header_line:
            try:
                number_part = header_line.split("Scene", 1)[1].split(":", 1)[0].strip()
                if number_part.isdigit():
                    scene_data["scene_number"] = int(number_part)
            except (IndexError, ValueError):
                pass
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Scene"):
                continue
            for field, marker in [
                ("summary", "Summary:"),
                ("characters", "Characters:"),
                ("setting", "Setting:"),
                ("goal", "Goal:"),
                ("emotional_beat", "Emotional Beat:"),
                ("scene_type", "Scene Type:"),
            ]:
                if marker.lower() in line.lower():
                    content = line.split(marker, 1)[1].strip() if marker in line else line.split(marker.lower(), 1)[1].strip()
                    content = content.lstrip("*-[]").strip()
                    if field == "characters":
                        characters = [name.strip() for name in content.split(",") if name.strip()]
                        scene_data["characters"] = characters
                    else:
                        scene_data[field] = content
        if not scene_data["summary"]:
            for line in lines:
                if line and not any(marker in line.lower() for marker in ["scene", "summary:", "characters:", "setting:", "goal:", "emotional beat:"]):
                    if scene_data["summary"]:
                        scene_data["summary"] += " " + line.strip()
                    else:
                        scene_data["summary"] = line.strip()
        return scene_data if scene_data["summary"] else None

    def process_scene_outline(self, chapter: Chapter, scene_outline_md: str):
        """Parses the Markdown scene outline and adds scenes to the chapter."""
        lines = scene_outline_md.split("\n")
        current_scene = None
        scene_number = 1
        chapter.scenes = []
        current_summary = ""
        current_characters = []
        current_setting = ""
        current_goal = ""
        current_emotional_beat = ""
        in_scene_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ("scene" in line.lower() or "**scene" in line.lower()) and not in_scene_section:
                if current_summary:
                    current_scene = Scene(
                        scene_number=scene_number,
                        summary=current_summary.strip(),
                        characters=current_characters,
                        setting=current_setting,
                        goal=current_goal,
                        emotional_beat=current_emotional_beat
                    )
                    chapter.scenes.append(current_scene)
                    scene_number += 1
                    current_summary = ""
                    current_characters = []
                    current_setting = ""
                    current_goal = ""
                    current_emotional_beat = ""
                in_scene_section = True
                if ":" in line:
                    parts = line.split(":", 1)
                    current_summary = parts[1].strip()
                    if current_summary.startswith("**"):
                        current_summary = current_summary[2:].strip()
                    if current_summary.endswith("**"):
                        current_summary = current_summary[:-2:].strip()
            elif "characters:" in line.lower() or "character:" in line.lower():
                in_scene_section = True
                if ":" in line:
                    chars_part = line.split(":", 1)[1].strip()
                    if "[" in chars_part and "]" in chars_part:
                        chars_part = chars_part.replace("[", "").replace("]", "")
                    chars = chars_part.split(",")
                    current_characters = [c.strip() for c in chars if c.strip()]
                    current_characters = [c.replace("*", "").strip() for c in current_characters]
            elif "setting:" in line.lower():
                in_scene_section = True
                if ":" in line:
                    current_setting = line.split(":", 1)[1].strip()
                    if current_setting.startswith("*"):
                        current_setting = current_setting[1:].strip()
                    if current_setting.endswith("*"):
                        current_setting = current_setting[:-1].strip()
            elif "goal:" in line.lower():
                in_scene_section = True
                if ":" in line:
                    current_goal = line.split(":", 1)[1].strip()
                    if current_goal.startswith("*"):
                        current_goal = current_goal[1:].strip()
                    if current_goal.endswith("*"):
                        current_goal = current_goal[:-1].strip()
            elif "emotional beat:" in line.lower() or "emotion:" in line.lower():
                in_scene_section = True
                if ":" in line:
                    current_emotional_beat = line.split(":", 1)[1].strip()
                    if current_emotional_beat.startswith("*"):
                        current_emotional_beat = current_emotional_beat[1:].strip()
                    if current_emotional_beat.endswith("*"):
                        current_emotional_beat = current_emotional_beat[:-1].strip()
            elif in_scene_section and not any(marker in line.lower() for marker in ["characters:", "setting:", "goal:", "emotional beat:", "emotion:", "scene"]):
                if "chapter" in line.lower() and (":" in line or "**" in line):
                    in_scene_section = False
                    if current_summary:
                        current_scene = Scene(
                            scene_number=scene_number,
                            summary=current_summary.strip(),
                            characters=current_characters,
                            setting=current_setting,
                            goal=current_goal,
                            emotional_beat=current_emotional_beat
                        )
                        chapter.scenes.append(current_scene)
                        scene_number += 1
                        current_summary = ""
                        current_characters = []
                        current_setting = ""
                        current_goal = ""
                        current_emotional_beat = ""
                else:
                    if current_summary:
                        current_summary += " " + line
                    else:
                        current_summary = line
                    if current_summary.startswith("**"):
                        current_summary = current_summary[2:].strip()
                    if current_summary.endswith("**"):
                        current_summary = current_summary[:-2:].strip()

        if current_summary:
            current_scene = Scene(
                scene_number=scene_number,
                summary=current_summary.strip(),
                characters=current_characters,
                setting=current_setting,
                goal=current_goal,
                emotional_beat=current_emotional_beat
            )
            chapter.scenes.append(current_scene)

        chapter.scenes.sort(key=lambda s: s.scene_number)
        chapter.scenes = [
            s for s in chapter.scenes
            if s.summary.strip() and not s.summary.strip().startswith("Continue")
            and "..." not in s.summary and len(s.summary) > 5
        ]
        for i, scene in enumerate(chapter.scenes):
            scene.scene_number = i + 1

    def process_outline(self, project_knowledge_base: ProjectKnowledgeBase, outline_markdown: str, max_chapters: int):
        """Parses the Markdown outline and populates the knowledge base."""
        lines = outline_markdown.split("\n")
        current_chapter = None
        chapter_count = 0
        current_section = None
        current_content = []

        logger.info("Processing outline...")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            if "Chapter" in line and (line.startswith("Chapter") or "##" in line or "**" in line):
                if chapter_count >= max_chapters:
                    break
                if current_chapter and current_content:
                    if current_section == "summary":
                        current_chapter.summary = "\n".join(current_content).strip()
                    current_content = []
                try:
                    chapter_parts = line.replace("##", "").replace("**", "").replace("Chapter", "").strip()
                    if ":" in chapter_parts:
                        chapter_num_str, chapter_title = chapter_parts.split(":", 1)
                    elif "-" in chapter_parts:
                        chapter_num_str, chapter_title = chapter_parts.split("-", 1)
                    else:
                        import re
                        match = re.match(r'(\d+)\s*(.*)', chapter_parts)
                        if match:
                            chapter_num_str, chapter_title = match.groups()
                        else:
                            chapter_num_str = str(chapter_count + 1)
                            chapter_title = f"Chapter {chapter_num_str}"

                    chapter_number = int(''.join(filter(str.isdigit, chapter_num_str)))
                    chapter_title = chapter_title.strip()
                    logger.info(f"Found Chapter {chapter_number}: {chapter_title}")
                    current_chapter = Chapter(
                        chapter_number=chapter_number,
                        title=chapter_title,
                        summary=""
                    )
                    project_knowledge_base.add_chapter(current_chapter)
                    chapter_count += 1
                    current_section = None
                    current_content = []
                except Exception as e:
                    logger.error(f"Error processing chapter line '{line}': {e}")
                    continue
            elif "Book Summary" in line and chapter_count == 0:
                book_summary_lines = []
                j = i + 1
                while j < len(lines) and not (lines[j].strip().startswith("Chapter") or "Chapter List" in lines[j]):
                    if lines[j].strip():
                        book_summary_lines.append(lines[j].strip())
                    j += 1
                if book_summary_lines:
                    summary = "\n".join(book_summary_lines)
                    # Phase 0: only fill the description if the user left it blank/default; otherwise
                    # record it as a suggestion rather than overwriting their words.
                    _default_desc = ("", "No description provided.")
                    if (project_knowledge_base.description or "").strip() in _default_desc:
                        project_knowledge_base.description = summary
                    else:
                        project_knowledge_base.suggested_description = summary
            elif current_chapter and ("Summary" in line or line.startswith("Summary")):
                if current_chapter:
                    current_section = "summary"
                    current_content = []
                    continue
            elif current_chapter and ("Key Events" in line or "Plot Points" in line):
                if current_chapter and current_content:
                    current_chapter.summary = "\n".join(current_content).strip()
                current_section = "plot_points"
                current_content = []
                continue
            elif current_chapter and current_section:
                cleaned_line = line.replace("*", "").replace("[", "").replace("]", "").strip()
                if cleaned_line:
                    current_content.append(cleaned_line)
                    if current_section == "summary":
                        current_chapter.summary = "\n".join(current_content).strip()
            elif "Chapter List" in line or "chapters" in line.lower():
                try:
                    next_line = lines[i+1] if i+1 < len(lines) else ""
                    if next_line:
                        import re
                        digits = re.findall(r'\d+', next_line)
                        if digits:
                            total_chapters = int(digits[0])
                            logger.info(f"Found total chapters: {total_chapters}")
                            if total_chapters > 0 and total_chapters <= max_chapters:
                                project_knowledge_base.num_chapters = total_chapters
                except Exception as e:
                    logger.error(f"Error extracting chapter count: {e}")

        if current_chapter and current_content:
            if current_section == "summary":
                current_chapter.summary = "\n".join(current_content).strip()

        if chapter_count == 0:
            logger.warning("No chapters found in outline")
            default_chapter = Chapter(
                chapter_number=1,
                title="Shadow's Discovery",
                summary="Shade, a daemon eking out a meager existence in the polluted shadows of Neo-London, stumbles upon a pulsating dragon egg during a scavenging run. He grapples with whether to protect it or preserve his anonymity."
            )
            default_scene = Scene(
                scene_number=1,
                summary="Shade discovers the dragon egg in an abandoned research facility.",
                characters=["Shade"],
                setting="Abandoned research facility in Neo-London",
                goal="Introduce the protagonist and the discovery that changes everything",
                emotional_beat="Wonder mixed with apprehension"
            )
            default_chapter.scenes.append(default_scene)
            project_knowledge_base.add_chapter(default_chapter)
            project_knowledge_base.num_chapters = 1
            logger.info("Created default chapter with scene")
        else:
            project_knowledge_base.num_chapters = chapter_count
            logger.info(f"Successfully processed {chapter_count} chapters")

        if isinstance(project_knowledge_base.num_chapters, int) and project_knowledge_base.num_chapters <= 1:
            try:
                full_text = outline_markdown.lower()
                if "chapter list" in full_text:
                    import re
                    chapter_count_patterns = [
                        r'(\d+)\s+chapters',
                        r'total\s+chapters:\s*(\d+)',
                        r'chapter\s+list\s*[\(:]?\s*(\d+)'
                    ]
                    for pattern in chapter_count_patterns:
                        matches = re.search(pattern, full_text)
                        if matches:
                            estimated_chapters = int(matches.group(1))
                            if 1 <= estimated_chapters <= max_chapters:
                                project_knowledge_base.num_chapters = estimated_chapters
                                logger.info(f"Extracted estimated chapter count: {estimated_chapters}")
                                break
            except Exception as e:
                logger.error(f"Error extracting chapter count from text: {e}")

    def _generate_arc_milestones(self, pkb: ProjectKnowledgeBase) -> None:
        """After outline is complete, generate story arcs with milestones mapped to chapters."""
        try:
            chapter_summaries = []
            for ch_num in sorted(pkb.chapters.keys()):
                ch = pkb.chapters[ch_num]
                chapter_summaries.append(f"Chapter {ch_num}: {ch.title} - {ch.summary[:200]}")

            if not chapter_summaries:
                return

            outline_summary = "\n".join(chapter_summaries)
            prompt = f"""Analyze this book outline and identify 1-3 major story arcs with milestones.

Book: "{pkb.title}" ({pkb.genre})
Description: {pkb.description}

Chapters:
{outline_summary}

Return a JSON array of story arcs. Each arc has:
- name: arc name
- description: what this arc is about
- arc_type: "main" or "subplot"
- characters_involved: list of character names
- milestones: array of milestone objects with:
  - name: milestone name
  - milestone_type: one of "inciting_incident", "rising_action", "climax", "falling_action", "resolution"
  - target_chapter: chapter number where this should occur
  - description: what happens

Return ONLY valid JSON array, no markdown wrapper."""

            self.emit("log", {"level": "info", "message": "Generating story arc milestones..."})
            response = self.llm_client.generate_content_with_json_repair(prompt, max_tokens=3000, temperature=0.5)
            if not response:
                return

            arcs_data = extract_json_from_markdown(response)
            if not arcs_data or not isinstance(arcs_data, list):
                return

            for arc_data in arcs_data:
                milestones = []
                for m in arc_data.get("milestones", []):
                    milestones.append(ArcMilestone(
                        name=m.get("name", ""),
                        milestone_type=m.get("milestone_type", "rising_action"),
                        target_chapter=m.get("target_chapter"),
                        description=m.get("description", ""),
                        status="pending",
                    ))

                arc = StoryArc(
                    name=arc_data.get("name", ""),
                    description=arc_data.get("description", ""),
                    arc_type=arc_data.get("arc_type", "main"),
                    chapters_involved=sorted(set(
                        m.target_chapter for m in milestones if m.target_chapter
                    )),
                    characters_involved=arc_data.get("characters_involved", []),
                    status="active",
                    milestones=milestones,
                )
                if arc.name:
                    pkb.add_story_arc(arc)
                    self.emit("log", {"level": "info", "message": f"Created arc: {arc.name} with {len(milestones)} milestones"})

        except Exception as e:
            logger.warning(f"Failed to generate arc milestones: {e}")

    def execute_partial(
        self,
        pkb: ProjectKnowledgeBase,
        locked_chapters: list[int],
        regenerate_chapters: list[int],
    ) -> None:
        """Regenerates outlines for specific chapters while keeping locked chapters fixed."""
        try:
            locked_context = []
            for ch_num in sorted(locked_chapters):
                ch = pkb.get_chapter(ch_num)
                if ch:
                    locked_context.append(
                        f"Chapter {ch_num}: {ch.title}\nSummary: {ch.summary}"
                    )

            locked_text = "\n\n".join(locked_context) if locked_context else "None"
            regen_nums = ", ".join(str(n) for n in regenerate_chapters)

            prompt = f"""You are regenerating specific chapters of a book outline.

Book: "{pkb.title}" ({pkb.genre}, {pkb.category})
Description: {pkb.description}

The following chapters are LOCKED and must not change (use them as context for continuity):
{locked_text}

Regenerate outlines for chapters: {regen_nums}

For EACH regenerated chapter, provide:
## Chapter [number]: [Title]
### Summary
[Detailed chapter summary, 1-2 paragraphs]

### Key Events
- [Event 1]
- [Event 2]
- [Event 3]

Ensure the regenerated chapters maintain continuity with the locked chapters.
IMPORTANT: The content should be written entirely in {pkb.language}.
"""
            self.emit("log", {"level": "info", "message": f"Regenerating chapters {regen_nums}..."})
            response = self.llm_client.generate_content(prompt, max_tokens=3000, temperature=0.5)
            if not response:
                self.emit("log", {"level": "error", "message": "Failed to regenerate outline."})
                return

            # Parse regenerated chapters
            max_chapters = max(regenerate_chapters) if regenerate_chapters else 20
            temp_pkb = ProjectKnowledgeBase(project_name="_temp")
            self.process_outline(temp_pkb, response, max_chapters)

            # Replace only unlocked chapters
            for ch_num, ch in temp_pkb.chapters.items():
                if ch_num in regenerate_chapters:
                    pkb.chapters[ch_num] = ch
                    self.emit("log", {"level": "info", "message": f"Regenerated Chapter {ch_num}: {ch.title}"})

            # Regenerate scene outlines for changed chapters
            for ch_num in regenerate_chapters:
                ch = pkb.get_chapter(ch_num)
                if ch:
                    self.generate_scene_outline(pkb, ch)
                    self.emit("log", {"level": "info", "message": f"Regenerated scenes for Chapter {ch_num}"})

        except Exception as e:
            logger.exception(f"Error in partial outline regeneration: {e}")
            self.emit("log", {"level": "error", "message": f"Partial regeneration failed: {e}"})
