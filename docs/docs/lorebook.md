---
sidebar_position: 5
---

# The Lorebook

The lorebook is your project's living knowledge base. It feeds context into every chapter the
AI writes and into the brainstorm co-writer. **All character and world work happens here** —
it's authored lore, not a generation stage: the AI can propose, but every change to your canon
goes through your review.

Day to day you edit lore entities **in the [Story Workbench](./workbench) tree** (Characters,
Locations, Codex, World, Arcs, Threads sections). The **Lore tools** page (top-right in the
workbench) hosts the whole-lorebook utilities described below — import, the review sandbox,
gap scans, reference material, and the cross-reference graph — alongside the same entity tabs.

## Entities

- **Characters** — role, appearance, personality, background, motivations, arcs,
  relationships, and a **voice profile** (speech patterns, vocabulary, verbal tics, sample
  lines) that shapes their dialogue. **Generate voice profile** drafts one with AI — reviewed
  in the editor before you save.
- **Locations** — description, significance, associated characters.
- **Codex** — factions, organizations, items, technology, concepts, events, rules (the named
  world entities that aren't people, places, or plots).
- **Arcs** — story arcs with **milestones**: planned beats targeted at chapters, whose
  completion is AI-verified against the actual prose and approved by you (see
  [the Workbench](./workbench#honest-milestones)).
- **Worldbuilding** — a per-field world bible, with per-field AI generation.
- **Threads** (auto-detected plot promises) and a cross-reference **Graph**.

Each entity can be edited directly, analyzed by AI for consistency, or sent to the brainstorm
co-writer with **Brainstorm this**. Batch cast/world generation for seeding a brand-new
project lives on the **Automation** page; anything it produces that collides with existing
lore is staged in the sandbox for review, never merged automatically.

## Importing lore (including from other tools)

Use **Import JSON** to bring in lore from a file. The importer is format-aware and will detect:

- **LibriScribe bundles** and generic `{characters, locations, lore, arcs}` JSON,
- **SillyTavern / TavernAI character cards** (V1 and V2, including the embedded
  `character_book`),
- **KoboldAI / SillyTavern World Info** lorebooks — `entries` maps/lists, and full **KoboldAI
  save files** (lore under `worldinfo`; the rest of the game state is ignored).

Toggle **AI-map** to have the LLM re-classify and enrich entries from unfamiliar formats. It
reasons about each entry one at a time before assigning it to a category, so a World-Info blob
where everything is lumped together gets sorted properly (people to characters, places to
locations, factions/items/concepts to lore). Unknown shapes fall back to pure-LLM mapping.

### Review before it's saved

Import (and the brainstorm **Apply to lore**) never writes blindly. You get a **review panel**:
records grouped by category, each with a **New** or **Update** badge, editable fields, and a
checkbox. On apply, existing entries are **smart-merged** — empty fields are filled, clearly
revised fields are updated, and **anything not mentioned is preserved**. Nothing is overwritten
that you didn't touch.

## Reference material (bring-your-own sources)

The **References** tab lets you import external **source documents** — a research folder, a
style guide, a prior book's "series bible":

- Supported: **PDF, TXT, Markdown**, and — via OCR — **scanned PDFs and images**
  (PNG/JPG/TIFF…). See OCR setup below.
- References are indexed as a **distinct source**: the AI uses them as **background/citation,
  never as canon lore**, and they're **excluded from exports**.
- They ground both chapter generation and the brainstorm co-writer (with a toggle). Retrieval
  from references is much stronger with **Semantic/Hybrid** search enabled — see
  [Semantic Search](./semantic-search).
- Large files are processed in the background; each reference shows a status (processing /
  ready / error) and an **OCR** badge when applicable.

### OCR for scanned documents

Scanned PDFs and images are read with **Tesseract OCR** (pages are rasterized with PyMuPDF).
The Windows installer bundles Tesseract, so OCR works out of the box. Running from source? OCR
activates when the Tesseract binary is installed and on your `PATH` (or pointed to via the
`TESSERACT_CMD` environment variable). Without it, text and text-PDF imports still work; scanned
imports report a clear "OCR unavailable" message.
