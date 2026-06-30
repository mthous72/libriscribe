# LibriScribe GUI

<div align="center">

### AI-Powered Multi-Agent Book Writing System

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

</div>

---

> **Attribution:** This project is a fork of [LibriScribe](https://github.com/guerra2fernando/libriscribe) originally created by **Fernando Guerra** and **Lenxys**. The original project provided the core multi-agent architecture, CLI pipeline, LLM client, and prompt template system that this version builds upon. If you appreciate the foundational work, consider [supporting the original author](https://buymeacoffee.com/guerra2fernando).

---

## Overview

LibriScribe is a multi-agent system that uses specialized AI agents to collaboratively write long-form fiction. Agents handle concept generation, outlining, character creation, worldbuilding, chapter drafting, editing, and formatting -- orchestrated by a project manager agent that coordinates the full pipeline.

This fork extends the original CLI tool into a **web application** (FastAPI + React) and adds storytelling-quality features for better prose output.

<!-- TODO: Add screenshot of the web UI here -->

---

## What's Different in This Fork

### Web Application (v0.5.0)
- **FastAPI backend** with REST API and WebSocket streaming for real-time generation progress
- **React + TypeScript frontend** with pages for project management, chapter editing, lorebook, outline editing, and settings
- **Async generation pipeline** with pause/resume and human review support

### Storytelling Enhancements (F0-F5)
- **Writing System Prompt** -- Injects prose-quality rules into creative writing calls (ASCII-only output, no AI-obvious patterns, varied sentence structure)
- **Arc Milestones** -- Story arcs become living data: milestones are auto-generated during outlining, tracked during generation, and injected into scene context
- **Narrative Thread Tracker** -- Automatically detects plot threads, promises, and open questions after each chapter; warns about unresolved threads before the final chapter
- **Dialogue Voice Profiles** -- Each character gets a voice profile (speech patterns, vocabulary, verbal tics) that shapes how their dialogue is written
- **Scene Pacing Controls** -- Scene types (action, dialogue, introspective, exposition, transition) drive type-specific writing instructions and optional word count targets
- **Partial Outline Regeneration** -- Lock specific chapters and regenerate only the unlocked ones, preserving continuity

### Context-Aware Generation
- **Context Builder** with token budgeting assembles relevant lore, character states, continuity notes, arc milestones, and open threads into each scene prompt
- **Lore Sync** service analyzes entities for consistency and surfaces suggestions

### Inherited from Original
- Multi-provider LLM support (OpenAI, Claude, Gemini, DeepSeek, Mistral, OpenRouter)
- Configurable fallback chain for provider resilience
- External YAML prompt templates (15+ agents)
- LLM cost tracking (`llm_usage.jsonl`)
- Self-healing JSON parser for robust agent responses
- Local keyword retrieval with BM25/TF-IDF and cross-reference indexing

---

## Install (Windows)

The easiest way to use LibriScribe is the prebuilt Windows installer — **no Python, Node.js, or other prerequisites required.**

1. Go to the [**Releases**](https://github.com/mthous72/libriscribe/releases) page and download the latest `LibriScribeGUI-<version>-Setup.exe`.
2. Run the installer (a standard wizard; installs for your user account).
3. Launch **LibriScribe GUI** from the Start Menu. It starts a local web server and opens your browser at `http://127.0.0.1:8000`. A **system-tray icon** lets you open the app or quit it.
4. Open **Settings** and add an API key for any provider you want (OpenAI, Claude, Gemini, DeepSeek, Mistral, OpenRouter) — or point it at a **local LLM** (LM Studio / Ollama) via the *Local (OpenAI-compatible)* provider for fully offline, private generation.

**Where your data lives:** projects, settings (`.env`), version snapshots, and logs are stored under `%LOCALAPPDATA%\LibriScribe` (not in Program Files), so they survive upgrades. Use **Export Project** / **Import Project** on the dashboard to move a book between machines.

**Updating:** download the newer `Setup.exe` and run it over your existing install — your projects and settings are untouched.

**It runs locally:** the app is a web server bound to `127.0.0.1`; nothing leaves your machine except calls to whichever LLM provider you configure (and nothing at all if you use a local LLM).

### Building the installer yourself

Installers are produced by GitHub Actions ([`.github/workflows/build-installer.yml`](.github/workflows/build-installer.yml)): PyInstaller bundles the app with a Python runtime, then Inno Setup wraps it into a single self-contained `Setup.exe`.

- **Publish a release:** push a `v*` tag (e.g. `git tag v0.8.0 && git push origin v0.8.0`) — the workflow builds the installer and attaches it to a GitHub Release.
- **Just get an installer (no release):** Actions → *Build Windows Installer* → **Run workflow**, then download the `LibriScribeGUI-Installer` artifact.

---

## Run from source (developers)

### 1. Install

```bash
git clone https://github.com/mthous72/libriscribe.git
cd libriscribe
pip install -e .
```

### 2. Configure

Copy `.env.example` to `.env` and add your API keys:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

CLAUDE_API_KEY=your_key
CLAUDE_MODEL=claude-sonnet-4-20250514

GOOGLE_AI_STUDIO_API_KEY=your_key
GOOGLE_AI_STUDIO_MODEL=gemini-2.5-flash

# Optional: OpenRouter, DeepSeek, Mistral
# Optional: FALLBACK_CHAIN=claude,openrouter/anthropic/claude-3-haiku
```

### 3. Launch

```bash
libriscribe
```

This starts the web server at `http://127.0.0.1:8000` and opens your browser.

### Development (frontend)

```bash
cd frontend && npm install && npm run dev
```

Vite dev server runs at `http://localhost:5173` and proxies API calls to the backend.

---

## Architecture

```
Browser (React + Vite + TypeScript)
    |
    +-- REST API (axios) + WebSocket
    |
FastAPI (uvicorn, :8000)
    |
    +-- asyncio.to_thread()
    |
Agent Pipeline (sync Python)
    |
    +-- ProjectManagerAgent (orchestrator)
    |       |-- ConceptGeneratorAgent
    |       |-- OutlinerAgent
    |       |-- CharacterGeneratorAgent
    |       |-- WorldbuildingAgent
    |       |-- ChapterWriterAgent + ContextBuilder
    |       |-- EditorAgent
    |       |-- ContentReviewerAgent
    |       +-- FormattingAgent
    |
    +-- LLMClient (unified, multi-provider)
    |       +-- CostTracker -> llm_usage.jsonl
    |
    +-- Retrieval System (keyword index, cross-refs)
```

### Key directories

```
src/libriscribe/
    agents/          # All specialized agents
    api/             # FastAPI routers, schemas, dependencies
    services/        # Generation pipeline, context builder, lore sync, thread tracker
    retrieval/       # Document builder, keyword index, cross-references
    utils/           # LLM client, cost tracker, system prompts, prompt loader
frontend/            # React + Vite + Tailwind
prompts/templates/   # External YAML prompt templates
projects/            # Runtime output (generated books)
tests/               # Unit tests
```

---

## Project Output

Each generated book project produces:

```
projects/your_project/
    project_data.json          # Full project knowledge base (characters, arcs, threads, etc.)
    .libriscribe_status.json   # Pipeline checkpoint state
    outline.md                 # Chapter-by-chapter outline
    characters.json            # Character profiles with voice data
    world.json                 # Worldbuilding details
    chapter_1.md ... chapter_N.md
    research_results.md
```

---

## Running Tests

```bash
PYTHONPATH=src python -m pytest tests/
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

Originally created by [Fernando Guerra](https://github.com/guerra2fernando) and Lenxys | Fork maintained by [mthous72](https://github.com/mthous72)

</div>
