---
sidebar_position: 1
---

# Introduction

**LibriScribe** is an AI-powered, multi-agent book-writing application. Specialized agents
collaborate — concept, outline, characters, worldbuilding, chapter drafting, editing,
formatting — orchestrated by a project manager agent that runs the whole pipeline.

This documentation covers the **web-app fork**: the original command-line tool has been
extended into a local **desktop/web application** (FastAPI + React) with a one-click Windows
installer, live provider/model selection, local-LLM support, a lore-aware brainstorm
co-writer, versioning, portable export/import, semantic search over your own reference
material, and more.

## What you get

- **Runs locally.** A web server on `127.0.0.1` with a browser UI and a system-tray icon.
  Nothing leaves your machine except calls to whichever LLM provider you configure — and
  nothing at all if you use a local model.
- **Multi-agent generation** from concept → outline → characters → worldbuilding → chapters →
  editing → formatting.
- **A living lorebook** — characters, locations, lore entries, story arcs, worldbuilding — with
  cross-references and search.
- **A brainstorm co-writer** that sees your lore, can focus on a single entity, keeps multiple
  parallel chat sessions, and turns ideas into structured lore.
- **Bring-your-own sources** — import reference PDFs/text (with OCR for scans) and ground the
  AI in them without polluting your canon.
- **Your data stays yours** — export/import a whole project as one file, snapshot versions and
  roll back, and read everything as plain files under `%LOCALAPPDATA%\LibriScribe`.

## Where to go next

- **[Getting Started](./getting-started)** — install the Windows app (or run from source) and
  create your first project.
- **[Using LibriScribe](./usage)** — the end-to-end workflow.
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
