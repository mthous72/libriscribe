"""Path resolution for both development and PyInstaller frozen bundles."""
from __future__ import annotations

import sys
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


def get_frontend_dist() -> Path:
    return get_base_dir() / "frontend" / "dist"


def get_prompts_dir() -> Path:
    return get_base_dir() / "prompts"


def get_default_projects_dir() -> Path:
    """Projects dir lives next to the executable when frozen, else in repo root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "projects"
    return get_base_dir() / "projects"


def get_default_env_path() -> Path:
    """The .env file lives next to the executable when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / ".env"
    return get_base_dir() / ".env"
