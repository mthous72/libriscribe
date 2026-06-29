"""Path resolution for both development and PyInstaller frozen bundles."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def get_base_dir() -> Path:
    """Return the application base directory.

    In development: the repo root (two levels up from this file).
    In a PyInstaller bundle: sys._MEIPASS (the temp extraction dir).
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    # src/libriscribe/utils/paths.py -> repo root
    return Path(__file__).resolve().parent.parent.parent.parent


def get_app_data_dir() -> Path:
    """User-writable directory for runtime data (.env, projects).

    Frozen builds install under Program Files, which is read-only for standard
    users, so writable data must live elsewhere: %LOCALAPPDATA%\\LibriScribe
    (falling back to a temp dir). In development this is the repo root, matching
    the historical layout. The directory is created if missing.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        path = Path(base) / "LibriScribe"
    else:
        path = get_base_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_frontend_dist() -> Path:
    return get_base_dir() / "frontend" / "dist"


def get_prompts_dir() -> Path:
    return get_base_dir() / "prompts"


def get_bundled_env_example() -> Path:
    """The .env.example shipped inside the bundle (seed source on first run)."""
    return get_base_dir() / ".env.example"


def get_default_projects_dir() -> Path:
    """Projects live in the user-writable app-data dir (see get_app_data_dir)."""
    return get_app_data_dir() / "projects"


def get_default_env_path() -> Path:
    """The .env file lives in the user-writable app-data dir."""
    return get_app_data_dir() / ".env"


def get_writing_prompt_path() -> Path:
    """The global writing system prompt is stored in its own file (it is multi-line,
    which `.env`'s line-based KEY=VALUE format cannot hold)."""
    return get_app_data_dir() / "writing_system_prompt.txt"
