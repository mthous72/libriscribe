---
sidebar_position: 8
---

# Versioning, Export & Import

Your work is portable and recoverable. Everything lives as plain files under
`%LOCALAPPDATA%\LibriScribe`, and the app adds convenient backup, versioning, and transfer tools.

## Export & import a project

From the project dashboard:

- **Export Project** — saves the entire project (knowledge base + all prose) as a single
  self-contained `.libriscribe.json` **bundle**.
- **Import Project** — loads a bundle on another machine (auto-renaming on name collisions).
- **Export Story (.txt)** — the manuscript as plain text (markdown stripped), for sharing or
  submission.

Use these to move a book between machines or to keep external backups. Reference material is
**not** included in exports (it's your source material, not the manuscript).

## Version snapshots & rollback

Snapshot a project at any point and roll back later:

- **Save a version** — capture the current state with an optional label.
- **Restore** — roll the whole project back to a snapshot. A snapshot is taken automatically
  *before* a restore, so rollbacks are themselves reversible.

Snapshots use the same self-contained bundle format and are stored under the project's
`versions/` folder.

## Where everything is stored

```
%LOCALAPPDATA%\LibriScribe\
  .env                         # your settings / API keys
  projects\<project>\
    project_data.json          # the knowledge base
    chapter_1.md ...           # prose
    versions\                  # snapshots
    references\                # imported source docs (excluded from exports)
    chat_sessions\             # brainstorm sessions
```

Because it's all plain files, you can back it up or sync it with any tool you like.
