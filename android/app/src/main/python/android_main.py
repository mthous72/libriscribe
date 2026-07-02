"""Chaquopy entry point for the embedded LibriScribe server.

Called from ServerService.kt as:  android_main.serve(<filesDir>)

By the time this runs, the Kotlin side has already unpacked the bundled assets
into `<filesDir>`:
    <filesDir>/frontend/dist   (the built web UI)
    <filesDir>/prompts         (agent prompt templates)

The same directory is used for writable runtime data (projects/, .env), which
is fine on Android where filesDir is private and writable.
"""
from __future__ import annotations

import os


def serve(files_dir: str) -> None:
    # Point path resolution at on-device storage (see libriscribe.utils.paths).
    os.environ.setdefault("LIBRISCRIBE_BASE_DIR", files_dir)
    os.environ.setdefault("LIBRISCRIBE_DATA_DIR", files_dir)

    # Import is deferred until the env is set so settings pick up the right dirs.
    from libriscribe.server import serve_embedded

    serve_embedded(host="127.0.0.1", port=8000)
