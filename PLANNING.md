# LibriScribe — Feature Planning & Backlog

Living planning doc. Features are specced here **before** implementation. Nothing
in "Backlog" is built until it has been promoted to a full spec and approved.

Last updated: 2026-06-29

---

## Build priority (pain-first — chosen 2026-06-29)

1. **B1 + B2** — server overhaul: single-instance launch + tray/quit + dirty-flag
   foundation. **← specced below (Spec #1), awaiting approval to build.**
2. **B3** — manual-save reminder (reuses B2's dirty flag).
3. **Import/Export** — project bundle + story `.txt` (foundation for B4).
4. **B4** — version tracking (reuses the bundle; wholesale → granular).

Each item is built only after its spec is approved.

---

## Spec #1 — B1 + B2: server overhaul (single-instance + tray/quit + dirty flag)

**Status: VERIFIED on test builds (splash, Settings, tray/quit) — releasing as v0.6.0.**
Combines B1 and B2
because both rewrite `server.py`'s startup/run model — done in one pass. Also
establishes the dirty-flag foundation that B3 reuses. (Decision records: see B1 and
B2 in the Backlog below.)

**Implementation notes (as built):**
- New `libriscribe.runtime` (shutdown event + in-memory `{dirty, active_generation}`).
- New `api/routers/system.py`: `GET /api/health`, `GET|POST /api/ui-state`,
  `POST /api/shutdown`. App version sourced from `libriscribe.__version__` (0.6.0).
- `server.py` rewritten: port-walk `_choose_port()` over 8000..8010; programmatic
  `uvicorn.Server` (background thread) + `pystray` tray (main thread) when frozen, or
  `LIBRISCRIBE_TRAY=1`; plain main-thread run otherwise; `log_config=None` (belt-and-
  suspenders for the windowed no-tty logging crash); native Windows confirm on tray
  Quit when `dirty`.
- Frontend: `store/uiSlice.ts` dirty flag (debounced report to `/api/ui-state`);
  `App.tsx` Quit button + `beforeunload` guard + shutdown screen; dirty wired into
  ChapterEditor, Outline, and Lorebook (FieldEditor/World/saves).
- Deps `pystray` + `Pillow` added to `setup.py`, spec `hiddenimports`, and the `.ico`
  bundled via spec `datas`.
- Tests: `tests/test_server_port_walk.py` (8, pass locally), `tests/test_system_endpoints.py`
  (needs app deps; runs in CI/standard env).
- **Coverage caveat:** dirty-flag wiring covers the main editors; some sub-fields
  (e.g. character voice-profile inputs) don't yet set dirty — best-effort, acceptable
  per the agreed design. Extend incrementally if needed.

**Post-test fixes (round 2, from installed verification):**
- **Startup feedback (#1/#2):** added a PyInstaller **splash screen** (generated in
  the spec via Pillow; shown instantly on launch, closed by `server.py` via
  `pyi_splash` once `/api/health` answers). Removes the "is it working?" gap and the
  "page cannot be reached" race — the browser already auto-opens only when ready.
- **Settings button broken (#4):** root cause was SPA routing — `<a href>` did a full
  reload to `/settings`, which `StaticFiles` 404'd. Fixed with `SPAStaticFiles`
  (index.html fallback for non-API 404s) + client-side `<Link>` nav.
- **#3 (Quit web + tray):** confirmed working on the test build.

### Dependencies to add
- `pystray` + `Pillow` → `setup.py` install_requires, PyInstaller `hiddenimports`,
  and bundle `installer/libriscribe.ico` via the spec `datas`. Verify the frozen
  build is self-contained (zero end-user prerequisites).

### Backend — `server.py` startup overhaul
1. **Health endpoint (B1):** `GET /api/health` → `{"app":"libriscribe","version":…}`,
   used to recognize an existing instance.
2. **Port-walk + single-instance (B1):** candidate ports `8000..8010`. For each,
   probe `http://127.0.0.1:<port>/api/health` (short timeout):
   - LibriScribe signature → existing instance: open the browser there and **exit**
     (no duplicate).
   - Responds but not LibriScribe → try next port.
   - Refused/free → bind here.
   Pass the chosen port to both `uvicorn` and `webbrowser.open`.
3. **Programmatic server + tray (B2):** replace blocking `uvicorn.run(...)` with
   `uvicorn.Server(uvicorn.Config(...))` on a **background daemon thread**; run the
   `pystray` icon on the **main thread**. Poll `/api/health` until up, then open the
   browser (removes today's fixed-delay race).
4. **Tray menu:** *Open LibriScribe* (open browser at the active port; also the
   double-click default) and *Quit LibriScribe*. Optional one-time "running in the
   system tray" notification.
5. **Clean shutdown:** Quit (tray or web) → dirty check → `server.should_exit=True`,
   `icon.stop()`, exit. This is the clean shutdown hook the app lacks today.

### Backend — quit & state endpoints
- `POST /api/shutdown` → triggers the same clean shutdown (web-UI Quit path).
- `POST /api/ui-state` → frontend reports `{dirty, active_generation}`; server keeps
  it in memory for the tray's dirty check.

### Dirty-flag foundation (shared with B3)
- Server holds in-memory `ui_state = {dirty, active_generation, updated_at}`.
- **Web Quit:** frontend knows its own dirty state → confirm modal → `POST /api/shutdown`.
- **Tray Quit:** reads server-side `dirty`; if dirty, native **Windows MessageBox**
  (ctypes `user32.MessageBoxW`, Yes/No) before shutting down; else quit immediately.

### Frontend
- **Dirty flag** in the Zustand store: set on book/lore edits, cleared on manual save;
  report to backend via debounced `POST /api/ui-state`.
- **`beforeunload`** warning when dirty (best-effort hard-close guard).
- **Quit button** in the app header: if dirty → confirm modal → `POST /api/shutdown`
  → show "LibriScribe has shut down — you can close this tab."

### Verification
- Unit: port-walk selection (mock probes), health endpoint, shutdown sets exit flag,
  ui-state read/write.
- Installed/manual: launch twice → 2nd opens browser, no 2nd process; tray Quit clean
  vs dirty; web Quit; port fallback when 8000 is held by another app.
- Build: confirm `pystray`/`Pillow` are bundled — the frozen exe shows the tray on a
  clean Windows VM with nothing else installed.

### Minor sub-decisions (defaulted — flag if you disagree)
- Candidate port range upper bound = **8010**.
- Tray double-click → **Open**.
- One-time "running in system tray" notification = **yes**.

---

## Spec #3 — Project & Story Import / Export

> **Partial delivery (v0.7.0):** a **lore JSON import** shipped — Lorebook → "Import JSON"
> parses `characters`/`locations`/`lore`/`arcs`/`worldbuilding` (lists or name-keyed
> objects, field aliases) into KB records, with an optional **AI-map** mode
> (`POST /api/projects/{name}/lore/import`, `smart` flag) for non-standard JSON. The full
> project bundle (`.libriscribe.json`) + story `.txt` export below are still pending.

**Goal:** Let users back up, move between machines, and share their work — both
the *entire* project (lossless) and the *readable story* (plain text).

#### 1a. Project Export — full, lossless, single JSON bundle

- **Output file:** `<ProjectName>.libriscribe.json` (single, portable, human-readable)
- **Contents:**
  - `schema_version` (start at `1`) and `exported_at` timestamp
  - The complete `ProjectKnowledgeBase` (everything in `project_data.json`):
    characters, locations, lore entries, story arcs, worldbuilding, outline,
    chapter structure/summaries, continuity notes, narrative threads, character
    states, lore suggestions, and project settings (genre, tone, audience, etc.)
  - **Inlined prose** — the full text of every prose `.md` file in the project
    (`chapter_N.md`, `chapter_N_revised.md`, `outline.md`, `manuscript.md`),
    embedded as strings keyed by filename. This is essential: the `Chapter`
    model holds only summaries, **not** the written words.
  - Per-project `writing_system_prompt` and LLM/model settings.
- **Excluded:**
  - **API keys** — never in a bundle (they live in `.env`, outside any project).
    Sharing a bundle must never leak keys.
  - **Retrieval indexes** — derived data; rebuilt from content on import.
- **Open question (default = include):** should LLM/model picks be stripped so a
  *shared* bundle doesn't carry the sender's model choices? Default for now:
  include everything except API keys. Revisit if sharing becomes common.

#### 1b. Project Import

- **Input:** a `.libriscribe.json` bundle (file upload).
- **Behavior:** validate `schema_version` and the KB against the model; recreate
  the project folder under `projects_dir`; write `project_data.json`; re-emit each
  inlined `.md` file; rebuild the retrieval index from content.
- **Name collisions:** if a project of that name already exists → **prompt the
  user, default to auto-rename** (`MyBook-2`, `-3`, …). Never silently overwrite.
- **Failure handling:** clear, user-facing error on malformed/incompatible bundle;
  no partial project left behind on failure.

#### 1c. Story Export — readable prose, `.txt`

- **Output file:** `<ProjectName>.txt`
- **Behavior:** assembled on the fly from the chapters **as they currently stand**
  (works mid-draft; does not require a finished `manuscript.md`):
  - Book title at top.
  - Each chapter in order as `Chapter N: Title` followed by its prose.
  - Prefer `chapter_N_revised.md` when present, else `chapter_N.md`.
  - Light Markdown stripping so it reads as clean prose.
  - Pure prose — no synopsis/outline/front matter.

#### 1d. UI & API surface

- **Project Dashboard:** "Export Project" (`.json`) + "Export Story (`.txt`)" buttons.
- **Home page:** "Import Project" (file picker → upload, with collision prompt).
- **Endpoints (in `api/routers/projects.py`):**
  - `GET /api/projects/{name}/export` → JSON bundle (download)
  - `GET /api/projects/{name}/export/story` → `.txt` (download)
  - `POST /api/projects/import` → accepts uploaded bundle (+ optional target name /
    collision strategy)
- **Backend:** new helpers in `services/project_service.py`
  (`build_export_bundle`, `import_bundle`, `assemble_story_text`) + a small
  Markdown-stripping utility.
- **Frontend:** `api/client.ts` methods, buttons, and an import modal.
- **Tests:** export→import round-trip fidelity; story assembly ordering and
  revised-vs-original selection.

**Status:** BUILT (v0.8.0). `project_service`: `export_project_bundle` (KB + inlined
`.md` prose + chat history; excludes keys/indexes), `import_project_bundle` (validates
schema, recreates the project, **auto-renames on collision**), `export_story_text`
(assembles current chapters, prefers revised, light Markdown strip). Endpoints:
`GET /{name}/export`, `GET /{name}/export/story`, `POST /import`. UI: Dashboard
"Export Project (.json)" + "Export Story (.txt)"; Home "Import Project" (file picker →
upload → navigate, notes rename). Retrieval index rebuilds lazily on next use.

---

## Backlog (to be specced before building)

> Add items here as we think of them. Each gets promoted to "Active spec" and
> approved before any code is written.

### B1. Single-instance launch (open existing instead of duplicating)

**Problem:** Launching LibriScribe while it's already running starts a second
resident process instead of surfacing the instance that's already up.

**Insight:** LibriScribe is a local web server (uvicorn on `127.0.0.1:8000`) that
auto-opens the browser. "Open the existing instance" therefore just means pointing
the browser at the already-running server — not starting a second one.

**Proposed approach:**
- Add a tiny identity endpoint (e.g. `GET /api/health` → `{"app":"libriscribe","version":…}`).
  No such endpoint exists today.
- In `server.py main()`, **before** binding, walk an ordered list of candidate
  ports — `8000`, then `8001`, then a few more (e.g. up to `8010`) for safety —
  and for each one:
  - **Probe** `http://127.0.0.1:<port>/api/health` with a short timeout.
    - If it answers with the LibriScribe signature → an instance is already up on
      that port; **open the browser there and exit** (no duplicate). This also
      finds an existing instance that itself fell back to 8001+.
    - If the port answers but is **not** LibriScribe → skip to the next candidate.
    - If the port is **free** → start the server there and open the browser to it.
- The chosen port must flow through to both `uvicorn.run(port=…)` and
  `webbrowser.open(...)` (today both are hardcoded to 8000). The frontend uses
  relative `/api` and `/ws`, so it needs no change regardless of port.
- Optional secondary guard: a Windows named mutex / PID lock file, but the port
  walk alone both prevents the duplicate **and** delivers "open the existing one,"
  so it is likely sufficient.

**Decisions (resolved):**
- **Port conflict:** if 8000 is held by a non-LibriScribe app, **fall back to 8001**
  (and onward through the candidate list), rather than erroring.
- **Browser focus:** **best-effort is acceptable** — re-opening the URL focuses the
  existing tab in most browsers; no attempt to force-focus an OS window.

**Status:** ✅ promoted → see **Spec #1** (server overhaul). Build order #1.

### B2. System tray icon (stop / open the running service)

**Problem:** The app runs as a windowed (no-console) process, so there is no
visible handle on it — the only way to stop the service today is Task Manager.

**Proposed approach (recommended): a system tray icon.**
- Use `pystray` (+ `Pillow` for the icon image); reuse `installer/libriscribe.ico`
  (bundle it via the PyInstaller spec `datas`, load from `sys._MEIPASS`).
- Tray menu:
  - **Open LibriScribe** → `webbrowser.open(...)` at the active host/port.
  - **Quit LibriScribe** → clean shutdown of the uvicorn server, then exit.
- **Architecture change:** switch from the blocking `uvicorn.run(...)` to a
  programmatic `uvicorn.Server(Config(...))` run on a background thread, with the
  tray loop on the main thread. "Quit" sets `server.should_exit = True`, stops the
  tray, and exits the process. (This also gives us the clean shutdown hook the app
  currently lacks.)
- Optional first-run notification: "LibriScribe is running in the system tray."

**Two quit paths (both included):**
- **Tray → Quit LibriScribe** (native, always available).
- **Web-UI Quit button** → `POST /api/shutdown`, for users who live in the browser.
Both run the same dirty-state check below before shutting down.

**Confirm-before-quit on unsaved changes (best-effort):**
- Frontend tracks a **dirty flag** = unsaved edits to book/lore.
- **Web-UI Quit:** frontend already knows dirty state → show a confirm modal
  ("You have unsaved changes — quit anyway?") before calling `POST /api/shutdown`.
- **Tray Quit:** the Python process can't see the browser's edit state directly, so
  the frontend **reports dirty/clean to the backend** (WebSocket heartbeat or a
  small `POST /api/ui-state`). Tray Quit reads that server-side flag and, if dirty,
  pops a **native OS confirm dialog** (Windows `MessageBox` via `ctypes`) before
  shutting down; if clean, quits immediately.
- **Hard browser close:** caught best-effort via the browser `beforeunload` warning
  when dirty. Cannot be guaranteed (user accepts this) — and the service keeps
  running in the tray regardless, so closing the tab no longer loses the instance.
- **Implementation note:** check how the app currently saves (autosave vs explicit
  save) when speccing — it determines how wide the "unsaved" window actually is and
  where the dirty flag must be set/cleared.

**Decisions (resolved):**
- **Scope:** ship **both** the tray icon and the web-UI Quit button.
- **Dependencies:** OK to add `pystray` + `Pillow`, **provided they are baked into
  the release** — must be in PyInstaller `hiddenimports`/`datas` and the build
  verified self-contained (zero end-user prerequisites, per the project's installer
  goal).
- **Confirm-before-quit:** yes, when there are **unsaved changes** to book/lore;
  best-effort across the hard-browser-close case.

**Pairs with:** B1 — the tray handle belongs to the single running instance; a
second launch still just opens the browser and exits.

**Save model (decided, see B3):** manual save only — **no autosave**. The dirty
flag here means "edits since the last manual save."

**Status:** ✅ promoted → see **Spec #1** (server overhaul). Build order #1.

### B3. Manual-save reminder (no autosave)

**Decision:** the product deliberately has **no autosave**. Instead, remind the
user to save manually when they have unsaved work.

**Proposed approach:**
- Reuse the **dirty flag** from B2 (unsaved edits to book/lore). Reminders only
  fire while dirty; saving clears the flag and resets the timer.
- **Time-based nudge:** while there are unsaved changes, show a periodic,
  **non-blocking** reminder — a dismissible toast/banner with a **"Save now"**
  action button — rather than a modal that interrupts writing.
- Reset the interval on every manual save; stop reminding once clean.
- Shares infrastructure with B2 (dirty tracking) and reinforces B2's quit/close
  confirmations.

**Open questions:**
- **Interval:** default reminder cadence (e.g. every 5 or 10 minutes), and should
  it be user-configurable in Settings?
- **Style:** non-blocking toast/banner (recommended) vs. a more assertive prompt?
- **Escalation:** should the reminder get more prominent the longer work stays
  unsaved, or as more changes pile up? (Lean: gentle, non-escalating — possibly a
  small persistent "unsaved changes" indicator plus the periodic toast.)

**Status:** backlog — needs interval/style decisions, then promote to a full spec.

### B4. Save version tracking (snapshots / rollback)

**Goal:** keep a history of saved versions so the user can track progress and roll
back to an earlier state of the story/lore.

**Key synergy:** a "version" is a point-in-time snapshot of the project — which is
exactly what the **Import/Export bundle** (Active spec) produces. Reuse it: each
saved version is a `.libriscribe.json` written to a `versions/` folder inside the
project; **restore = import that bundle** over the project. One snapshot mechanism,
not two.

**⚠️ Namespace warning — story version ≠ app version ≠ schema version.** These are
three distinct things and must never be conflated:
- **App/software version** (e.g. `0.6.0`) — global, in `libriscribe.__version__`,
  `setup.py`, the installer `.iss`, and `GET /api/health`.
- **Schema versions** — already exist as `version: 1` integers in `configuration.py`
  and `project_status.py` (file-format versions).
- **Story version (this feature)** — per-project snapshot counter (`vNNN`). Give its
  metadata field an unambiguous name (e.g. `snapshot_number` / `story_version`), not
  bare `version`, to avoid colliding with the schema-version fields above.

**File naming (decided): `storyshort_vNNN_yymmdd`**
- e.g. `mybook_v003_250629`. `storyshort` = sanitized project name.
- The **incrementing version number `vNNN` is the unique key** — it disambiguates
  multiple saves on the same day, so the day-granular date is fine (it's there for
  human readability, not uniqueness).
- Zero-padded N sorts sensibly; revisit padding width if a project could plausibly
  exceed 999 versions.

**Storage:** `<project>/versions/` subfolder, so history lives with the project.

**Versioning scheme (decided):**
- **Backbone = dumb auto-incrementing integer** (`v001, v002, …`). No user
  classification, no semver — every save just bumps the number. (`major.minor.patch`
  was rejected: it adds per-save friction and the boundaries are subjective for prose.)
- **Optional milestone labels** the user applies when *they* decide something matters
  ("Draft 1 complete", "Act 2 rewrite", "Beta to editor") — the writer-native analog
  of a "major version."
- **Auto-computed change summaries** shown per version (e.g. `+1,240 words ·
  2 chapters changed · 3 lore entries edited`), derived by diffing snapshots. This
  conveys *magnitude* at a glance **without** encoding it in the version number —
  the identifier stays a dumb integer; "how big was the change" is computed and
  displayed separately.

**Rollback (decided): phased.**
- **Phase 1 — wholesale rollback:** restore the entire project to a prior snapshot
  (re-import its bundle). Simple, safe, predictable, essentially free given the
  bundle model. Build this first.
- **Phase 2 — granular restore:** restore individual units (a chapter, character,
  location, lore entry, arc, the outline) from an older version while keeping
  everything else current — mechanically feasible since each snapshot is addressable
  by key. Must warn: "this grafts older content into your current project — review
  for continuity," since partial restore can create contradictions / stale index.
- **Universal safety rule:** any restore (full or partial) **first auto-snapshots the
  current state**, so a rollback is itself never destructive (undo the undo).

**Restore/rollback UI:** list versions (number, date, optional label, change
summary), preview, and restore — "Restore all" in Phase 1; per-element selection in
Phase 2.

**Open questions:**
- **When is a version created?** Every manual save auto-snapshots, OR versions are
  explicit "checkpoints" the user creates on demand (separate from plain save)?
  (Leaning: explicit checkpoints + optionally snapshot-on-save, to avoid clutter.)
- **Retention:** keep all versions, keep last N, or prune by age? (Text is small, so
  "keep all" is viable, but offer pruning.)
- **Export interaction:** should the project export bundle **include** the
  `versions/` history, or export only the current state (leaner file)? (Lean:
  exclude history by default; optional "include history" toggle.)

**Pairs with:** Active spec (reuses the bundle format) and B3 (save action is the
natural snapshot trigger).

**Status:** BUILT — Phase 1 (wholesale) in v0.8.0, reusing the export/import bundle.
`project_service`: `save_project_version` (export bundle → `versions/<slug>_vNNN_yymmdd.libriscribe.json`
+ `versions/versions.json` index with label, timestamp, count summary), `list_project_versions`,
`restore_project_version` (auto-snapshots current first, then overwrites in place). Endpoints
`GET|POST /{name}/versions`, `POST /{name}/versions/{version}/restore`. Dashboard **Versions**
panel: Save Version (optional label), list with counts, Restore (confirm, reversible).
**Still backlog:** Phase 2 granular per-element restore; retention/pruning; explicit
"snapshot every manual save" trigger.

### B5. Settings / API-key overhaul (no junk defaults, per-provider enable)

**Bug found:** `.env.example` seeds every `*_API_KEY` with the literal
`your_api_key_here`. First-run seeding copies that into `.env`, so the Settings page
shows masked placeholder values (`your...here`) and **every provider falsely reports
"configured"** (`bool("your_api_key_here")` is truthy) — generation would then fail
on fake keys.

**Phase 0 — DONE (shipping in v0.6.0):** blanked the keys in `.env.example`
(`OPENAI_API_KEY=` etc.; kept model defaults + base_url) so fresh installs show
providers **off**. Also added backend defense in `api/routers/settings.py`
(`_is_real_key` / `_PLACEHOLDER_KEYS`) so placeholder-seeded keys read as "not set"
for both masking and `configured` — fixes existing installs too, without deleting `.env`.

**Phase 1 — UI overhaul:**
- Each provider **off by default**, with an enable toggle; key + model fields only
  active when enabled.
- `configured` = enabled **and** a real (non-empty, non-placeholder) key present.
- Don't render masked placeholders for empty/placeholder keys.
- Optional: treat known placeholder strings as "not set" defensively in the backend.

### B6. Model dropdown populated from provider model-list API

**Goal:** when a provider is selected and an API key is provided, reach out to that
provider's API, pull the list of available models, and populate that provider's model
dropdown — flagging/filtering **free** models where the provider exposes pricing.

**Per-provider list-models calls (researched & confirmed):**

| Provider | Method + URL | Auth | Response → model id | Free flag |
|---|---|---|---|---|
| **OpenAI** | `GET https://api.openai.com/v1/models` | `Authorization: Bearer <key>` | `data[].id` | — |
| **OpenRouter** | `GET https://openrouter.ai/api/v1/models` | `Authorization: Bearer <key>` (optional) | `data[].id` (+ `name`) | `pricing.prompt=="0" && pricing.completion=="0"`, or name contains `(free)` |
| **Anthropic (Claude)** | `GET https://api.anthropic.com/v1/models` | `x-api-key: <key>` + `anthropic-version: 2023-06-01` | `data[].id` (+ `display_name`) | — |
| **Google AI Studio (Gemini)** | `GET https://generativelanguage.googleapis.com/v1beta/models?key=<key>` | key in query string | `models[].name` → strip `models/` prefix; keep only entries whose `supportedGenerationMethods` includes `generateContent` | — |
| **DeepSeek** | `GET https://api.deepseek.com/models` | `Authorization: Bearer <key>` | `data[].id` (OpenAI-compatible) | — |
| **Mistral** | `GET https://api.mistral.ai/v1/models` | `Authorization: Bearer <key>` | `data[].id` (OpenAI-compatible) | — |
| **Local / OpenAI-compatible (B7)** | `GET {base_url}/models` | optional `Bearer` | `data[].id` | all local models are free |

Four of seven are OpenAI-shaped (`/v1/models`, Bearer, `{data:[{id}]}`) → one helper.
Anthropic and Google need their own auth header / response parsing. (Sources:
OpenRouter `/api/v1/models`, Google `generativelanguage …/v1beta/models`, Anthropic
`GET /v1/models`.)

**Backend (`api/routers/settings.py`):**
- `POST /api/settings/models` with body `{ provider, api_key?, base_url? }`. Uses the
  provided key if present (so the dropdown works *before* the user saves), else the
  saved key. Calls the provider's endpoint (server-side — avoids browser CORS),
  normalizes to `[{ id, label, free }]`, sorts (free first), returns it.
- Clear, typed errors: `missing_key`, `invalid_key` (401/403), `network_error`,
  `unsupported_provider` — surfaced to the UI as a friendly message.
- Short in-process cache per (provider, key-hash) — model lists change rarely.
- Use the already-bundled `requests`/`httpx`; short timeout (~10s).

**Frontend (Settings page, ties into B5 redesign):**
- Per provider: when enabled + a key is entered, a "Fetch models" affordance (button,
  or auto-fetch on key blur) calls the endpoint and fills a **dropdown**.
- Free models flagged/grouped; manual text entry remains as fallback (custom/unknown
  model ids).
- Only query enabled providers (B5).

**Open questions:**
- Auto-fetch on key entry vs an explicit "Fetch models" button? (Lean: explicit
  button first — avoids firing on every keystroke and surprise API calls.)
- Filter to free-only, or show all with a "free" badge + a free-only toggle?
  (Lean: show all, badge free, optional toggle.)

**Pairs with:** B5 (only query enabled providers; sends the just-entered key) and B7
(local servers list installed models via the same OpenAI-compatible helper).

**Status:** BUILT — folded into v0.6.0. Backend `POST /api/settings/models` with the
six per-provider fetchers (OpenAI-compatible helper for openai/deepseek/mistral;
dedicated openrouter/anthropic/gemini) + typed errors. Settings page rebuilt: per-
provider key + model field with a `<datalist>` dropdown and a "Load" button (sends the
just-typed key, else falls back to the saved key; masked values ignored). UX defaults
applied: explicit Load button; all models shown with a "free" badge (free sorted first).
B7 (local LLM) not yet built. Pending live verification against real provider keys.

### B7. Local / OpenAI-compatible LLM provider (Ollama, LM Studio, llama.cpp)

**Question raised:** support connecting to a local LLM via an OpenAI-compatible endpoint?
**Recommendation: yes — low effort, high value.** The `LLMClient` already drives
OpenAI-compatible servers via a configurable `base_url` (that's how `openrouter`
works; `openai`/`openrouter` share code paths). A new provider (e.g. `local` /
`openai_compatible`) needs only: a config branch using the OpenAI SDK with a
user-set `base_url` (e.g. `http://localhost:11434/v1` Ollama, `http://localhost:1234/v1`
LM Studio) and an optional/dummy key, plus adding its name to the existing
`provider in {"openai", "openrouter"}` branches.

**Value:** free, private, offline generation. **Composes with B6:** local servers expose
`/v1/models`, so the dropdown auto-populates installed models.

**B7 status:** BUILT — folded into v0.6.0. New `local` provider: `settings.local_*`
(default base_url `http://localhost:1234/v1`); `llm_client` branch mirroring openrouter
(OpenAI SDK + base_url, dummy key when blank) and added to the OpenAI-compatible routing
sets; `model_routing` SUPPORTED_PROVIDERS + default model; B6 model dropdown handles
`local` via the OpenAI-compatible fetcher (no key needed). Settings UI: Local card with a
base_url field, LM Studio / Ollama preset buttons, and a privacy note. Requests go only to
the configured localhost — nothing leaves the machine (caveat: cloud entries in the
fallback chain would). Pending live verification against a running LM Studio/Ollama.

**Status (B5 Phase 1):** still backlog — per-provider enable toggles and "configured =
enabled + real key" UI overhaul not yet built (B5 Phase 0 shipped; B6 + B7 shipped).

---

## Epic: lore-aware LLM "co-writer" (B8–B11) — brainstorm, planning, series

Theme: an LLM layer that plans/brainstorms *with* the project's lore as context, before
ideas get tied down. Most plumbing already exists (retrieval, cross-reference,
`context_builder`, per-entity `analyze` endpoints + suggestion accept/reject, streaming,
`LLMClient`). Effort tiers below are relative (S/M/L), not time estimates.

### Spec — B9. Lore-aware brainstorm chat + Apply-to-lore — **AWAITING APPROVAL** (effort: M)

A side-panel chat to brainstorm/plan/research with the LLM using the project's lore as
RAG context, persisted per project, with one-click "Apply" to turn ideas into lore.
Covers the user's "side panel to bounce ideas," "planning/research before tying down,"
and "general chatbot" asks together. Reuses retrieval (`SearchServiceImpl.search`),
`context_builder` + `TokenBudget`, `generate_content_streaming`, and lore CRUD.

**Backend**
- **Conversation store:** `chat_history.json` in the project dir (travels with the
  project; included in a future export). Shape: `[{role, content, ts}]`.
  - `GET /api/projects/{name}/chat` → history. `DELETE` → clear.
- **Chat (streaming):** `POST /api/projects/{name}/chat` `{message}`:
  1. Append the user message to history.
  2. **RAG context:** `SearchServiceImpl.search(message, top_k)` over the project's
     retrieval index (characters/locations/lore/chapters); assemble a `TokenBudget`-bounded
     lore block. Fallback when retrieval is disabled/empty: a compact KB dump (entity
     names + short descriptions).
  3. **System prompt:** "You are a worldbuilding/brainstorming partner for this book. Use
     the established lore below; stay consistent; clearly flag anything *new* you propose.
     Lore: <context>."
  4. Stream via `generate_content_streaming(system_prompt=…)` using the project's
     `kb.llm_provider` / `kb.model` (now switchable — works with the local LLM too).
  5. SSE `StreamingResponse`; append the assistant message to history server-side when the
     stream completes.
- **Apply-to-lore (MVP):** `POST /api/projects/{name}/chat/apply`
  `{text, target_type: character|location|lore|arc, name}` → create a draft entry via the
  existing lore CRUD (description = text). Returns the created entity.
  (Phase 2: structured extraction — the LLM returns a typed object to pre-fill.)

**Frontend**
- A **Brainstorm** toggle within a project opens a right-side **drawer** (available across
  dashboard / lorebook / editor).
- Chat panel: load history on open, message list, **streaming** assistant responses (reuse
  the existing streaming pattern via `fetch` + ReadableStream — POST has a body, so not
  `EventSource`), input box, **Clear chat**.
- Each assistant message has **Apply → Character / Location / Lore / Arc** → prompt for a
  name → call the apply endpoint → toast + link to the new entry in the Lorebook.
- No unsaved-changes concern: chat auto-persists server-side.

**Transport:** SSE via FastAPI `StreamingResponse` (`text/event-stream`) — self-contained,
doesn't entangle with the generation WebSocket.

**Decisions (resolved):**
- **Apply = BOTH:** "Apply (draft)" creates an entry with the selected text as its
  description; "Smart fill" runs LLM structured extraction to populate typed fields.
  One endpoint with a `smart` flag.
- **Drawer scope = all project pages** (dashboard, lorebook, outline, chapter editor).
- **Chat scope = per-project** (series-wide deferred to B8). Rest of spec as drafted.

**Status:** BUILT (v0.7.0) — pending verification. Backend `api/routers/chat.py`:
GET/DELETE/POST `/chat` (SSE stream) + `/chat/apply` (draft or `smart` extraction);
RAG via `SearchServiceImpl` + `TokenBudget` fallback to KB dump; history in
`chat_history.json` per project; uses the project's provider/model. Frontend:
`components/BrainstormDrawer.tsx` mounted in `App` for any `/projects/:name` route —
floating "Brainstorm" button → right drawer, streaming chat (fetch ReadableStream),
persisted history, per-message "Apply to lore" (type + name + editable text + Smart-fill
toggle) with a link to the Lorebook. Ships with the v0.6.1 fixes as **v0.7.0**.

### B10. Per-lore-section LLM assist that references related lore — **effort: S–M**
- Each character/location/lore/arc gets an interactive "ask/refine/expand" affordance
  (extends the existing `analyze` + suggestion flow from one-shot to conversational).
- Inject **related** lore into the prompt via the cross-reference graph + search
  (`context_builder`) so edits stay consistent ("does this fit what's established?").
- Largely composes existing endpoints; the new work is the per-entity chat UI + pulling
  related-entity context into the call.

**Status:** BUILT (v0.8.0). Delivered via the Brainstorm focus engine: each Lorebook
entry (character/location/lore/arc) has a **"Brainstorm this"** button that opens the
drawer pre-focused on it (shared `brainstormSlice` store), which already loads the
entity + surrounding lore as read-only context. (A separate inline per-entity chat
wasn't needed — the focused drawer covers it.)

### B8. Series / multi-book arc planning — **effort: L** (phase it)
- Today: one project = one book (`ProjectKnowledgeBase`). A series needs a **Series**
  container above Project, a shared **series bible** (characters/locations/lore/world/
  arcs) that books inherit/reference, and **cross-book arcs** + continuity.
- **Phase 1:** a Series grouping + shared series-bible lore that books read for context
  (retrieval indexes series-level docs alongside the book). Lowest-risk first slice.
- **Phase 2:** series-level story arcs spanning books; cross-book continuity checks
  (extend `checkContinuity`). 
- Biggest lift (data-model + UI), but the retrieval/cross-reference layer already
  generalizes to series-level documents once the Series entity exists.

### B11. New-project wizard draft persistence — **effort: S**
- The new-project wizard keeps everything in browser state; nothing saves until "Create
  Project," so closing mid-setup loses it. Persist the in-progress draft (localStorage,
  or a server draft) so a partial setup survives.

**Status:** BUILT (v0.8.0). The wizard autosaves the form to `localStorage`
(`libriscribe:new-project-draft`) on every change and restores it on return (with a
"Resumed your in-progress draft — Start fresh" banner); the draft is cleared on
successful create.

### B12 + B13. Smart lore intake (Apply + Import) — **BUILT** (staged, post v0.8.0)

B12 (smart brainstorm Apply) and B13 (smart JSON import for foreign formats) turned out to
be the **same engine** — parse arbitrary input → reviewable proposal → smart-merge — with
two front doors. Built together as one shared module.

**Decisions (resolved):** Smart merge (fill empty / revise changed / preserve untouched,
case-insensitive name match) + Review & confirm (nothing writes until "Apply selected") for
**both** doors. Foreign formats handled **hybrid**: deterministic adapters first, LLM to
re-classify/enrich + a pure-LLM fallback for unknown shapes.

**Shared engine** — `services/lore_intake.py`:
- `detect_and_adapt(data)` — deterministic adapters: SillyTavern/TavernAI character cards
  (V1 flat + V2 nested, incl. embedded `character_book`), KoboldAI / SillyTavern **World
  Info** (`entries` as dict-by-uid or list; keys/comment/content), and our own bundle / a
  lenient `{characters:[],…}` shape. Returns canonical categories + a format label, or None.
- `llm_map()` / `extract_from_text()` — LLM mapping (foreign JSON enrich/fallback; brainstorm
  prose) into the same canonical `{name, fields}` categories.
- `build_proposal(kb, cats)` — annotates each record `new`/`update` (case-insensitive KB
  match), stringifies field values for editing. **No writes.**
- `merge_apply(kb, records)` — upsert with smart merge: start from existing `model_dump()`,
  overlay only non-empty fields (typed-field coercion: str↔list/int/dict), preserve the rest;
  never wipes untouched data. Worldbuilding merged field-by-field.

**Endpoints:** `POST /{name}/chat/parse` (prose→proposal), `POST /{name}/lore/parse`
(JSON→proposal, `smart` toggles LLM enrich), shared `POST /{name}/lore/apply-parsed`
(merge). Old `/chat/apply` + `/lore/import` kept for back-compat.

**Frontend:** shared `LoreProposalReview` component (records grouped by category, New/Update
badges, per-record checkboxes default-checked, editable fields, Apply-selected with counts).
Wired into the Brainstorm drawer ("Apply to lore" → `ParseApply`) and the Lorebook **Import
JSON** flow (file → parse → review modal; "AI-map" toggles LLM enrich; detected-format note).

**Tests:** `tests/test_lore_intake.py` (14) — adapters (ST card + book, V1 card, WI dict/list,
native, unrecognized), proposal status/stringify, merge (preserve untouched, no-wipe-on-empty,
create, str→list coercion, case-insensitive key, worldbuilding). Full suite **113 passed**.
End-to-end TestClient run confirms parse→apply merges without clobbering existing fields.

---

### Spec — B12. Smart Apply: multi-category lore extraction from brainstorm — ~~APPROVED, building~~ **SUPERSEDED** (see "B12 + B13. Smart lore intake — BUILT" above; this is the original single-door spec, kept for history)

**Problem:** today's "Apply to lore" (chat.py `apply_to_lore`) targets ONE entity of ONE
type with a curated field subset and OVERWRITES by name. A rich brainstorm reply has too
much info for that — it often spans several entities/categories and should *update*
existing entries, not clobber them.

**Decisions (resolved):**
- **Smart merge** for existing entries (match by name, case-insensitive): fill empty
  fields, update fields the parse clearly revises, **preserve anything not mentioned**
  (never wipe untouched data). New names are created.
- **Review & confirm**: parse → show a review panel (records grouped by category, New vs
  Update badge, editable, per-record checkboxes) → nothing is written until "Apply
  selected".

**Backend (api/routers/chat.py, reuse lore-import shape + `_SMART_FIELDS`):**
- `POST /{name}/chat/parse` `{text}` → LLM extracts `{characters:[], locations:[], lore:[],
  arcs:[]}` (each item = name + the `_SMART_FIELDS` for its type). For each record, annotate
  `status: "new" | "update"` by matching name against the KB. **Does NOT write.** Returns the
  proposal. (Reuse `generate_content_with_json_repair`; prompt = "parse into these categories
  with these fields…".)
- `POST /{name}/chat/apply-parsed` `{records: {...}}` → upsert with **merge**: for each entity,
  start from existing `model_dump()` (or empty), overlay provided non-empty fields, rebuild the
  model, save. Return per-category counts. (Generalize the lore-import `_coerce` to merge onto an
  existing record instead of replacing.)

**Frontend (BrainstormDrawer):**
- Replace the simple Apply (type+name) form with **Parse to lore**: call `/chat/parse`, render a
  review list grouped by category — each row: New/Update badge, editable fields, checkbox
  (default checked). **Apply selected** → `/chat/apply-parsed` with the chosen/edited records →
  toast with counts + link to Lorebook.
- Keep the old quick draft-apply path as a fallback option if useful.

**Reuses:** lore-import normalized shape & `_iter_entities`/`_coerce`, `_SMART_FIELDS`, the
focus context engine. **Target:** next feature (post v0.8.0 staging).

**Recommended sequence:** B9 (chat/RAG co-writer) → B10 (per-lore assist) → B8 (series,
phased). Each is independently valuable; B9/B10 also de-risk B8 by proving the lore-aware
context pipeline before the bigger data-model change. **Status: brainstorm — none specced
or built yet.**

---

## Writingway comparison — features to incorporate (specced 2026-07-01)

Compared LibriScribe against **Writingway** (fork `github.com/mthous72/Writingway`; upstream
**`a-omukai/Writingway`**, MIT, PyQt5 desktop app on LangChain). On the core (multi-agent
generation, lore-aware brainstorm, compendium, customizable prompts, local models) we're at
parity or ahead — our smart lore intake, per-project provider switching, version snapshots,
export/import bundle, single-instance packaging + CI have no Writingway equivalent.

Three of Writingway's author-facing features are worth taking (below as B14–B16). Explicitly
**skipping**: spaCy NER auto-entities (our LLM `lore_sync` already covers it, heavy dep),
PyQtChart arc charts (different UI stack), LangChain (our `LLMClient` already does
multi-provider + fallback). Deferred/optional: semantic/vector retrieval (rides the `mode`
scaffold in `retrieval/models.py` but cuts against our deliberate no-external-vector-DB
design — hold), and swapping the fragile Google-scrape in `agents/researcher.py` for the
Wikipedia API (reliability win — revisit later).

### B14. Readability & manuscript statistics — **effort: S** — ✅ **BUILT**

**Status: BUILT.** `services/stats_service.py` (dependency-free, offline): per-chapter + whole-
book word/sentence/paragraph counts, avg sentence length, syllable-based Flesch Reading Ease +
Flesch-Kincaid grade, adverb & dialogue ratios, and reading time — reusing the chapter-file +
`_strip_markdown` path from `export_story_text`. Endpoint `GET /{name}/stats`. UI: a **Manuscript
stats** card on the Project Dashboard (overall tiles + a per-chapter length-bar / reading-ease
pacing view). Tests: `tests/test_stats_service.py` (5). Full suite **149 passed**.

### ~~B14.~~ Readability & manuscript statistics — **effort: S** — *near-term*
**What:** per-chapter and whole-book writing stats — Flesch reading-ease + grade level,
word / sentence / paragraph counts, avg sentence length, adverb & dialogue ratio, estimated
reading time, and a simple pacing view across chapters. Writingway uses `textstat`; we can
add `textstat` (pure-Python, no network) or hand-roll the handful of formulas.
- **Backend:** a stats service over chapter prose (reuse the markdown-strip from
  `export_story_text`); endpoint `GET /{name}/stats` (+ optional per-chapter). No LLM, no
  external calls — cheap and offline.
- **Frontend:** a "Stats" panel on the Project dashboard / chapter editor; small bar view of
  length/readability per chapter to spot pacing outliers.
- **Why it wins:** highest-value author-polish feature Writingway has that we lack, and it
  fits our stack cleanly. No new heavy deps.

### B15. Assembled-prompt / injected-context preview — **effort: M** — ✅ **BUILT**

**Status: BUILT.** No-LLM dry-run of prompt assembly. Brainstorm: `POST /{name}/chat/preview`
returns the exact assembled system prompt (focus/general lore context + reference band) for a
message/focus, via a shared `_assemble_system_prompt()` the live chat now also uses. Generation:
`GET /{name}/preview-context/{chapter}` runs `ContextBuilder.build_scene_context` for a chapter's
representative scene and returns the injected context + token estimate. UI: a **Preview prompt**
button in the Brainstorm drawer (overlay showing the system prompt) and a **Preview AI context**
button on the Chapter editor (modal with the injected context + ~token count). Neither calls the
LLM. Full suite **149 passed**; frontend builds clean.

### ~~B15.~~ Assembled-prompt / injected-context preview — **effort: M** — *near-term*
**What:** before (or alongside) a generation call, show the *fully assembled* prompt with the
exact lore/context our `context_builder` + `TokenBudget` injected. Writingway has a
`prompt_preview_dialog`; for us it's both a transparency feature and a real debugging aid for
our RAG (which is more sophisticated than theirs).
- **Backend:** a dry-run/preview path that runs context assembly for a given chapter/scene
  (and for brainstorm focus) and returns the assembled system+user prompt and the list of
  retrieved/injected lore chunks with their token costs — WITHOUT calling the LLM.
- **Frontend:** a "Preview prompt" affordance in the chapter generate flow and the Brainstorm
  drawer; a read-only view of prompt + injected-context chunks + token budget usage.
- **Reuses:** `services/context_builder.py` (`TokenBudget`), the retrieval `search_service`,
  and the chat `_build_lore_context` / `_focus_context` paths.

### B16. Read-aloud (text-to-speech) — **effort: S** — 🧊 **BACK BURNER (not required now, per user)**
**What:** a "▶ Read aloud" control in the chapter editor / brainstorm to hear prose and catch
clunky phrasing. Writingway needs `pyttsx3` because it's native; **we get this free and
dependency-free** via the browser `SpeechSynthesis` Web API — no backend, no new deps.
- **Frontend only:** play/pause/stop over the current chapter text (or a selection), with a
  voice/rate picker from `speechSynthesis.getVoices()`. Sentence-level highlight-follow is a
  nice-to-have, not required for v1.
- **Status:** specced but **parked** — revisit only when the higher-value items below are done.

### B17. Semantic / embeddings retrieval — **effort: M/L** — ✅ **BUILT**

**Status: BUILT.** Engine: `retrieval/embedder.py` (OpenAI-compatible, cloud or local via
base_url; `build_embedder()` from Settings; signature identifies the embedding space),
`retrieval/semantic_index.py` (cosine, numpy-or-pure-python, filter parity, JSON persistence +
signature check), wired into `IndexManager` (builds/persists on rebuild when mode is
semantic/hybrid + embedder present; drops stale vectors / cleans up on embed failure) and
`SearchServiceImpl.search` (effective-mode resolution + min-max hybrid merge, silent keyword
fallback). Enablement: embedding source (Off/OpenAI/Local + model) on the **Settings** page;
per-book **search mode** (Keyword/Semantic/Hybrid) + "Apply & rebuild index" on the **Project
Dashboard** (`GET`/`PUT /projects/{name}/retrieval`). Tests: `tests/test_semantic_retrieval.py`
(14). Full suite **127 passed**. Keyword remains the default; semantic/hybrid degrade to keyword
when no embedder/index is ready. **Next in cluster:** B19 (reference RAG) leans on this.

_Original spec below._

### ~~B17.~~ Semantic / embeddings retrieval — **effort: M/L** — *wanted (per user)*
**What:** add an optional **semantic** retrieval mode alongside today's keyword BM25 +
cross-ref, so paraphrased/thematic queries recall the right lore and prose. This is the
foundation that also makes B19 (external-reference RAG) actually good.
- **Design (keep our "no external vector DB" promise):** embed chunks and persist vectors to
  disk; do similarity in-process with a **pure-numpy cosine** index (project-scale corpora are
  small — a book + a few refs — so FAISS is optional, not required). Ride the existing `mode`
  field in `retrieval/models.py` and the `SearchServiceImpl` seam; keyword stays the default,
  semantic is opt-in, hybrid (keyword ∪ semantic, re-ranked) is the stretch goal.
- **Embedding source — decide at build (recommended: local-first):**
  1. **Local OpenAI-compatible** embeddings (LM Studio / Ollama `/v1/embeddings`) — offline,
     no heavy Python dep, fits our existing Local provider story. *(recommended default)*
  2. **Provider embeddings** (OpenAI `text-embedding-3-small`, etc.) — best quality, costs
     tokens, needs a key.
  3. Bundled local model (`sentence-transformers`) — offline but a heavy dep + model download;
     avoid unless (1)/(2) prove insufficient.
- **Incremental:** reuse `index_manager`'s hash-based refresh so only changed chunks re-embed;
  log embedding cost via `CostTracker` when a paid provider is used.
- **Fallback:** if no embedder is configured/reachable, silently fall back to keyword — never
  break search.

### B18. Multiple parallel brainstorm sessions — **effort: M** — ✅ **BUILT**

**Status: BUILT.** Chat storage moved from one `chat_history.json` to per-session files under
`<project>/chat_sessions/` (id, title, persistent `focus`, created/updated, messages); the
legacy single history is auto-migrated into a default **"General"** session on first list.
Endpoints (`chat.py`): `GET/POST /chat/sessions`, `GET/PATCH/DELETE /chat/sessions/{sid}`,
`DELETE /chat/sessions/{sid}/messages`; `POST /chat` gained `session_id`; old `/chat`
GET/DELETE kept as back-compat over the default session. UI: a **session switcher** in the
Brainstorm drawer (new / rename / delete / switch), with **per-session Focus** (persisted via
PATCH) and messages; Smart Apply / references / streaming unchanged. Tests:
`tests/test_chat_sessions.py` (5, incl. migration). Full suite **144 passed**; frontend builds
clean; e2e TestClient run confirms migrate → create(+focus) → rename → delete. **Completes the
Writingway-derived set** (B17/B19/B20/B18); B14/B15 remain near-term, B16 parked.

_Original spec below._

### ~~B18.~~ Multiple parallel brainstorm sessions — **effort: M** — *wanted (per user)*
**What:** today the Brainstorm co-writer is a **single** thread per project
(`chat_history.json`). Add **named, parallel sessions** so an author can keep, e.g., a "plot"
chat, a "villain" chat, and a "magic system" chat separate — each with its own history and
optional persistent Focus.
- **Backend:** move chat storage from one file to a `chat_sessions/` dir (one file per
  session: id, title, created/updated, optional `focus`, messages). Endpoints: list / create /
  rename / delete sessions; the existing `/chat`, `/chat/parse` gain a `session_id`. Migrate
  the current single history into a default "General" session on first load.
- **Frontend:** a session switcher in the Brainstorm drawer (list + new + rename + delete);
  Focus and Smart Apply operate within the active session. Everything else (streaming, parse →
  review → merge) is unchanged.
- **Note:** purely additive to B9/B12; no change to the lore-merge engine.

### B19. Bring-your-own-reference RAG — **effort: L** — ✅ **BUILT**

**Status: BUILT.** `services/reference_service.py` stores imported PDFs/TXT/MD under
`<project>/references/` (extract-once via `pypdf`, manifest, add/list/delete) and builds
`reference`-typed RetrievalDocuments. `IndexManager._all_documents()` folds them into the
keyword + semantic index; new `exclude_source_type` filter keeps references out of canon
retrieval. Grounding: brainstorm chat gets a labelled reference band + a **"Use reference
material"** toggle (`chat.py`), and chapter generation gets a bounded reference band in
`context_builder` (canon retrieval now excludes references). API: `GET/POST/DELETE
/projects/{name}/references` (multipart upload, auto-reindex). UI: a **References** tab in the
Lorebook (upload/list/delete). References are **never treated as canon** and are **excluded
from exports** (verified). Tests: `tests/test_references.py` (8). Full suite **135 passed**;
end-to-end TestClient run confirms upload → reference-only retrieval, canon exclusion, and
no export leakage. Best paired with B17 semantic (done). **Cluster complete** (B17 + B19); B18
(multi-session) still open.

_Original spec below._

### ~~B19.~~ Bring-your-own-reference RAG — **effort: L** — *wanted (per user)*
**What:** let the author **ingest external reference material** (PDF, plain text/markdown,
maybe a URL) into a project and have the brainstorm/generation ground answers in it — a
research folder, a style guide, or a prior-book "series bible." This is the biggest capability
Writingway's workshop has that we lack (`rag_pdf`, `rag_smart_qa`, `rag_visual_explorer`).
- **Ingest:** upload → extract text (PDFs via a light dep, e.g. `pypdf`) → chunk with the
  existing `chunking.py` → index as a new **`reference` document source** distinct from lore/
  prose (so refs inform but never pollute the lorebook). Store under the project dir.
- **Retrieve:** references flow through the same `search_service`; **best paired with B17**
  (semantic) but works on keyword too. Context builder gets a `references` band with its own
  token sub-budget, clearly labelled so the model cites/uses them as source, not canon.
- **Chat:** a "sources" toggle/picker in the brainstorm drawer to include/exclude refs;
  optional "what did it retrieve" peek (mirrors Writingway's visual explorer, and dovetails
  with B15's context preview).
- **Manage:** list/remove reference docs; refs are excluded from Story/Project export by
  default (they're not the author's prose) — confirm at build.
- **Depends on:** B17 recommended first (semantic makes ref recall much better); reuses
  `document_builder` / `chunking` / `index_manager`.

**Suggested order for this cluster:** B17 (semantic retrieval) → B19 (reference RAG, which
leans on it) with B18 (multi-session) sliding in anywhere since it's independent. B14/B15
remain the immediate near-term items; B16 (TTS) is parked.

---

### B20. OCR for references (scanned PDFs & images) — ✅ **BUILT** (code) / installer step pending

**Decision:** maximize accuracy with **Tesseract** (per user), rasterizing scanned PDF pages
with **PyMuPDF**.

**Status: BUILT (code).** `reference_service.extract_text_with_ocr()` is text-first: it uses
the pypdf text layer, and for pages with little/no text (scanned) it rasterizes via PyMuPDF
(`fitz`, 300 dpi) and OCRs with Tesseract (`pytesseract`); image files (`png/jpg/tiff/…`) OCR
directly. OCR is **auto-detected** (`ocr_available()`, Tesseract binary via `$TESSERACT_CMD`, a
bundled `…/tesseract/tesseract.exe`, or PATH) and **degrades gracefully** — text/text-PDF still
import when OCR is absent; scanned/image imports return a clear "install Tesseract" error.
Uploads are **processed in a background thread** (`register_pending` → `finalize` → reindex) so
slow OCR doesn't block the request; references carry `status` (processing/ready/error) + `ocr`
flags, and the References tab **polls** while processing and shows an **OCR** badge / errors.
Deps: `pymupdf`, `pytesseract` added to `setup.py`. Tests: `tests/test_references.py` (OCR paths
skip when the binary is absent). Full suite **139 passed**; frontend builds clean. Works today
anywhere the Tesseract binary is installed/on PATH.

**Installer bundling — WIRED (verify via CI build):** the build workflow now installs Tesseract
via Chocolatey and stages it to `dist\tesseract`; the Inno script ships it to `{app}\tesseract\`
(guarded with `#if FileExists` so local builds without it still compile), and
`_configure_tesseract()` auto-discovers `{app}\tesseract\tesseract.exe` and sets
`TESSDATA_PREFIX`. Confirm with a `workflow_dispatch` run of *Build Windows Installer* (installer
grows by the Tesseract footprint). Local `iscc` builds without the staged folder simply omit OCR.

## Docs refresh (Docusaurus, **not a wiki**) — low-priority parallel track

Decision (2026-07-01): we already have a **Docusaurus** site in `docs/` wired for GitHub
Pages — so we do **not** start a separate GitHub wiki (it would fragment/duplicate the
in-repo, versioned docs). Instead, revive and refresh the existing site. This is a background
track, not a blocker for feature work.

**Done so far:**
- Retargeted `docs/docusaurus.config.ts` to the fork (`mthous72`, url/org/editUrl, credit line
  keeps Fernando Guerra & Lenxys). Set `onBrokenLinks: 'warn'` temporarily so stale-content
  links don't fail the build.
- Added `.github/workflows/deploy-docs.yml` (build `docs/` → publish to Pages on push to
  `docs/**`). Verified the site builds locally.

**Remaining:**
1. **Manual, one-time:** enable GitHub Pages for the repo with **Source: GitHub Actions**
   (Settings → Pages). Until then the workflow builds but has nothing to publish to.
2. **Content pass** — the current docs are upstream/CLI-era: the blog is still the default
   Docusaurus template ("2019-…first-blog-post"), agent pages describe the old CLI, and none
   of the fork's work is covered. Rewrite intro / getting-started / usage for the **web app**,
   and add feature pages as we ship: providers & model dropdowns, local LLM, Brainstorm
   co-writer + Focus, **smart lore intake** (incl. importing SillyTavern/KoboldAI), export/
   import & version snapshots, and (when built) B14/B15/B17–B19. Fold the **deferred Writingway
   attribution** in here too.
3. After the content pass, restore `onBrokenLinks: 'throw'`.
4. **Internal docs hygiene:** PLANNING.md is ~800 lines doing spec + backlog + history; when it
   gets unwieldy, split shipped specs into a `PLANNING-history.md` / CHANGELOG and keep this file
   to the live backlog.

**Out of scope (separate item if wanted):** an *in-app* help system for authors (a "how do I
use the lorebook / brainstorm" panel inside LibriScribe itself) — distinct from this public
docs site. Not planned yet; raise as its own B-item if desired.

### Deferred task — README attribution for Writingway (do NOT add until integrated)
Once we ship the **first** feature derived from Writingway (likely B14), update `README.md`:
- Add Writingway to the attribution/"sources" area as an additional inspiration for the code,
  crediting original author **a-omukai** (upstream `github.com/a-omukai/Writingway`, MIT).
- Add a **support pointer**: Writingway has **no donation link** today — support is via their
  GitHub issues/discussions and **Discord (`https://discord.gg/xkkGaRFXNX`)**. If a
  sponsor/Ko-fi/etc. link exists at integration time, use that instead; otherwise point to the
  Discord/GitHub as their support channel (mirroring how we credit the original LibriScribe
  author with a Buy-Me-a-Coffee pointer).
- **Trigger:** first Writingway-derived feature merged. **Until then, keep it out of the
  README.**
