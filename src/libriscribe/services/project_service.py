"""Project CRUD operations."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from libriscribe.knowledge_base import ProjectKnowledgeBase, Location
from libriscribe.settings import Settings
from libriscribe.workflow_state import inspect_project_progress
from libriscribe.utils.file_utils import get_existing_chapter_numbers


def get_projects_dir() -> Path:
    settings = Settings()
    return Path(settings.projects_dir)


def list_projects() -> list[dict[str, Any]]:
    """Lists all projects with summary info."""
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return []

    summaries = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir():
            continue
        project_data_path = entry / "project_data.json"
        if not project_data_path.exists():
            continue
        kb = ProjectKnowledgeBase.load_from_file(str(project_data_path))
        if not kb:
            continue

        progress = inspect_project_progress(entry, kb)
        existing_chapters = get_existing_chapter_numbers(entry)
        total = kb.num_chapters
        if isinstance(total, tuple):
            total = total[1]

        summaries.append({
            "project_name": kb.project_name,
            "title": kb.title,
            "genre": kb.genre,
            "category": kb.category,
            "language": kb.language,
            "next_step": progress.next_step,
            "chapter_count": len(existing_chapters),
            "total_chapters": total if isinstance(total, int) else 0,
        })
    return summaries


def get_project_detail(project_name: str) -> dict[str, Any] | None:
    """Returns detailed project info."""
    project_dir = get_projects_dir() / project_name
    project_data_path = project_dir / "project_data.json"
    if not project_data_path.exists():
        return None
    kb = ProjectKnowledgeBase.load_from_file(str(project_data_path))
    if not kb:
        return None

    progress = inspect_project_progress(project_dir, kb)
    existing_chapters = get_existing_chapter_numbers(project_dir)

    return {
        "project_name": kb.project_name,
        "title": kb.title,
        "genre": kb.genre,
        "description": kb.description,
        "category": kb.category,
        "language": kb.language,
        "num_characters": kb.num_characters,
        "worldbuilding_needed": kb.worldbuilding_needed,
        "review_preference": kb.review_preference,
        "book_length": kb.book_length,
        "logline": kb.logline,
        "tone": kb.tone,
        "target_audience": kb.target_audience,
        "num_chapters": kb.num_chapters,
        "llm_provider": kb.llm_provider,
        "model": kb.model,
        "outline": kb.outline,
        "next_step": progress.next_step,
        "chapter_count": len(existing_chapters),
        "stage_statuses": progress.stage_statuses,
    }


def create_project(data: dict[str, Any]) -> dict[str, Any]:
    """Creates a new project on disk."""
    from libriscribe.agents.project_manager import ProjectManagerAgent

    kb = ProjectKnowledgeBase(**data)
    pm = ProjectManagerAgent()
    pm.initialize_project_with_data(kb)

    # Backfill locations from worldbuilding
    backfill_locations(kb)
    if kb.locations:
        pm.save_project_data()

    return get_project_detail(kb.project_name) or {"project_name": kb.project_name}


def delete_project(project_name: str) -> bool:
    """Deletes a project directory."""
    import shutil
    project_dir = get_projects_dir() / project_name
    if project_dir.exists():
        shutil.rmtree(project_dir)
        return True
    return False


def load_kb(project_name: str) -> ProjectKnowledgeBase | None:
    """Loads and returns the KB for a project."""
    project_dir = get_projects_dir() / project_name
    project_data_path = project_dir / "project_data.json"
    if not project_data_path.exists():
        return None
    return ProjectKnowledgeBase.load_from_file(str(project_data_path))


def save_kb(project_name: str, kb: ProjectKnowledgeBase) -> None:
    """Saves the KB to disk."""
    project_dir = get_projects_dir() / project_name
    kb.project_dir = project_dir
    file_path = str(project_dir / "project_data.json")
    kb.save_to_file(file_path)


def backfill_locations(kb: ProjectKnowledgeBase) -> None:
    """Auto-populate locations from worldbuilding.key_locations."""
    if kb.worldbuilding and kb.worldbuilding.key_locations and not kb.locations:
        for loc_name in kb.worldbuilding.key_locations.replace("\n", ",").split(","):
            loc_name = loc_name.strip()
            if loc_name and loc_name not in kb.locations:
                kb.locations[loc_name] = Location(name=loc_name)
