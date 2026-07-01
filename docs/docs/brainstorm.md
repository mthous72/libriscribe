---
sidebar_position: 6
---

# Brainstorm Co-writer

A lore-aware chat panel available on every project page (the **Brainstorm** button, bottom-right).
It sees your project's lore, helps you plan and explore before anything is finalized, and can
turn ideas into structured lore.

## Lore-aware chat

The co-writer retrieves relevant lore for each message and stays consistent with what's
established. Replies are deliberately **concise** — a few focused ideas, not essays. When it
proposes something new (not already in your lore), it says so.

## Focus mode

Pick a **Focus** — a specific character, location, lore entry, or arc — to develop *just that
entity*. The co-writer draws on the surrounding world (connected characters, involved arcs, world
lore) as **read-only context** to keep ideas grounded and consistent, but keeps every suggestion
about the focused entity and won't wander off to rewrite the others.

## Multiple parallel sessions

Keep separate, named chat threads per book — e.g. a **plot** session, a **villain** session, a
**magic-system** session — each with its own history and its own persisted Focus. Use the session
switcher at the top of the drawer to create, rename, delete, and switch between them. Your
previous single conversation is migrated into a **General** session automatically.

## Ground in reference material

Toggle **Use reference material** to include your imported [references](./lorebook) as background
source in the co-writer's context. Great for staying faithful to research or a series bible.

## Apply ideas to the lorebook (Smart Apply)

Click **Apply to lore** on any reply to turn it into lore. The co-writer parses the reply into
**multiple records across categories** (characters/locations/lore/arcs) with the right fields,
then shows a **review panel** — New/Update badges, editable fields, per-record checkboxes. On
apply, records are **smart-merged** into the lorebook (fill empty, update revised, preserve
untouched). See [The Lorebook](./lorebook) for the merge details.

## Preview the prompt

Click **Preview prompt** to see the exact assembled system prompt — the lore context and any
reference material — that the AI would receive for your current message and Focus. No LLM call is
made. This is a handy way to understand (and debug) what context the model is actually working
with. A companion **Preview AI context** button on the chapter editor does the same for chapter
generation — see [Manuscript Stats & Prompt Preview](./stats-and-preview).
