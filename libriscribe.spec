# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for LibriScribe GUI."""

import os
from pathlib import Path

block_cipher = None
repo_root = os.path.abspath(".")

a = Analysis(
    ["src/libriscribe/server.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # Frontend build output
        ("frontend/dist", "frontend/dist"),
        # Prompt templates
        ("prompts/templates", "prompts/templates"),
        # .env example for first-run reference
        (".env.example", "."),
        # Tray icon (loaded at runtime by pystray)
        ("installer/libriscribe.ico", "installer"),
    ],
    hiddenimports=[
        "libriscribe.api.app",
        "libriscribe.api.routers.projects",
        "libriscribe.api.routers.generation",
        "libriscribe.api.routers.settings",
        "libriscribe.api.routers.lorebook",
        "libriscribe.api.routers.ws",
        "libriscribe.agents.project_manager",
        "libriscribe.agents.concept_generator",
        "libriscribe.agents.outliner",
        "libriscribe.agents.character_generator",
        "libriscribe.agents.worldbuilding",
        "libriscribe.agents.chapter_writer",
        "libriscribe.agents.editor",
        "libriscribe.agents.editor_enhanced",
        "libriscribe.agents.content_reviewer",
        "libriscribe.agents.researcher",
        "libriscribe.agents.formatting",
        "libriscribe.agents.formatting_optimized",
        "libriscribe.agents.style_editor",
        "libriscribe.agents.plagiarism_checker",
        "libriscribe.agents.fact_checker",
        "libriscribe.services.generation_service",
        "libriscribe.services.context_builder",
        "libriscribe.services.lore_sync",
        "libriscribe.services.thread_tracker",
        "libriscribe.services.job_manager",
        "libriscribe.services.streaming_bridge",
        "libriscribe.services.project_service",
        "libriscribe.retrieval.document_builder",
        "libriscribe.retrieval.keyword_index",
        "libriscribe.retrieval.cross_reference",
        "libriscribe.retrieval.index_manager",
        "libriscribe.utils.llm_client",
        "libriscribe.utils.cost_tracker",
        "libriscribe.utils.prompt_loader",
        "libriscribe.utils.prompt_integration",
        "libriscribe.utils.system_prompts",
        "libriscribe.utils.paths",
        "libriscribe.knowledge_base",
        "libriscribe.settings",
        "libriscribe.configuration",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "pydantic",
        "pydantic_settings",
        "email_validator",
        "multipart",
        "yaml",
        "bs4",
        "fpdf",
        "tenacity",
        "anthropic",
        "google.genai",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "libriscribe.runtime",
        "libriscribe.api.routers.system",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Startup splash: shown the instant the exe launches (before Python is fully up),
# giving immediate feedback while the web server boots. server.py closes it via
# pyi_splash once /api/health responds. Generated here with Pillow (a build dep)
# so there is no binary asset to commit; degrades gracefully if generation fails.
splash = None
_splash_png = os.path.join("installer", "splash.png")
try:
    from PIL import Image, ImageDraw, ImageFont

    _img = Image.new("RGB", (460, 240), (24, 24, 27))
    _draw = ImageDraw.Draw(_img)
    try:
        _title_font = ImageFont.truetype("arialbd.ttf", 34)
    except Exception:
        _title_font = ImageFont.load_default()
    _draw.text((34, 78), "LibriScribe", fill=(129, 140, 248), font=_title_font)
    _img.save(_splash_png)

    splash = Splash(
        _splash_png,
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(34, 150),
        text_size=12,
        text_color="white",
        text_default="Starting LibriScribe…",
        always_on_top=True,
    )
except Exception as _exc:  # noqa: BLE001
    print("Splash generation skipped:", _exc)
    splash = None

_icon = "installer/libriscribe.ico" if os.path.exists("installer/libriscribe.ico") else None

if splash is not None:
    exe = EXE(
        pyz,
        a.scripts,
        splash,
        [],
        exclude_binaries=True,
        name="LibriScribeGUI",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # No console window -- runs as GUI app
        icon=_icon,
    )
    coll = COLLECT(
        exe,
        splash.binaries,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="LibriScribeGUI",
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="LibriScribeGUI",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # No console window -- runs as GUI app
        icon=_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="LibriScribeGUI",
    )
