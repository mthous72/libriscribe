"""B45 Slice 3: write/rewrite ONE scene of a chapter — the smallest prose bite.

Reuses ChapterWriterAgent's single shared prompt stack (_build_scene_prompt: register >
canon > all-scenes recap > continuity tail > repetition-guard ban list > scene brief) and its
freshness enforcement, but scoped to one scene. Mirrors revision.revise_chapter's contract:
returns {original, revised} WITHOUT saving — the author diffs and keeps or discards.
"""
from __future__ import annotations

from pathlib import Path


def write_scene(kb, project_dir: Path, chapter_number: int, scene_number: int,
                guidance: str = "") -> dict | None:
    """Generate prose for one scene. Returns {original, revised} or None when generation
    fails. Raises ValueError for structural problems (missing scene, unstructured chapter)."""
    from libriscribe.agents.chapter_writer import ChapterWriterAgent
    from libriscribe.services.project_service import create_llm_client
    from libriscribe.services.context_builder import ContextBuilder
    from libriscribe.services.scene_prose import read_chapter_split
    from libriscribe.utils.prose_sanitizer import sanitize_prose, strip_summary_echo

    chapter = kb.get_chapter(chapter_number)
    if not chapter:
        raise ValueError(f"Chapter {chapter_number} is not in the outline")
    scene = next((s for s in chapter.scenes if s.scene_number == scene_number), None)
    if not scene:
        raise ValueError(f"Scene {scene_number} is not in Chapter {chapter_number}'s outline")

    kb.project_dir = str(project_dir)  # the agent's prose readers resolve through this
    agent = ChapterWriterAgent(create_llm_client(kb))
    try:
        from libriscribe.services.retrieval_service import search_service_for
        svc = search_service_for(project_dir, kb)
    except Exception:
        svc = None
    agent.context_builder = ContextBuilder(kb, svc)

    split = read_chapter_split(project_dir, chapter_number)
    if split is not None and split.unstructured:
        raise ValueError("This chapter's prose has no scene markers — use chapter-level revise instead.")
    bodies = {b.scene_number: b.body for b in split.scenes} if split else {}

    ordered = sorted(chapter.scenes, key=lambda s: s.scene_number)
    prev_tail = agent._prev_chapter_tail(kb, chapter_number)
    before = [bodies[s.scene_number] for s in ordered
              if s.scene_number < scene_number and s.scene_number in bodies]
    written = "\n\n".join(before)
    prior = written if written else prev_tail
    # Guard against repeating ANY other prose in play: previous chapter's tail plus every
    # OTHER scene of this chapter (later scenes matter on a mid-chapter rewrite).
    others = [bodies[n] for n in sorted(bodies) if n != scene_number]
    guard_context = "\n\n".join(x for x in [prev_tail, *others] if x).strip()
    recap = agent._prev_chapters_recap_entries(kb, chapter_number) + [
        (f"Scene {s.scene_number}", s.summary or "", bodies[s.scene_number])
        for s in ordered if s.scene_number < scene_number and s.scene_number in bodies
    ]

    prompt, max_tokens = agent._build_scene_prompt(
        kb, chapter, scene, len(ordered), prior,
        recap_entries=recap, guard_prose=guard_context,
    )
    if guidance and guidance.strip():
        prompt += f"\n\nAUTHOR'S DIRECTION FOR THIS SCENE:\n{guidance.strip()}"
    sys_prompt = agent._get_system_prompt(kb)

    content = agent.llm_client.generate_content(prompt, max_tokens=max_tokens, system_prompt=sys_prompt)
    if not content or not content.strip():
        return None
    content = sanitize_prose(strip_summary_echo(content, scene.summary))
    content = agent._enforce_freshness(content, scene, prompt, sys_prompt, guard_context, max_tokens)

    return {"original": bodies.get(scene_number, ""), "revised": content}
