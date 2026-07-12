---
sidebar_position: 1
---

# Introduction

**LibriScribe** is an AI-powered, multi-agent book-writing application. Specialized agents
collaborate — concept, outline, characters, worldbuilding, chapter drafting, editing,
formatting — orchestrated by a project manager agent that runs the whole pipeline.

This documentation covers the **web-app fork**: the original command-line tool has been
extended into a local **desktop/web application** (FastAPI + React) built around the
**Story Workbench** — work through every piece of your book one item at a time, with small,
human-approved AI actions — plus a one-click Windows installer, live provider/model selection,
local-LLM support, a lore-aware brainstorm co-writer, versioning, portable export/import, and
semantic search over your own reference material.

## What you get

- **Runs locally.** A web server on `127.0.0.1` with a browser UI and a system-tray icon.
  Nothing leaves your machine except calls to whichever LLM provider you configure — and
  nothing at all if you use a local model.
- **The Story Workbench** — a story tree of every object (concept, outline, chapters, scenes,
  lore, arcs, milestones), a per-item editor with Prev/Next to walk the story in order, and
  per-item AI actions that always show you the result before anything saves: rewrite one
  scene, draft one voice profile, generate one world field.
- **Honest milestones** — the AI grades whether your prose actually delivered each planned
  story beat, with quoted evidence; you approve every flag.
- **Multi-agent generation** when you want it — concept → outline → chapters → formatting as
  a directed pipeline, plus opt-in batch tools for seeding a cast or world.
- **A living lorebook** — characters (with dialogue voice profiles), locations, codex entries,
  story arcs, worldbuilding — with cross-references, search, and a review sandbox so AI
  suggestions never overwrite your canon.
- **A brainstorm co-writer** docked beside your work: its focus follows whatever you select —
  a scene, a character, the concept — and it turns ideas into structured, reviewed changes.
- **Bring-your-own sources** — import reference PDFs/text (with OCR for scans) and ground the
  AI in them without polluting your canon.
- **Your data stays yours** — export/import a whole project as one file, snapshot versions and
  roll back, and read everything as plain files under `%LOCALAPPDATA%\LibriScribe`.

## Where to go next

- **[Getting Started](./getting-started)** — install the Windows app (or run from source) and
  create your first project.
- **[Using LibriScribe](./usage)** — the end-to-end workflow.
- **[The Story Workbench](./workbench)** — the project view, item by item.
- **[Providers & Models](./providers-and-models)** — cloud providers, live model lists, and
  local (offline) LLMs.
- **[The Lorebook](./lorebook)**, **[Brainstorm Co-writer](./brainstorm)**,
  **[Semantic Search & Local Embeddings](./semantic-search)**,
  **[Versioning, Export & Import](./versioning-and-export)**, and
  **[Manuscript Stats & Prompt Preview](./stats-and-preview)**.

## Credits

This project is a fork of [LibriScribe](https://github.com/guerra2fernando/libriscribe) by
**Fernando Guerra** and **Lenxys**, which provided the core multi-agent architecture, LLM
client, and prompt system. Several of the fork's features (semantic retrieval, bring-your-own
reference RAG, OCR, and multi-session brainstorming) were inspired by
[Writingway](https://github.com/a-omukai/Writingway) by **a-omukai** (MIT) — a kindred
open-source AI writing tool; support them via their
[Discord](https://discord.gg/xkkGaRFXNX).
