---
sidebar_position: 3
---

# Using LibriScribe

The app is organized around **projects** (one per book). Each project has a dashboard, an
outline, a chapter editor, and a lorebook, plus a brainstorm co-writer available everywhere.

## The typical workflow

1. **Create a project** — title, genre, category, and the AI provider/model for the book.
2. **Generate a concept** — a title, logline, and description you can refine.
3. **Generate the outline** — a chapter-by-chapter plan. Edit it, lock chapters you like, and
   regenerate only the rest.
4. **Build the lorebook** — characters, locations, lore, story arcs, worldbuilding. These feed
   context into every chapter. See [The Lorebook](./lorebook).
5. **Write chapters** — the pipeline drafts, edits, reviews, and formats. Human-review pauses
   let you approve or adjust along the way. Watch progress stream live.
6. **Edit & polish** — tweak prose in the chapter editor; check
   [Manuscript Stats](./stats-and-preview) for pacing and readability.
7. **Export** — save the whole project as a portable bundle, or the story as plain text. See
   [Versioning, Export & Import](./versioning-and-export).

## The project dashboard

The dashboard is mission control for a book:

- **Generate / resume / cancel** the pipeline, with live progress.
- **AI configuration** — switch the provider or model for this project at any time.
- **Search (lore retrieval)** — choose Keyword, Semantic, or Hybrid retrieval and rebuild the
  index. See [Semantic Search](./semantic-search).
- **Manuscript stats** — word counts, readability, and per-chapter pacing.
- **Versions** — snapshot the project and roll back.

## The brainstorm co-writer

A lore-aware chat panel is available on every project page. Bounce ideas around, **focus** on a
single character/location/lore/arc to develop it using the surrounding world as read-only
context, keep **multiple parallel sessions**, ground replies in your **reference material**, and
**apply** good ideas straight into the lorebook. See [Brainstorm Co-writer](./brainstorm).

## Where your work is stored

Each project is a folder under `%LOCALAPPDATA%\LibriScribe\projects\` containing
`project_data.json` (the knowledge base), chapter markdown files, and subfolders for versions,
references, and chat sessions. Everything is plain files you can back up or sync.
