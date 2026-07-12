---
sidebar_position: 3.5
---

# The Story Workbench

The workbench is the project view — open any project and you land in it. It's built for
**maximum control**: work through every piece of your book one item at a time, in story
order, with small AI actions you review before anything is saved.

Three panes (resizable; they stack on small screens):

- **Left — the story tree.** Concept → Outline → Chapters (expand for Scenes) → Characters →
  Locations → Codex → World → Arcs (expand for Milestones) → Threads. Status dots are derived
  live from your actual files and data: green = written/complete, blue = developed/in
  progress, gray = pending, amber = an AI proposal awaiting your review.
- **Center — the item editor.** Every field of the selected item, editable in place, plus the
  AI actions that make sense for that item type. **Prev/Next** walks the story spine in order.
  Every selection is a URL (`?sel=scene:3.2`), so bookmarks and the back button work.
- **Right — the brainstorm co-writer, docked.** Its focus follows your tree selection: select
  a scene and the chat develops *that scene*. See [Brainstorm Co-writer](./brainstorm).

## Working one item at a time

Each item type gets its own editor:

- **Concept** — title, genre, logline, tone, audience, description; generation suggestions
  appear here with per-field Apply/Dismiss (the AI never overwrites your values).
- **Outline** — the markdown plan, plus **Develop remaining** (additive: fills placeholder
  chapters and adds scenes only where missing) and the lock-protected **Rewrite unlocked…**
  (destructive, names exactly which chapters it will rewrite; developed chapters start locked).
- **Chapter** — title and summary, the scene list, the full prose with **Revise with AI**
  (diff, keep or discard), **Develop scenes** to (re)generate the chapter's scene briefs,
  **Write/Rewrite chapter**, and **Check milestones** (below).
- **Scene** — the brief (summary, setting, characters, goal, emotional beat, pacing type,
  target words) and *this scene's prose only*. **Write/Rewrite scene** drafts just this scene
  with the full story context — canon rules, a recap of every scene written so far, the
  preceding prose, and a repetition ban list — then shows a diff; keeping it splices the new
  text into just that scene's block of the chapter file.
- **Character / Location / Codex entry / Thread** — every field, relationship pickers,
  connections, and for characters a **Generate voice profile** action (speech patterns,
  verbal tics, sample lines — reviewed in the editor before you save).
- **World** — each worldbuilding field individually, with a per-field **Generate** that
  drafts one field grounded in your lore.
- **Milestone** — see below.

**Editing never cascades.** Changing an early item never regenerates anything later. Lore
editors show an *impact hint* — "Referenced in prose: Ch. 3 (2×) · outline scenes: 5.1 —
editing here never regenerates any of them" — so you can revise with confidence.

## Honest milestones

Story arcs carry milestones — planned beats targeted at specific chapters. The workbench makes
their completion **verified, not assumed**:

1. On a written chapter, click **Check milestones (AI)**. The AI grades whether the chapter's
   prose *actually delivers* each targeted beat — not merely mentions or foreshadows it — and
   must cite an **exact quote** as evidence. A cited quote that isn't really in the prose
   downgrades the verdict to *uncertain* automatically.
2. Verdicts are **proposals** (amber "review" badge in the tree). Open the milestone to see
   the evidence and reasoning, then **Accept** or **Dismiss**.
3. Accepting a *delivered* verdict marks the milestone completed; accepting a *not delivered*
   verdict re-opens it. Either way, **you own the flag** — every milestone's status can be
   flipped manually at any time, like every flag in LibriScribe.

## Generation: small bites by default, batch on demand

The pipeline is **concept → outline → chapters → formatting**. Character and world work
happens in the lorebook — per-item, human-approved — not as pipeline stages.

The **Automation** page (top-right link; the former dashboard) keeps the run-level controls:
run next step, write a specific chapter, run-all, reset-to-stage, exports, version snapshots,
and AI/model configuration. Its **Batch tools…** menu offers one-shot cast or worldbuilding
generation for seeding a brand-new project — results that collide with existing lore are
staged in the sandbox for your review, never merged automatically.

**Lore tools** (also top-right) hosts the utilities that operate on the whole lorebook:
JSON import (with auto-repair and format detection), the review sandbox, gap scans,
reference material, and the cross-reference graph. See [The Lorebook](./lorebook).
