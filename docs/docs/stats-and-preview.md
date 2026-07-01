---
sidebar_position: 9
---

# Manuscript Stats & Prompt Preview

Two tools for understanding your book and what the AI sees — both run locally with no LLM calls.

## Manuscript statistics

The **Manuscript stats** card on the project dashboard computes readability and length metrics
across your chapters (click **Load stats**):

- **Counts** — total words, chapters, average sentence length.
- **Readability** — **Flesch Reading Ease** (higher = easier; ~60–70 is plain English) and
  **Flesch-Kincaid grade** (approximate US school grade level).
- **Style ratios** — share of text that's dialogue, and the proportion of `-ly` adverbs.
- **Reading time** — an estimate for the whole book.
- **Per-chapter pacing** — a length bar and reading-ease per chapter, to spot outliers (a
  chapter that's unusually long, or suddenly much denser than its neighbors).

These are quick, dependency-free estimates meant to guide revision — not exact linguistic
measures.

## Prompt / context preview

Ever wonder exactly what the model receives? Preview it before spending a token:

- **Brainstorm drawer → Preview prompt** — the fully assembled system prompt for the co-writer:
  the lore context and any reference material, for your current message and Focus.
- **Chapter editor → Preview AI context** — the context that `ContextBuilder` injects into the
  chapter-writing prompt: character profiles, previous-chapter recaps, relevant lore, arc
  milestones, retrieved passages, and reference material, with a token estimate.

Neither makes an LLM call. It's a transparency and debugging aid — if a chapter isn't picking up
a piece of lore, the preview shows whether it made it into the context.
