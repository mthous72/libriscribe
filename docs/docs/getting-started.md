---
sidebar_position: 2
---

# Getting Started

There are two ways to run LibriScribe: the **prebuilt Windows installer** (easiest — no
prerequisites) or **from source** (for development or other platforms).

## Option A — Windows installer (recommended)

No Python, Node.js, or other prerequisites required.

1. Download the latest `LibriScribeGUI-<version>-Setup.exe` from the
   [**Releases**](https://github.com/mthous72/libriscribe/releases) page.
2. Run the installer (a standard wizard; installs for your user account).
3. Launch **LibriScribe GUI** from the Start Menu. It starts a local web server and opens your
   browser at `http://127.0.0.1:8000`. A **system-tray icon** lets you open the app or quit it.
4. Open **Settings** and add an API key for any provider — or point it at a **local LLM**. See
   [Providers & Models](./providers-and-models).

**Where your data lives:** projects, settings (`.env`), version snapshots, references, and logs
are stored under `%LOCALAPPDATA%\LibriScribe` (not in Program Files), so they survive upgrades.

**Updating:** download the newer `Setup.exe` and run it over your existing install — your
projects and settings are untouched.

## Option B — Run from source

Requires **Python 3.10+** and (for the frontend) **Node.js 18+**.

```bash
git clone https://github.com/mthous72/libriscribe.git
cd libriscribe
pip install -e .
```

Build the frontend once (served by the app):

```bash
cd frontend && npm install && npm run build && cd ..
```

Launch the app:

```bash
libriscribe
```

This starts the server at `http://127.0.0.1:8000` and opens your browser.

### Frontend dev server (optional)

For UI development with hot reload:

```bash
cd frontend && npm run dev
```

Vite runs at `http://localhost:5173` and proxies API/WebSocket calls to the backend on `:8000`.

## First run

1. Open **Settings** and configure at least one provider (cloud key or a local LLM). Providers
   stay disabled until a real key is added.
2. From the home page, create a **New Project** — pick a title, genre, and the AI provider/model
   for the book. The wizard autosaves your draft as you go.
3. Generate a concept and outline, then write chapters — or jump straight into the
   [Lorebook](./lorebook) and [Brainstorm co-writer](./brainstorm).

Next: **[Using LibriScribe](./usage)**.
