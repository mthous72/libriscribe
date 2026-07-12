# LibriScribe GUI

<div align="center">

### AI-Powered Multi-Agent Book Writing System

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

</div>

---

> **Attribution:** This project is a fork of [LibriScribe](https://github.com/guerra2fernando/libriscribe) originally created by **Fernando Guerra** and **Lenxys**. The original project provided the core multi-agent architecture, CLI pipeline, LLM client, and prompt template system that this version builds upon. If you appreciate the foundational work, consider [supporting the original author](https://buymeacoffee.com/guerra2fernando).
>
> Several of this fork's features — semantic retrieval, bring-your-own reference RAG, OCR, and multi-session brainstorming — were inspired by [Writingway](https://github.com/a-omukai/Writingway) by **a-omukai** (MIT), a kindred open-source AI writing tool. Support them via their [Discord](https://discord.gg/xkkGaRFXNX).

---

## Overview

LibriScribe is a multi-agent system that uses specialized AI agents to collaboratively write long-form fiction. Agents handle concept generation, outlining, character creation, worldbuilding, chapter drafting, editing, and formatting -- orchestrated by a project manager agent that coordinates the full pipeline.

This fork extends the original CLI tool into a **web application** (FastAPI + React) built around the **Story Workbench**: a three-pane view (story tree · item editor · brainstorm chat) where you work through every piece of your book — concept, outline, chapters, scenes, characters, world, arcs, milestones — **one item at a time**, with small, human-approved AI actions instead of one big batch pipeline.

<!-- TODO: Add screenshot of the web UI here -->

---

## What's Different in This Fork

### The Story Workbench (v0.14.0)

The project view is a **three-pane workbench**: an ordered story tree on the left (Concept →
Outline → Chapters ▸ Scenes → Characters → Locations → Codex → World → Arcs ▸ Milestones →
Threads), a per-item editor in the center with Prev/Next to walk the story in order, and the
brainstorm co-writer **docked** on the right with focus that follows your selection.

- **Every object is editable in place** — down to a single scene's brief or one milestone's
  status — and every selection is a shareable URL (`?sel=scene:3.2`)
- **Small-bite AI actions, always propose → review → save:** write/rewrite **one scene**
  (diff, then spliced into just that scene's block), develop one chapter's scene briefs,
  generate one character's voice profile, generate one worldbuilding field
- **Honest milestones** — an AI check grades whether a chapter's prose *actually delivered*
  each planned story beat, citing an exact quote as evidence (fabricated quotes are
  auto-downgraded). Verdicts are proposals: you accept, dismiss, or flip any flag manually
- **Edit early, never break late** — editing an item never regenerates anything downstream;
  impact hints show where an entity is referenced later
- **The pipeline slimmed to concept → outline → chapters → formatting** — character and world
  work lives in the lorebook as approve-only actions; batch cast/world generation survives as
  opt-in tools on the Automation page (the old dashboard)

### Prose Quality & Local-Model Reliability (v0.13.0–v0.14.0)

- **Deterministic prose sanitation** — mojibake repair, think-block stripping, outline-echo
  removal; scaffolding (scene titles, summaries) never reaches the reader
- **Repetition guard** — a named ban list of overused phrases and scene openings from
  everything written so far, plus a whole-book scene recap in every prompt, plus a
  deterministic post-check that regenerates a scene once with its violations named
- **Reasoning/thinking model support** (Qwen, Hermes, …) — thinking tokens are budgeted as a
  first-class cost with escalating retries and a learned per-model allowance; `<think>` blocks
  are stripped safely even across streaming chunk boundaries
- **Lore-safe generation** — the character/worldbuilding generators never overwrite your lore;
  collisions are staged in the sandbox as suggestions you explicitly approve
- **Import auto-repair** — damaged JSON (merge debris, missing commas, BOM, mojibake) is fixed
  on import with a human-readable list of every repair made

### Web Application (v0.5.0)
- **FastAPI backend** with REST API and WebSocket streaming for real-time generation progress
- **React + TypeScript frontend** with pages for project management, chapter editing, lorebook, outline editing, and settings
- **Async generation pipeline** with pause/resume and human review support

### Storytelling Enhancements (F0-F5)
- **Writing System Prompt** -- Injects prose-quality rules into creative writing calls (ASCII-only output, no AI-obvious patterns, varied sentence structure)
- **Arc Milestones** -- Story arcs become living data: milestones are auto-generated during outlining and injected into scene context; since v0.14.0 completion is AI-verified against the actual prose and human-approved (see the Workbench above)
- **Narrative Thread Tracker** -- Automatically detects plot threads, promises, and open questions after each chapter; warns about unresolved threads before the final chapter
- **Dialogue Voice Profiles** -- Each character gets a voice profile (speech patterns, vocabulary, verbal tics) that shapes how their dialogue is written
- **Scene Pacing Controls** -- Scene types (action, dialogue, introspective, exposition, transition) drive type-specific writing instructions and optional word count targets
- **Partial Outline Regeneration** -- Lock specific chapters and regenerate only the unlocked ones, preserving continuity

### Context-Aware Generation
- **Context Builder** with token budgeting assembles relevant lore, character states, continuity notes, arc milestones, and open threads into each scene prompt
- **Lore Sync** service analyzes entities for consistency and surfaces suggestions

### Desktop app, providers & co-writer (v0.6.0–v0.8.0)

**Packaging & reliability (v0.6.0)**
- One-click **Windows installer** (no prerequisites); **single-instance** launch, **system-tray** open/quit, and a startup splash
- User data (projects, `.env`, versions, logs) lives under `%LOCALAPPDATA%\LibriScribe` and survives upgrades

**Providers & models (v0.6.0)**
- **Model dropdowns** populated live from each provider's API (free models flagged)
- **Local / OpenAI-compatible provider** (LM Studio, Ollama, llama.cpp, …) for fully offline, private generation
- Switch the AI **per project**; cleaner Settings (providers off until a real key is added)

**Brainstorm co-writer (v0.7.0)**
- Lore-aware **side-panel chat** with a **Focus** mode — develop a specific character/location/lore/arc using the surrounding world (companions, arcs, world lore) as read-only context
- **Apply to lore** turns a brainstormed idea into a draft Character/Location/Lore/Arc (optionally LLM-extracted into typed fields)
- **Lore JSON import**

**Backup, versioning & portability (v0.8.0)**
- **Project Export / Import** as a single self-contained `.libriscribe.json` bundle, plus **Story `.txt`** export
- **Version snapshots** with reversible **rollback**
- **"Brainstorm this"** button on each lore entry; new-project wizard **draft persistence**
- Backend **test suite** run automatically by CI

**Smart lore intake (v0.8.0)**
- **Smart Apply** — a brainstorm reply is parsed into multiple lore records across categories (characters, locations, lore, arcs) with the right fields, shown in a **review panel** (New/Update badges, editable, per-record checkboxes) before anything is saved
- **Smart import** of lore JSON from other tools — **SillyTavern** character cards & World Info, **KoboldAI** World Info, or our own bundle — auto-detected and mapped into your lorebook (with an optional AI-map pass for unknown formats), also via the same review panel
- **Smart merge** on apply: existing entries are updated field-by-field — empty fields filled, revised fields updated, and **anything not mentioned is preserved** (never overwrites untouched data)

**Retrieval, references & co-writer upgrades (v0.9.0)**
- **Semantic & hybrid search** over your lore and prose, powered by embeddings from a cloud provider or a **local (offline) server** (LM Studio / Ollama) — chosen per book, with a safe keyword fallback
- **Bring-your-own reference material** — import **PDF / TXT / Markdown** (and **scanned PDFs / images via OCR**) as a distinct *source* that grounds brainstorming and generation but never becomes canon and is excluded from exports
- **OCR** for scanned documents via bundled **Tesseract** (no separate install in the packaged app)
- **Multiple parallel brainstorm sessions** per book — named threads, each with its own history and persistent Focus
- **Manuscript stats** — readability (Flesch), counts, dialogue/adverb ratios, and per-chapter pacing
- **Prompt / context preview** — see the exact assembled prompt and injected lore/context before spending a token (brainstorm and chapter generation)
- **Live documentation site** (Docusaurus)

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

**Where your data lives:** projects, settings (`.env`), version snapshots, and logs are stored under `%LOCALAPPDATA%\LibriScribe` (not in Program Files), so they survive upgrades. Use **Export Project** on the Automation page / **Import Project** on the home page to move a book between machines.

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
    |   pipeline: concept -> outline -> chapters -> formatting
    |   (characters & worldbuilding run as opt-in batch tools)
    |
    +-- ProjectManagerAgent (orchestrator)
    |       |-- ConceptGeneratorAgent
    |       |-- OutlinerAgent
    |       |-- CharacterGeneratorAgent   (tool / per-item voice profiles)
    |       |-- WorldbuildingAgent        (tool / per-field generation)
    |       |-- ChapterWriterAgent + ContextBuilder
    |       |-- EditorAgent
    |       |-- ContentReviewerAgent
    |       +-- FormattingAgent
    |
    +-- Per-item services (workbench actions)
    |       |-- scene_writer     (write/rewrite ONE scene, full steering stack)
    |       |-- scene_prose      (split/splice chapters at scene markers)
    |       |-- milestone_verifier (AI grades beats vs prose; user approves)
    |       +-- impact           (where is this entity referenced later?)
    |
    +-- LLMClient (unified, multi-provider, reasoning-model aware)
    |       +-- CostTracker -> llm_usage.jsonl
    |
    +-- Retrieval System (keyword/semantic index, cross-refs)
```

### Key directories

```
src/libriscribe/
    agents/          # All specialized agents
    api/             # FastAPI routers, schemas, dependencies
    services/        # Pipeline, context builder, scene writer/splicer,
                     # milestone verifier, impact scan, lore sync, sandbox
    retrieval/       # Document builder, keyword index, cross-references
    utils/           # LLM client, prose sanitizer, repetition guard,
                     # JSON repair, cost tracker, prompt loader
frontend/
    src/workbench/   # Story Workbench (tree, per-item editors, brainstorm pane)
    src/pages/       # Home, New Project, Workbench, Automation, Lore tools, Wizard, Settings
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
