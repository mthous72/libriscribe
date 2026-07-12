---
sidebar_position: 3
---

# Using LibriScribe

The app is organized around **projects** (one per book). Opening a project lands you in the
[**Story Workbench**](./workbench) — a three-pane view where you work through the whole book
one item at a time. Two utility pages sit alongside it: **Automation** (batch generation,
exports, versions, model settings) and **Lore tools** (import, sandbox review, gap scans,
references, graph).

## The typical workflow

1. **Create a project** — title, genre, category, and the AI provider/model for the book.
2. **Shape the concept** — select the Concept node in the workbench tree; edit it directly,
   brainstorm it in the docked chat, or run the concept stage and apply/dismiss its
   suggestions field by field.
3. **Build the outline** — generate it, then refine chapter by chapter: **Develop remaining**
   fills in placeholder chapters additively; locks protect what you've settled.
4. **Grow the lorebook as you go** — characters, locations, codex entries, world fields, arcs
   with milestones. These feed context into every chapter. Voice profiles shape each
   character's dialogue. See [The Lorebook](./lorebook).
5. **Write chapters — or single scenes.** Run a whole chapter from its editor (or the
   Automation page), or take the smallest bite: **Write scene** drafts one scene with full
   story context and shows you a diff before anything saves.
6. **Verify the story is landing** — **Check milestones** grades whether each chapter's prose
   actually delivered its planned beats; you approve every flag.
7. **Edit & polish** — revise prose with AI diffs (chapter- or scene-level) or by hand; check
   [Manuscript Stats](./stats-and-preview) for pacing and readability.
8. **Export** — the whole project as a portable bundle, the story as text, or a DOCX
   manuscript. See [Versioning, Export & Import](./versioning-and-export).

Steps 2–7 aren't a one-way street: the workbench is built for going **back** — sharpen an
early scene, rename a character trait, re-target a milestone — without touching anything you
wrote afterward.

## The three surfaces

- **[Story Workbench](./workbench)** — the project view. The story tree, per-item editors
  with Prev/Next, per-item AI actions, and the docked brainstorm chat.
- **Automation** — run-level generation (next step / specific chapter / run all / reset),
  batch cast & world tools for seeding a new project, AI/model configuration per project,
  retrieval mode ([Semantic Search](./semantic-search)), manuscript stats, versions, exports.
- **Lore tools** — whole-lorebook utilities: JSON import (format-aware, with auto-repair),
  the review **sandbox** where AI-proposed lore waits for your accept/reject, structural and
  AI gap scans, reference material (PDF/TXT/OCR), and the cross-reference graph.

## The brainstorm co-writer

The lore-aware chat is docked into the workbench (and available as a drawer on the utility
pages). Its focus **follows your selection** — select a scene, chat about that scene — and
good ideas apply straight into the focused item or the lorebook, always via review. See
[Brainstorm Co-writer](./brainstorm).

## Where your work is stored

Each project is a folder under `%LOCALAPPDATA%\LibriScribe\projects\` containing
`project_data.json` (the knowledge base), chapter markdown files, and subfolders for versions,
references, and chat sessions. Everything is plain files you can back up or sync.
