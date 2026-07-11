# LibriScribe — Feature Planning & Backlog

Living planning doc. Features are specced here **before** implementation. Nothing
in "Backlog" is built until it has been promoted to a full spec and approved.

Last updated: 2026-07-10

> **B-numbers are stable historical IDs, not build order.** The build order is the **Roadmap** below. Detailed specs keep their original B-number wherever they already live in this doc.

---

## Roadmap — incremental build sequence (consolidated 2026-07-07)

Each phase is a **shippable win that builds on the previous one** and plugs into the current codebase. Ordered so early phases unblock later ones and nothing is built before its foundation.

**Shipped (current software).** Web app (FastAPI + React), lorebook with smart import, brainstorm sessions (focus + per-property aspect, verbosity/length, conversational tone, voice profiles), retrieval (keyword/semantic; brainstorm pinned to keyword after a session's first turn), **B25** entity connections (navigable + pickable + auto-suggest), **B28** gap-finder (structural + AI referenced-but-undefined), **B29** bounded concurrency, edit-project-meta, non-loopback bind, releases through v0.12.0.

**Phase 0 — Stop the bleeding** ✅ **BUILT (PRs #24 #25, 2026-07-07).** Generation currently overwrites the user's title/description and shrinks chapter count, and ignores the lorebook. Fix inside `concept_generator` + `outliner`: **suggest-don't-overwrite** metadata (write `suggested_*`, never clobber) and **lore-ground concept + outline** (inject a KB digest so it builds on the user's world). *Win: generation stops destroying projects and starts using your lore — valuable even before the full redesign.* → foundation for everything generation-related. (Epic **B30**, Slice A subset.)

**Phase 1 — Human-directed generation (**B30**)** ✅ **BUILT (PR #26).** Per-stage gates (stop after every stage), reset, suggestion-apply UI, typed job state, step controller. Builds on Phase 0 (the now-safe, lore-grounded stages get gated). *Win: you direct the story stage by stage.*

**Phase 2 — Consistency guardrails (**B32** → **B31**)** ✅ **BUILT (PR #27).** **B32** canon lock (slim `canon_rules` + seeded categories) injected into the now-grounded/gated stages; **B31** continuity guard checks written chapters against canon+lore (on-demand, Gaps-style report). Builds on Phase 0 (grounding) + Phase 1 (per-stage/chapter flow to hook checks into). *Win: the story stays consistent; canon is enforced.*

**Phase 3 — Actionable staging (**B27** Slice A)** ✅ **BUILT (PR #28).** Sandbox spine (per-run) + review/cherry-pick + **gap→sandbox** seed, so B28 gaps and B25 "unlinked" names become **createable**. Independent of generation. *Win: cherry-pick gap/undefined candidates into the lorebook.* → foundation the wizard stages into.

**Phase 4 — World-seeding wizard (**B38**)** ✅ **BUILT (PR #29).** LLM-authored, project-tailored questions → gather the user's specifics → **elaborate** into lore (never invent) → stage into the B27 sandbox → explore/edit. Two modes: seed a new project / overall-brainstorm an existing one. Builds on Phase 3 (sandbox) + Phase 0 (shared lore digest) + B25/B28. *Win: guided project seeding and whole-project brainstorm.*

**Phase 5 — Revision & deeper consistency (**B34** + **B35** + **B33**)** ✅ **BUILT (PR #30).** **B34** human-directed revision loop (rewrite existing chapters with the Phase-1 controls) + **B35** diff-on-regenerate (cross-cutting, also retro-fits Phase 1) + **B33** character-state/timeline (unlocks B31's "knows-too-early" check + time-aware context). Builds on Phase 1 (shared UX) + Phase 2 (canon/continuity). *Win: human-directed rewriting; the story tracks who-knows-what-when.*

**Phase 6 — Content controls & finishing (**B36** + **B37** slice 1 DOCX)** ✅ **BUILT (PR #31; EPUB/PDF remain).** **B36** gated content-intensity controls (rides the chapter/scene granularity from B30 Slice C) + **B37** export DOCX→EPUB→PDF-later. No hard dependencies; interleave when wanted. *Win: dial content per scene; get a real book out.*

**Parallel / back-burner tracks.** "Claude-like" brainstorming + Higher-end-value output (capture/feed-forward; some already shipped as B23/B26) — enrich the brainstorm side independently. **B21** model warm-up/keep-alive (helps local load times). Story-structure/pacing analysis (parked). Docs refresh. Cloud storage (held).

**Dependency summary.** `Phase 0 → 1 → 2` and `Phase 3 → 4` are the two spines; Phase 5 needs 1+2; Phase 6 is independent. Phase 0 is the urgent entry point.

---

## Backlog (held) — Cloud storage / sync (researched 2026-07-01, HELD per user)

Idea: let users keep project data on OneDrive / Google Drive / Proton Drive. The export/import
`.libriscribe.json` bundle is the natural sync unit. **Held for now** after a Proton reality check.

**Proton Drive reality (key reason held):**
- No official third-party API/SDK ready yet. Proton is building a Drive SDK (JS/C#) but the
  **auth + standalone-integration modules aren't available**, with a crypto migration targeted
  ~end-2026/early-2027. (proton.me/blog/proton-drive-sdk-preview; github ProtonDriveApps/sdk)
- Only path that works today = **unofficial** rclone `protondrive` backend + Proton-API-Bridge
  (reverse-engineered, E2EE-complex, can break on Proton changes). rclone.org/protondrive
- **In-app Proton account sign-up is NOT feasible** (CAPTCHA/anti-abuse + ToS). Best UX =
  connect an existing account + deep-link to Proton's sign-up page.
- Net: Proton is the hardest/riskiest of the three; OneDrive/Google Drive are the easy ones
  (official OAuth: Microsoft Graph / Google Drive API).

**Recommended approach when revisited (phased):**
1. **Sync-folder MVP** — a configurable data directory + guided setup so users point LibriScribe
   at a folder their OneDrive/GDrive/Proton **desktop client already syncs**. Works for all three
   today, zero API/crypto/ToS risk. (Settings already has `projects_dir`; mostly a UI + doc task.)
2. **rclone-backed app-managed backup/restore** — bundle rclone; one `CloudBackend` interface
   (list/upload/download/auth) covering OneDrive + GDrive (official OAuth) and Proton (experimental).
3. **Native Proton SDK** integration once Proton ships third-party auth (~2027).

**Alternative: Supabase (in the back pocket — spec later).** Different model: instead of the
user's own cloud, WE operate a backend. Fits the original "sign up in the app + sync" wish that
Proton couldn't: Supabase **Auth** (real email/OAuth sign-up), **Storage** (S3-compatible; upload
the `.libriscribe.json` bundle per user, RLS-isolated), official libs (`supabase-py` / `supabase-js`),
self-hostable. **Tradeoffs:** we become the data operator (host/pay/GDPR-ish responsibility; cost
scales with users) and it's encrypted-at-rest but **not E2E** — a shift from the current
local-first "nothing leaves your machine" story. **Mitigation:** client-side-encrypt the bundle
before upload (passphrase-derived key) for a Proton-like "we can't read it" property. **Architecture
if pursued:** keep local-first as default; optional account for opt-in backup/cross-device sync;
same `CloudBackend` interface so it coexists with sync-folder/rclone. Needs a Supabase project
URL + anon key (anon key safe to ship; never bundle the service-role key).

---

## Refactoring (from codebase review, 2026-07-01)

A 4-agent maintainability review produced a tiered plan. **Tier 1 (glue dedup + logging)
DONE:** extracted shared helpers — `utils/token_utils.estimate_tokens`,
`utils/file_utils.resolve_chapter_path`, `retrieval/models.{mode_str,matches_filters,
chunk_to_result}`, `services/retrieval_service.{get_retrieval_config,search_service_for,
rebuild_project_index}`, and `project_service.create_llm_client` — and rewired ~20 duplicated
call-sites across chat/lorebook/projects/references/generation + the two indexes; deduped the
`SettingsResponse` builder and `_SMART_FIELDS`; added operational logging to index-rebuild
failures. `tests/test_shared_helpers.py` added; full suite 155 passed.

**Remaining (deferred):**
- **Tier 1 tail:** broad `print()` → `logging` sweep in `utils/file_utils.py`,
  `knowledge_base.py`, and several agents (matters for the windowed build where stdout is None).
- **Tier 2 (structural splits):** split `chat.py`/`lorebook.py` into services + routers;
  frontend — extract oversized pages (ProjectDashboard/LorebookPage), shared `Modal`/`Input`/
  `Button`, domain `types.ts`, and add a vitest setup (no frontend tests today).
- **Tier 3 (bigger):** `llm_client` ProviderAdapter pattern; `Worldbuilding` god-object →
  subclasses; human-review `threading.Event` → `asyncio.Event` + timeout (hang-risk fix).
- **Tier 4 (cleanup):** delete legacy `_save_chat`/`_append`, dead vector-DB settings +
  `RetrievalBackend` enum values, orphaned `editor_enhanced.py`/`formatting_optimized.py`
  duplicates; migrate `configuration.py` `@validator` → `@field_validator`.
- **Skip (over-engineering):** multi-backend retrieval abstraction, structlog, YAML config for defaults.

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

### B21. Model warm-up / keep-alive on project select (+ opportunistic index build) — **effort: S/M** — *backlog (raised 2026-07-02)*

**Motivation.** Local servers (LM Studio, Ollama, llama.cpp) lazily JIT-load a model into VRAM on
the *first* request, so the first real brainstorm/generation call eats the whole load latency
(seconds). Warming the model when a project is opened hides that; a periodic keep-alive when idle
keeps it resident so later calls stay fast. Cloud providers have nothing to load, so this is a
**local-provider optimization** — gate on provider (skip for openai/claude/etc.).

**The warm request must be inconsequential (per user):** tiny prompt, `max_tokens=1`,
`temperature=0`, fire-and-forget; it must **not** touch any brainstorm/session history or "recent
calls" context, and should be excluded from (or tagged separately in) cost tracking so it doesn't
pollute `llm_usage.jsonl` or the cost report.

**Design sketch (build later, not now):**
- **Backend:** `POST /projects/{name}/warm-model` → if the project's provider is local/warmable,
  spawn a background thread that runs a throwaway 1-token `generate_content("ok", max_tokens=1)` on
  a standalone `LLMClient` (never via chat/session code). Swallow errors; return immediately.
  Consider a `warmup=True` flag on the call so `CostTracker` can skip/label it.
- **Frontend:** call it once when a project is opened, then a `setInterval` (~4 min) keep-alive that
  fires **only if** the tab is visible (`document.visibilityState === 'visible'`) **and** no real
  LLM call has happened in the last ~5 min (track a `lastLlmActivity` timestamp). Clear the interval
  on unmount / project switch. Never ping a hidden tab or a cloud provider.
- **Native keep-alive where available:** Ollama supports a `keep_alive` request param (e.g. `"10m"`,
  or `-1` to pin) — prefer passing that over polling when the provider is Ollama; LM Studio uses an
  idle-TTL auto-evict, so for it the periodic tiny request is the right mechanism (resets the timer).
- **Setting:** a toggle to disable background warming (some users won't want the extra local churn).

**Embedding index at project-open — yes, good fit, as a *separate* background task.** Project-open
is a natural trigger to (a) warm a **local embedding** model the same way (its first embed also JIT-
loads), and (b) run an **incremental** semantic/hybrid index refresh so retrieval is ready before
the first brainstorm. Keep it distinct from the lightweight chat-warm because it can be heavier:
- Only when the project's retrieval mode is **semantic/hybrid** AND an embedding source is configured
  (else no-op — keyword needs no index).
- Reuse the existing incremental machinery — `services/retrieval_service.rebuild_project_index` +
  `retrieval/index_manager` **hash-based refresh** — so if nothing changed since last time it's
  ~free (no re-embedding). Run in a background thread; never block project load.
- Surface state via the existing retrieval status readout (ProjectDashboard already shows
  "semantic index ready" / warnings), so a rebuild-in-progress is visible.

**Open decisions to confirm when specced:** warm prompt/token budget; keep-alive interval + idle
threshold (default ~4 min ping / ~5 min idle); whether to expose the enable/disable setting per
project or global; whether index refresh on open is automatic or gated behind the same setting.

### B22. Two-role model routing — Writing vs Utility model — **effort: M** — *APPROVED, building (2026-07-02)*

**Motivation.** Adult/uncensored fiction needs an uncensored model for prose, but "aggressive"
uncensored RP merges follow instructions / emit JSON poorly — bad for the *structured* jobs (lore
extraction, classification). Rather than per-agent granularity (12 confusing dropdowns — a Norman
Door), split into **two roles**:
- **Writing model** = the existing project `model` — prose, brainstorm chat, chapter generation.
- **Utility model** = an optional clean/instruct (ideally uncensored *instruct*, e.g. an abliterated
  or QAT-instruct model) used for structured tasks: lore intake (import classify + AI-map +
  extract-for-type), and brainstorm "Apply to lore" structuring. **Blank ⇒ use the Writing model**
  (so nothing changes for users who don't set it).

Both roles share the project's `llm_provider` (same LM Studio/Ollama server, different loaded model
id) in v1 — no second provider/base-URL. Reuses the existing per-agent plumbing conceptually
(`kb.agent_models` / `_get_model_for_agent`) but exposes a single clean field.

**Backend:**
- `knowledge_base.ProjectKnowledgeBase.utility_model: str = ""` (next to `model`).
- `project_service.create_utility_client(kb)` → `LLMClient(kb.llm_provider)` with model
  `kb.utility_model or kb.model` (falls back to Writing). Mirror of `create_llm_client`.
- Route the structured calls to it: `lorebook._maybe_client` (parse/classify + extract-fields) and
  `chat.extract_from_text` / `chat._extract_fields` (apply-to-lore). Leave brainstorm *chat*
  generation and the generation pipeline on the Writing model.
- Persist via `PUT /{name}/settings` (`utility_model` on `UpdateProjectSettings`); return it in
  `get_project_detail` + `ProjectDetail`; extend `resolve_active_model` to also report the resolved
  utility model + source.

**Frontend (ProjectDashboard AI-config):** a second `ModelPicker` "Utility model (structured
tasks — lore, classification)" with help "leave blank to use the writing model"; saved alongside
provider/model; readout shows both ("Writing: X · Utility: Y (or same as writing)").

**Later (not v1):** route the pipeline's structured agents (outliner, character/worldbuilding JSON,
fact-check) to Utility too; allow a different provider for Utility.

### B23. Brainstorm response verbosity switch (Low / Medium / High) — **effort: S** — *backlog (raised 2026-07-02)*

**Motivation.** Brainstorming sometimes wants terse, direct answers and sometimes wants expansive,
conversational exploration. A quick switch lets the author dial it without re-prompting. Applies to
**all brainstorming** (per request).

**Levels:**
- **Low** — succinct, direct answers; minimal elaboration; get to the point.
- **Medium** — moderate context and some elaboration/freedom (default).
- **High** — verbose, conversational; explores freely.

**Design:**
- **UI:** a Low/Medium/High control in `BrainstormDrawer` (near the composer or session header).
  Persist **per session** (sessions already carry state) so switching sessions keeps its setting;
  default Medium.
- **Backend:** inject a short verbosity directive into the assembled system prompt at
  `chat._assemble_system_prompt` (`chat.py:584`) — one line per level. Keep it **prompt-driven**
  (works across local models). Optionally also nudge `max_tokens` (Low smaller cap, High larger)
  and a touch of `temperature` for the Medium/High "freedom", but instruction-first.
- Thread the level from the chat request → `_assemble_system_prompt`; store it on the session so
  it persists.

**Open decisions:** per-session vs per-project vs global default; instruction-only vs also
tuning max_tokens/temperature; exact wording of the three directives.

### B24. Focus-aware "Apply to lore" — don't re-classify the selected entity — **effort: S/M** — *backlog (raised 2026-07-02)*

**Motivation.** In a focused brainstorm session (a specific character selected), "Apply to lore"
currently runs full multi-entity discovery (`extract_from_text`), which re-classifies the
already-known character from scratch — wasteful and a source of mis-classification. If you've
already selected the character, its info should apply straight to that record; only *new* Codex /
other items in the reply need discovery.

**Design:**
- The session carries `focus` (type, name). Thread it into the apply flow (`chat.parse_to_proposal`
  — add focus to the request, or a focus-aware branch).
- When a focus is present: extract the focused entity's fields with the robust single-entity path
  `lore_intake.llm_extract_for_type(focus.type, reply)` → pre-assigned to that known record
  (status = update). Separately run `extract_from_text` for OTHER entities and drop any that
  duplicate the focus.
- Review panel pre-selects the focused entity's type/name (already merge-able via the name pulldown).
- Reuses: `llm_extract_for_type` (robust), session focus, the merge/name pulldown.

### B25. Interconnect entities — link Characters ↔ Arcs / threads / Codex — **effort: M** — *backlog (raised 2026-07-02)*

**Motivation.** Arcs, plot threads, and codex entries should be tied to the characters they involve
so the lorebook is navigable and internally consistent.

**Current state (partial infra already exists, as free-form strings):** `Character.relationships`
(`knowledge_base.py:27`), `Location.associated_characters` (`:100`), `LoreEntry.related_entities`
(`:110`), `StoryArc.characters_involved` (`:129`); plus `retrieval/cross_reference.py` maps entity
co-occurrence across chapters.

**Design direction:**
- Formalize these into **pickable, navigable links**: choose real record names from a dropdown
  (reuse the review-panel name-pulldown pattern), validated against existing records; store by name
  (matches the merge-by-name model).
- **Bidirectional / navigable in the UI:** a character's page shows their arcs / threads / codex
  entries; click to jump. Same for the reverse.
- Optionally **auto-suggest** links from `cross_reference` co-occurrence.

**Open decisions:** enforce referential integrity vs. keep free-form; how aggressively to
auto-suggest; scope of the relationships panel per entity.

### B26. Brainstorm collaborator preamble — clearer/concise responses + clarifying questions — **effort: S** — *backlog (raised 2026-07-02)*

**Motivation.** The brainstorm system prompt should frame the LLM as a sharp creative collaborator —
clear, specific, concise — and have it **occasionally ask a clarifying question** rather than always
answering blind. Better, cleaner responses and a more useful back-and-forth. Companion to B23
(B23 = length dial; this = behavior contract) — same injection point, design/build together.

**Current state:** `chat._system_prompt` / `_focus_system_prompt`, assembled at
`chat._assemble_system_prompt` (`chat.py:584`), already frame brainstorming and tailor by focus type
— but don't push for crispness or invite clarifying questions.

**Design:**
- Strengthen the preamble into a tight **collaborator contract**: be clear and specific, build on
  the author's idea, cut filler/hedging.
- **Ask ONE targeted clarifying question** when the request is genuinely ambiguous or a decision is
  under-specified — *occasionally*, only when it actually helps (avoid nagging).
- **Tailor by focus**: character → motivation / voice / contradictions; location → atmosphere /
  role in plot; arc/thread → stakes / causality / consequences; worldbuilding → internal consistency.
- Compose with **B23** at `_assemble_system_prompt` (preamble = behavior, verbosity = length).
- Optionally **user-editable** later (like the existing `writing_system_prompt.txt`).

**Open decisions:** single global preamble vs per-focus variants; question frequency/threshold;
user-editable now or later.

## Epic: "Claude-like" brainstorming — **DESIGN (specced 2026-07-02, background planning; no code yet)**

**Goal.** Make brainstorming feel like a sharp collaborator: it *knows the intent* when you focus an
entity, it *proactively surfaces what you haven't considered* via targeted questions you can turn on
and off by dimension, it's controllable along independent axes (length, questioning, depth), and it
spends LLM calls and context freely — because the user runs locally and *more calls / more context is
better than fewer*. Absorbs **B23** (verbosity) and **B26** (collaborator preamble); pairs with
**B24** (focus-aware apply). Everything is **prompt-driven** so it works on local models.

### Where it plugs in (from the code map)
- One LLM call per turn today: `chat.chat` streams `generate_content_streaming(..., max_tokens=700,
  temperature=0.8, system_prompt=...)`. Budgets are deliberately SMALL (700 out, 3000-token history
  window, ~2600-token focus context, ~1800 lore).
- Prompts: `chat._system_prompt` (general) and `chat._focus_system_prompt` (one-entity focus; both
  already say "BE CONCISE"). Focus context assembled by `chat._focus_context` (record + cross-refs +
  involved arcs + world lore + keyword search).
- Session is a flat dict (`_new_session`): `{id,title,focus,messages,summary,summarized_upto}` —
  **no prefs field yet**. Threading model already proven for `focus`/`use_references`:
  BrainstormDrawer → `streamChat` → `ChatRequest` → `_assemble_system_prompt`, persisted per session.
- Multi-call precedents to reuse: `generation_service` (sequential stages), `lore_intake.llm_classify_all`
  (per-entry loop), `context_builder` (token-budget cascading retrieval), `retrieval` +
  `cross_reference` (co-occurrence).

### Design

**1. Per-session `prefs` (foundation).** Add `prefs` to the session dict + `SessionCreate/Update`;
accept on `ChatRequest` (or read from the resolved session); thread to `_assemble_system_prompt`.
Persist in `chat_sessions/{id}.json` like `focus`. Global defaults in Settings (.env) seed new
sessions. Shape:
```
prefs = { "verbosity": "medium",              # low | medium | high  (B23)
          "questioning": {"motive": true, "detail": false, "connectivity": true},
          "depth": "single" }                 # single | multi (agentic enrichment)
```

**2. Focus-aware intent lenses (extends B26).** Per-focus-type framing so the model knows the job:
character → motivation / voice / contradictions / relationships / arc; location → atmosphere / role
in plot; arc → stakes / causality / consequences; lore → internal consistency; worldbuilding →
coherence. One "intent lens" block appended to `_focus_system_prompt`; keep the one-entity-focus rule.

**3. Verbosity axis (B23).** Low/Medium/High → a prompt directive **and** `max_tokens`
(~250 / ~700 / ~1500+) and a slight temperature nudge. Instruction-first.

**4. Questioning switches — surface the unthought-of.** Master on/off + independent **dimension**
toggles, each a lens:
- **Motive** — why: drives, goals, fears, stakes, what they want vs. need.
- **Detail** — concrete specifics: sensory texture, mechanics, habits, contradictions in the record.
- **Connectivity** — links: to other characters / arcs / lore, consistency checks, unexploited ties
  (seed from `cross_reference` co-occurrence + retrieval).
Two operating modes (gated by **depth**):
- *Inline* (single call): append "then ask 1–3 targeted <enabled-dimension> questions" to the system
  prompt. Cheap.
- *Dedicated passes* (agentic, when depth=multi): after the main answer, one LLM call **per enabled
  dimension** generating grounded questions; render as a distinct "Questions to consider" block.

**5. Multi-pass enrichment (agentic; "more calls > fewer").** A turn expands into a pipeline:
(1) main response → (2) per-enabled-dimension question pass(es) → optional (3) a connectivity
"gaps / inconsistencies" critic that checks the focus record against established lore → optional
(4) synthesis. **Stream the main response first** (fast), then append enrichment as each pass
returns (progressive) so latency is hidden. Reuse the sequential-stage + token-budget patterns.

**6. Generous context usage.** Raise the focus/lore/window budgets (e.g. focus 2600 → 6–8k) and make
them **model-aware** (scale to the loaded context window). Front-load the full focus record +
cross-referenced companions + involved arcs + world lore + **semantic/hybrid** retrieval of relevant
prose (brainstorm currently defaults to keyword) + the rolling summary. Local large-context models
have the room — use it.

**7. Quality contract (absorbs B26).** Collaborator preamble: specific, non-sycophantic, builds on
the idea, no filler; a few strong options not everything; flag novel vs. established; ask ONE
clarifying question when genuinely ambiguous (this baseline is separate from the proactive
Questioning switches).

### UI (BrainstormDrawer prefs panel, below Focus/References)
Verbosity (Low/Med/High) · Questioning (master toggle + Motive/Detail/Connectivity checkboxes) ·
Depth (single vs multi-pass). Persisted per session via `updateSession`; global defaults in Settings.

### Suggested build order (each shippable)
1. Per-session `prefs` model + threading (foundation).
2. B23 verbosity + B26 preamble/intent lenses (prompt-only, small, immediate win).
3. Questioning dimensions — inline mode first.
4. Multi-pass enrichment + progressive streaming; questioning dedicated passes.
5. Context-budget expansion + semantic retrieval in brainstorm.

### Open decisions
- Inline vs dedicated-pass questioning, or both gated by Depth (leaning: both, Depth switches).
- Questions per dimension (1–3) and how they're surfaced (appended block vs. clickable follow-ups).
- Context budgets: fixed-larger vs. model-aware scaling (leaning: model-aware).
- Global defaults home (.env keys vs. a `brainstorm_prefs` file).
- Latency/cost of multi-pass — mitigated by local-only default + progressive streaming.

### Higher end-value output — organize, capture, feed-forward (detective pass, 2026-07-06)

**Thesis.** A Gemma-12B reaches "Claude-like" *end value* not by being smarter but by **orchestration
+ organization + feed-forward**: decompose each turn into small focused passes (which a 12B nails),
and turn the output into durable artifacts that seed the writing — instead of prose that dies in chat
scrollback. This is the point of the whole epic; the switches (B23/B26/questioning) shape *the reply*,
this section makes *the reply worth keeping*.

**What the writing side already consumes** (so we know what to aim brainstorm output at) — from
`services/context_builder.py`, all auto-injected into each scene prompt: `Scene`{summary, characters,
setting, goal, emotional_beat, scene_type, target_word_count}; `ArcMilestone`{milestone_type,
target_chapter, description, status}; `NarrativeThread`{thread_type, description, opened_chapter,
target_resolution_chapter, status, characters_involved}; `Character`{motivations, character_arc,
internal/external_conflicts} + `VoiceProfile`{speech_patterns, vocabulary_level, verbal_tics, avoids,
example_dialogue}; `CharacterState` per chapter; `Location`/`LoreEntry`/`Worldbuilding` fields.

**1. Emulate Claude by decomposing the turn (reuse proven local patterns).**
- **draft → self-critique → refine** — `agents/concept_generator.py` already does exactly this in 3
  small calls (generate JSON → plain-text critique → refine). Stream the draft first, fold the refined
  version in. This single pattern is what makes a 12B read like one sharp Claude answer.
- **options → judge/rank → recommend** — generate N options, a scoring pass ranks them, present the
  ranked shortlist + a recommendation (mirror `fact_checker`'s per-item loop).
- These ARE the epic's "multi-pass enrichment", now mapped to existing, local-friendly code.

**2. Ground + stay consistent.** A consistency pass checks each new idea against established lore
(retrieval + the focus record) and flags contradictions — reuse `fact_checker`'s extract-claims →
check-each, pointed at lore instead of the web. (Small models drift; this anchors them.)

**3. Capture the value — the GAP (session "Working Document").** Today only lore *entities* have a
home; decisions, rationale, parked options, and open questions vanish into chat history. Add a
persisted, structured **Working Document per session**: `decisions[]`, `open_questions[]`,
`parked_ideas[]` (each with a one-line rationale), auto-populated by a small **capture pass** after
substantive turns + user-editable. Feed settled `decisions` back into the system prompt so the 12B
stops re-litigating them — a big consistency win for small models.

**4. Feed-forward into writing — the payoff.** Generalize "Apply to lore" into **"Promote to
&lt;structure&gt;"**: from a brainstorm turn, offer *typed* promotions that the writing pipeline already
consumes — **arc milestone** (with target chapter), **narrative thread** (with resolution chapter),
**scene beat**, **voice tic/profile**, **character field** — via the proven per-entity extractor
(`lore_intake.llm_extract_for_type`) extended to these types + smart-merge. This is the highest end
value: brainstorm output directly seeds outline/scene/chapter generation.

**5. The capture pass is the organizing spine.** One small structured pass per substantive turn emits:
Decisions, Open questions, and *promotable typed artifacts* ("reads like an arc milestone ~ch 7"; "this
is a voice tic"). Surface as lightweight **accept-chips**; one click writes to the Working Document or
promotes into the KB structure. Keeps the reply conversational (Claude-like) while continuously
producing structured, feed-forward output on a side lane.

**Reusable building blocks (code map):** `concept_generator` generate→critique→refine;
`fact_checker` extract→check-each; `lore_intake.llm_extract_for_type` (per-entity, schema + example —
the gold pattern for 12B); `lore_intake.merge_apply` smart upsert; `context_builder.TokenBudget`;
`chat._manage_session_memory` rolling summary; `llm_client` structured-output + repair. All
local-model-friendly.

**Open decisions:** force structure on the chat reply vs. keep it conversational (lean: conversational
reply + a separate capture/promote lane); Working Document auto-populated vs. user-curated (lean:
auto-suggest → user confirm); which promotion targets ship first (lean: arc-milestone +
narrative-thread + character-field — they most directly feed the writing). Extends B24 (focus-aware
apply) and B25 (interconnection).

## Epic: Autonomous exploration ("Auto mode") → sandbox + gap-finder — **DESIGN (specced 2026-07-07, planning only; no code yet)**

**One-liner.** A mode where the LLM *thinks*, then autonomously pulls threads across characters / codex / lore / arcs — going down rabbit holes — and stages every candidate into a **sandbox** (NOT the live KB) that the author reviews and **cherry-picks** (accept / reject / edit per item). A companion **gap-finder** seeds it with missing/dangling references. Runs several LLM calls **concurrently** (the user hosts on **LM Studio, which allows 4 concurrent predictions** for the selected model). This is the *autonomous head* of the "Claude-like brainstorming" epic and its "Higher end-value output" section — same passes (draft→critique→refine, consistency, capture, promote-to-structure), driven by an orchestrator instead of one turn at a time.

**Why this is buildable on a 12B, locally:** every unit of work is a small focused pass the 12B already nails (per `lore_intake.llm_extract_for_type`, `concept_generator`, `fact_checker`); the *orchestrator* is deterministic Python (like `generation_service`), and the *sandbox* generalizes the existing per-item accept/reject proposal review. Nothing here needs a smarter model — it needs organization + concurrency + a review surface.

### B27. Auto-explore orchestrator + sandbox — **effort: L (phase it)**
- **Seed / scope** (what to explore): whole project · a focused entity · a category ("expand all thin characters") · the gap-finder's output (B28).
- **Orchestrator loop** (deterministic control; the model only *thinks* inside each pass):
  1. **Survey / think pass** — read a token-budgeted digest of current lore (retrieval + KB) and emit a *prioritized exploration plan*: a queue of "threads to pull" (e.g., "Tya's unexplained betrayal", "Codex names 'the Ashfall' but it's undefined", "no arc connects X and Y"). This is the "do some thinking first" step.
  2. **Fan-out** — for each thread, up to the concurrency cap (B29), run a focused enrichment mini-pipeline: **draft → self-critique → refine** (`concept_generator` pattern) → **consistency check** against established lore (`fact_checker` extract-claims→check-each, pointed at retrieval + the focus record). Produces *typed candidate artifacts* (character fields, new codex/lore, arcs, narrative threads, voice, scene beats — the shapes the writing pipeline already consumes).
  3. **De-dupe + annotate** — dedupe against the KB and against other candidates; tag each with source-thread, rationale, confidence, new-vs-update, provenance.
  4. **Stage into the sandbox** — write candidates to a **persisted staging store** (`projects/<p>/sandbox/<run_id>.json`), never the KB. Multiple runs kept, listed, abandonable.
  5. **Expand or stop** — threads discovered mid-pass (the "rabbit hole") get queued; stop when a stopping criterion trips (below).
- **Review / cherry-pick UI** — a Sandbox panel: candidates grouped by category & source-thread; per-item **accept / reject / edit**; bulk accept-by-filter; **"Apply accepted"** → `lore_intake.merge_apply` into the KB. This is the core UX and it reuses `LoreProposalReview`'s accept/reject affordance, scaled up and persisted.
- **Reuses:** `lore_intake.llm_extract_for_type` / `merge_apply` / `build_proposal`; `concept_generator` critique→refine; `fact_checker` consistency; retrieval (`search_service`, `document_builder`); the proposal-review component; `context_builder.TokenBudget`.

**Stopping criteria (the user's "how do we present a stopping point?" — offer a few, combine):**
- **Budget cap (primary, fits token-free local):** max LLM calls · max wall-clock · max tokens per run, with a **live counter + Stop button**. ("Explore for ~200 calls.")
- **Queue-drain (natural convergence):** stop when no new threads/gaps surface.
- **Diminishing returns (loop-until-dry backstop):** stop when the last K threads produced < X net-new candidates (dedupe/consistency rejection rate climbing).
- **Structural caps:** N expansion rounds, M depth per thread, ≤N new items per entity/category (runaway guard).
- Always a hard **Stop/cancel** + progress readout ("thread 12/40, 3/4 workers busy, 58 staged").

### B28. Gap-finder — **effort: S (structural) + M (LLM)** — huge value, ships partly with **zero LLM**
Finds what's *missing or dangling* and stages it into the same sandbox:
- **Structural invariants (deterministic, no LLM — fast, precise, ship first):**
  - Arcs / narrative threads opened but never resolved (`opened_chapter` set, `resolved_chapter` / resolution empty).
  - `characters_involved` / `associated_characters` / `related_entities` naming entities that **don't exist** in the KB.
  - `first_appearance` / target chapters that exceed `num_chapters` or point at missing chapters.
  - "Thin entity" report — characters with empty writing-consumed fields (`motivations`, `character_arc`, `voice_profile`); locations/lore referenced in prose (via `cross_reference`) but with empty `description`/`significance`.
- **Referenced-but-undefined pass (LLM):** extract named entities/proper nouns from prose + lore fields, diff against the KB, surface names referenced but unrecorded ("'the Ashfall Compact' appears 4×, no Codex entry").
- **Connective-tissue pass (LLM, optional):** arcs with no turning points, threads with no involved characters, characters with no relationships.
- **Output:** each gap → a staged candidate — either a *create-X stub* or an *enrich-X task* — with **evidence** (where it's referenced). Cherry-pick which gaps to fill; filling one hands off to a focused B27 generation. The `retrieval/cross_reference.py` index already maps entity references across chunks — the inverse (referenced-but-undefined) is the new pass.

### B29. Bounded concurrency infrastructure (shared) — **effort: S/M**
- `LLMClient` is sync; the pipeline already offloads via `asyncio.to_thread` (see `generation_service`). Add a **bounded parallel runner**: `asyncio.Semaphore(N)` over `asyncio.to_thread(client.call, …)` (or a `ThreadPoolExecutor(max_workers=N)`), `N` from a **per-provider `max_concurrency`** setting — **LM Studio default 4** (user's host), cloud higher, most others 1–2.
- **Verify** the sync client is safe under concurrent use (its `requests`/`httpx` session); if not, one client per worker or a small pool. Fallback chain still applies per call.
- **Progress** via the existing `EventCallback` → WebSocket bridge (reuse the generation streaming plumbing) so the sandbox UI shows live worker/stage counts.

### Context + response-length expansion (user note)
Auto mode leans on the **utility model** for structured passes and needs **bigger context + higher max_tokens** than interactive brainstorm: the survey pass ingests a large lore digest; enrichment passes emit long structured output. Add **per-mode overrides** (auto-mode context budget + response cap) distinct from the just-shipped interactive verbosity/`max_tokens` controls. **B21 (warm-up/keep-alive)** matters more here (many back-to-back calls).

### Decisions (locked 2026-07-07)
- **Auto-accept: NEVER.** Everything stages; the author always cherry-picks (accept/reject/edit) before anything merges. Non-negotiable.
- **Sandbox granularity: per-run.** Each Auto/gap run writes its own `sandbox/<run_id>.json`, listed so runs can be compared and abandoned. No single global sandbox.
- **Refine-step model: utility model only** (for now). All Auto-mode passes — survey, enrich, critique, refine, consistency — use the utility model. Using the writing model for the creative refine step is a *later* option, not in the first build.
- **Concurrency must be switchable OFF.** Default `max_concurrency` = 4 for the user's LM Studio host, but the setting must support **1 (fully serial)** to disable parallelism — e.g. OpenRouter free models where concurrent calls trigger rate limits. So: per-provider `max_concurrency` (1 = off), user-overridable; when 1, the runner degrades to sequential (same code path, semaphore of 1). Don't hard-code 4 anywhere.

### Still open (resolve at build time)
- Default stop criterion + value (lean: **budget-in-LLM-calls + live counter + Stop button**, diminishing-returns backstop on).
- Gap-finder placement (lean: a **seed strategy** for Auto mode **and** a standalone instant structural report).
- **Verify** the sync client is safe under concurrent use before relying on >1 workers (if not, one client per worker / small pool).

### Phasing / effort
**B29** ✅ (concurrency infra) → **B28 structural gap-finder** ✅ (zero-LLM) → **B28 LLM gap passes** ✅ (referenced-but-undefined, parallel) → **B27 orchestrator + sandbox + review UI** (L, sliced below). Extends the "Higher end-value output" section, B24 (focus-aware apply), B25 (interconnection); the property-narrowed apply is the per-item extractor the fan-out reuses.

### B27 — detailed slicing (planned 2026-07-07; build in order, each slice ships independently)

The sandbox is the spine — build it first, fill it from something that already produces candidates (the gap scan), and only then add the autonomous engine. Each slice is independently shippable, testable, and useful.

**Shared data model (fixed up front so slices don't churn it).**
- `projects/<p>/sandbox/<run_id>.json` — one file per run (per-run granularity, locked).
- **Run**: `{ id, created_at, seed: {kind, ...}, status: complete|running|cancelled, applied_at, candidates: [Candidate] }`.
- **Candidate**: `{ id, category: characters|locations|lore|arcs|threads, name, op: new|update, fields: {...}, status: pending|accepted|rejected, source: str, rationale: str, confidence: float|null, evidence: str }`.
- `fields` reuses the exact shape `lore_intake.merge_apply` already consumes (incl. `voice_*`), so **Apply = merge_apply over accepted candidates grouped by category** — no new merge logic.

**Slice A — Sandbox store + review UI + gap→sandbox seed (NO orchestrator, minimal LLM).** *effort: M*
- `services/sandbox.py` (pure/testable): `create_run`, `list_runs`, `get_run`, `set_candidate_status`, `edit_candidate`, `delete_run`, `apply_accepted(kb, run)` → builds cats from accepted candidates → `merge_apply` → marks run applied. **Never auto-accepts** (locked).
- Endpoints: `GET/POST /projects/{p}/sandbox`, `GET/DELETE …/{run_id}`, `PATCH …/{run_id}/candidates/{cid}` (status/fields), `POST …/{run_id}/apply`.
- **First filler (closes the gap→act loop):** `POST /projects/{p}/gaps/to-sandbox` — stage the deep-scan's `undefined_entity` findings as **create-candidates** (name + suggested category + evidence). This makes B28's AI output *actionable* without the orchestrator: find gap → stage → cherry-pick → merge.
- UI: a **Sandbox** surface (Lorebook tab or its own page) — run list; open a run; per-candidate accept/reject/edit; bulk accept-by-filter; **Apply accepted**. New/update badges reuse the proposal-review affordance.
- Ships: a persisted, reviewable staging area you fill from gaps and cherry-pick into the KB. Tests: store CRUD; `apply_accepted` merges ONLY accepted; gap→candidate mapping.

**Slice B — Auto-explore orchestrator writing into a sandbox run.** *effort: L*
- `services/auto_explore.py` (deterministic loop, mirrors `generation_service` to_thread + EventCallback): **survey/think pass** → prioritized thread queue → **fan-out enrichment** per thread (`concept_generator` draft→critique→refine + `fact_checker`-style consistency vs retrieval/focus) via `bounded_map` at `max_concurrency` → dedupe vs KB + siblings → **stage candidates** into a new run (utility model only, locked).
- **Stop:** budget in LLM-calls with a live counter + hard **Stop/cancel** (primary); queue-drain; diminishing-returns backstop; per-entity caps. Progress via the WS bridge.
- Endpoints: `POST …/sandbox/auto-explore` (seed + budget → starts a run), cancel; run appears in Slice A's list and is reviewed there.
- Tests: loop with a fake client — thread queue drains, budget stop trips, candidates land, cancel halts. Ships: the autonomous "rabbit hole" → sandbox; review/apply reuse Slice A.

**Slice C — Seeds, quality, and create-from-gap generation.** *effort: M*
- More seed strategies: focus entity, category ("expand all thin characters"), and **gap-driven** (feed B28's thin-character/undefined findings straight in as threads).
- **Create-from-gap (direct):** a gap → focused generation → staged candidate (bridges B28 ↔ B27 beyond the raw stub from Slice A).
- Consistency/provenance polish: show source-thread + rationale + confidence per candidate; diminishing-returns tuning; per-entity caps surfaced in the UI.

**Still-open at build time (unchanged):** default budget value; verify the sync client is safe under >1 workers *before* Slice B relies on parallel fan-out (Slice A is serial/LLM-light, so this can be verified in parallel with Slice A).

## Epic B30: Human-directed, step-by-step generation — **DESIGN (specced 2026-07-07, planning only; no code yet)**

**Problem (user).** "Start Generation" runs the whole book end-to-end with no pauses — no chance to check the story's direction, no stop at concept before outlining, no chapter-by-chapter control. Too much automation, not enough letting the human direct the story. It also **overwrites the user's story title** (and other metadata). Wanted: take the automation away, make each step explicit and human-directed, allow **reset**, and make generation only **suggest** metadata for approval.

**Current state (investigated 2026-07-07, with seams).**
- `STAGE_ORDER = concept → outline → characters → worldbuilding → chapters → formatting` runs unattended in one loop (`generation_service.py:75-84`); the only between-stage check is cancellation — **no inter-stage gate**. Each stage auto-saves + auto-advances (`project_manager.py:432-469`).
- The ONE human gate is per-chapter and only when `review_preference="Human"` (default `"AI"`): a `threading.Event.wait(3600)` after each chapter (`project_manager.py:515-537`), two options (proceed / apply_ai_style), **no reject**.
- Reusable HITL primitive: `human_review_required` event + `paused_for_review` status + `GenerationJob.review_threading_event`/`review_decision` + `submit_review_decision` (REST `/generate/resume` or WS) (`job_manager.py:66-72`).
- **Title clobber:** `concept_generator.py:131-137` unconditionally overwrites `title`/`logline`/`description`, persisted at `project_manager.py:440`. `outliner.py` also overwrites `num_chapters` (recomputed/clamped, `:96,462,487,490,508`) and sometimes `description` (`:434`).
- Frontend: free-form `jobStatus` string; one review panel with two "proceed" buttons (no reject/regenerate/reset); only Versions (save/restore) for "going back."

**Decisions (from user, 2026-07-07).** Gate after **every** stage (explicit approve to advance; nothing auto-advances). Chapters: support **both** — one-at-a-time (outline→approve→write→approve→next) AND outline-all-then-write-chapter-by-chapter (user chooses, "depending on how much story I have in my head"). Per-stage actions: **edit + save**, **edit → use as guidance for a rewrite**, and **flat regenerate**. Concept **suggests** a title (never overwrites). Reset must be possible.

**Lore-grounded generation (core pillar — every stage builds on the lorebook).** *Verified 2026-07-07:* the concept and outline stages are **blind to the lorebook** — `concept_generator.py` reads none of the KB entities (it invents from the description alone), and `outliner.py` only parses character names out of *its own* generated outline; neither injects the user's characters / locations / codex / arcs / threads / worldbuilding. The lore-injecting `context_builder` is used **only** in chapter writing. This is why generation produced a random world instead of the user's. **Fix:** build a compact **lorebook digest** (KB entities — characters with role/motivation/arc, locations, codex, arcs, threads, worldbuilding) and inject it into **every** stage's prompt so the model *extends the user's world* rather than inventing one. Reuse `context_builder` + a KB summary with keyword retrieval (no embedding swap). The character/worldbuilding stages must **augment** existing records (merge-by-name dedupe), never duplicate or overwrite them. This applies across all slices below.

**Design — a stepwise controller (nothing auto-advances).** Replace the fire-and-forget run: each stage runs only on request, then STOPS for review. Between steps the user edits the artifact with the existing editors (lorebook / outline / chapter) and chooses **Approve & continue**, **Regenerate** (optionally with a guidance note), **Edit → save → approve**, or **Reset** to an earlier step. Preferred implementation: **one-stage-per-request** (each step is its own short run that saves and stops) — avoids the fragile 3600 s blocking-thread model and makes "no automation" the literal default. Keep an optional **"run remaining automatically"** escape hatch for users who want the old behavior.

**Slice A — stop the automation + stop clobbering metadata (MVP; addresses the core complaint).**
- **Per-stage gate.** Add `generation_mode: 'step' | 'auto'` to the KB (default **step**). In step mode the controller runs exactly one stage then stops with a `stage_awaiting_approval` event; "Approve & continue" runs the next. Generalize the `human_review_required`/`submit_review_decision` plumbing to fire after each stage's `save_project_data()` (KB already persisted there — a natural checkpoint).
- **Suggest, don't overwrite.** Concept writes `suggested_title` / `suggested_logline` / `suggested_description` (new KB fields) instead of the canonical fields; the review UI shows each with an **Apply** button. Guard the outliner: treat user `num_chapters` as a target/cap (suggest, don't silently replace) and skip the `:434` description overwrite when the user set one.
- **Lore-grounded from the first stage.** Inject the lorebook digest into the concept + outline prompts so the story is built from the user's characters/world, not invented. (Full grounding across all stages is the core pillar above; concept + outline are the highest-impact and land here in Slice A.)
- **Reset.** A "Reset to <stage>" control that snapshots (Versions) then marks that stage + downstream incomplete so the flow re-gates there.
- Ships: generation stops after every stage, the title is never reset, generation builds on your lore, and you can go back.

**Slice B — per-stage review actions (edit / regenerate / guidance).**
- Review panel per stage shows the produced artifact + actions: **Approve & continue**, **Regenerate**, **Edit → save → approve** (opens the relevant editor; save via existing endpoints), **Add guidance → regenerate** (a note like "darker, fewer characters" injected into that stage's agent prompt).
- Backend: stage-run accepts optional `guidance`; regenerate re-runs the stage.

**Slice C — chapter granularity (both modes).**
- Choose per project/session: **outline-all-then-write** (full outline, then write chapters one at a time with approve each — reuses today's outliner + the existing per-chapter gate) OR **one chapter at a time** (outline a single chapter → approve → write → approve → next), which needs the outliner to support single-chapter outlining.
- Per-chapter approve / regenerate / edit-with-guidance (generalize the existing chapter gate; add reject/regenerate).

**Slice D — UI: step controller + typed state.**
- Typed `jobStatus` (`idle | running_stage | awaiting_approval | stopped | completed | failed`); `pendingReview` carries the stage id + artifact.
- Dashboard: a step controller — current step highlighted; **Run this step / Approve & continue / Regenerate / Reset to…**; artifact preview; suggestion-apply chips (title etc.). Wire the existing `getCurrentJob` to rehydrate on reload.

**Open decisions (resolve at build).** step-only vs `step`/`auto` toggle (lean: default step, keep auto escape hatch); "Apply suggested title" one-click vs auto-apply only when the user's title is blank (lean: one-click, never auto); reset granularity — single stage vs stage+downstream (lean: offer both); where single-chapter outlining lives in the outliner (Slice C).

**Reuses:** the `human_review_required` / `paused_for_review` / `submit_review_decision` gate; `save_project_data` per-stage checkpoints; Versions snapshot/restore for reset; existing entity/outline/chapter edit endpoints for hand-edits; the WS streaming bridge.

## Epic B38: Guided story-seeding wizard (Q&A → generate lore → explore/edit) — **DESIGN (specced 2026-07-07, planning only; no code yet)**

**Concept (user idea).** A separate, optional flow that **gathers the user's specific information** through structured questions — e.g. *how many main characters*, each character's info, *the high-level story arcs*, the setting — and then **elaborates those specifics into full lorebook records** (characters, locations, codex, arcs, worldbuilding, threads) the user explores and edits. This is **world-seeding, not prose writing** — explicitly a whole separate function from Start-Generation.

**NOT an invention engine (user clarification 2026-07-07).** The point is to **collect concrete parameters and expand them**, never to invent a random book. The user's answers are authoritative: counts (# main characters, # arcs), names, roles, arc shapes, setting — the system only **fills in the detail** the user didn't specify, strictly grounded in what they did. It elaborates; it does not originate the story.

**Why separate.** Start-Generation writes chapters; this builds the world. Someone with just an idea answers a handful of questions and gets a rich, editable lorebook to start from — then uses step-by-step generation (the other epic) to write. It's the on-ramp for a new project, and it's the counterpart to lore-grounded generation: **the wizard fills the lorebook that the generator then builds on.**

**Two modes (user clarification 2026-07-07).** (1) **Seed a new project** — gather specifics from scratch and elaborate into a starting lorebook. (2) **Overall brainstorming for an in-progress project** — run the same structured intake against an EXISTING project to expand/develop it: questions are pre-filled from the current KB, the user adjusts (add 2 more characters, a new arc, deepen the setting), and elaboration is **grounded in the existing lore** (merge-by-name, no duplicates). Same engine, different entry point — a project-level "brainstorm the whole thing" pass, complementing the per-entity focused brainstorm.

**Design.**
- **Question set — gather concrete parameters, not vibes.** Ask for the specifics the user actually has in mind: **how many main characters** (then per character: name/role/key trait), **the high-level story arcs** (name + shape, how many), the **setting/world**, central conflict, tone + genre, key factions / items / rules. Counts and named items drive how many records to elaborate. Keep it short and **staged** (answer a few → generate → refine) rather than one giant form.
- **LLM-authored, project-tailored questions (user idea 2026-07-07).** Beyond a small fixed core, **use the LLM to generate the questions themselves**, tailored to *this* project — its genre/category, title/premise, book length, and (for the in-progress mode) the existing lore digest. A mystery gets "Who's the detective? What's the central crime? Who are the suspects and their motives?"; a court-intrigue fantasy gets different ones. The generated questions are **stored** in the vestigial `dynamic_questions` KB field (`knowledge_base.py:207`, currently stored-but-unused) as `{question: answer}` (answers start empty), so they persist, and the user can **edit / add / remove / regenerate** them before answering. This is a small pass (reuse `concept_generator`/`llm_client` structured output) and it also powers the "adaptive follow-ups" — 1–2 further clarifiers generated from prior answers (ties to the brainstorm epic's "questioning" switches).
- **Generation.** From the answers, run focused passes per entity type — reuse `concept_generator` draft→critique→refine + `lore_intake.extract_from_text` / `llm_extract_for_type` + `merge_apply` — fanned out via `bounded_map` (B29), one pass per category. Produces typed candidates: characters (role/motivation/voice), locations, codex, arcs, threads, worldbuilding.
- **Review + cherry-pick.** Stage the generated lore into the **B27 sandbox** (per-run) so the user accepts / rejects / edits before it lands in the KB — this makes the wizard the **first real seed strategy for the sandbox**; the two features reinforce each other. (Fallback if built before B27: the existing proposal-review + `merge_apply`.)
- **Explore + edit.** Once applied, the user refines with the existing lorebook — editors, connections (B25), gaps (B28), brainstorm.

**Relation to the rest.**
- **Reuses:** `lore_intake` (extract/merge), `concept_generator` (draft→critique→refine), **B29** concurrency, **B27** sandbox (cherry-pick), the vestigial `dynamic_questions` field.
- **Distinct from** the step-by-step *prose* generation epic (writes chapters); this seeds the world. They chain: **wizard → lorebook → step-by-step generation.**

**Open decisions.** Fixed vs adaptive questions (lean: fixed core + optional 1–2 adaptive); where it lives — a New Project "guided" path vs a standalone "Seed my world" action on an existing/empty project (lean: **both**); direct-to-lorebook vs stage-in-sandbox (lean: sandbox once B27 exists, proposal-review before then); how many questions (lean: 6–8 core, staged).

**Effort: M/L.** Best sequenced **after B27 slice A** (so it can stage into the sandbox), though the question UI + a direct-to-proposal generation could ship earlier.

## Plan-review additions (2026-07-07) — consistency, revision & finishing

Gaps surfaced by reviewing the whole plan set. Worked through with the user one by one; only approved items are recorded here.

### B31. Continuity guard — check written prose against canon — **effort: M** — *APPROVED (2026-07-07)*

**The gap.** The gap-finder (B28) is entirely **pre-writing**. Once chapters exist, nothing checks the actual prose against the lorebook. The machinery already exists but is **unwired**: `fact_checker` (agent + `project_manager.check_facts`, reachable only standalone), the continuity checker, and the `ContinuityNote` model — none run in the writing flow.

**What it does.** On demand, run a pass over a written chapter (or the whole manuscript) that flags contradictions against canon:
- a character described against their record (eye colour, age, role);
- a dead/absent character reappearing;
- a location / codex fact contradicted;
- (LATER, needs B33) someone knowing something they shouldn't yet.

**How it surfaces.** Findings render like the **Gaps tab** — grouped, each with the offending chapter + the canon it violates, click-to-jump. **Read-only**: the author decides whether to fix the prose or update the lore (the story may have legitimately evolved). Nothing auto-edits the text.

**Decisions (locked).** **On-demand** (a "Check continuity" button + a Continuity report tab), NOT automatic — it's an LLM pass and auto-running it every chapter adds latency on local models and fights the human-directed feel. An **optional "auto-check after each chapter" toggle** in the step-by-step flow is a later enhancement, default off. **Scope first** the checks with no dependency (contradicted facts, description drift, dead/absent reappearance); the "knows too early" check waits for **B33** (character-state/timeline).

**Reuses.** `fact_checker` extract-claims→check-each pointed at lore + retrieval (keyword, no embed swap); `ContinuityNote`; the Gaps-tab report pattern; `bounded_map` (B29) to check chapters in parallel. Part of the **consistency cluster** with B32 (canon lock) and B33 (character-state/timeline), to be worked through next.

### B32. Canon lock / story bible — inviolable rules generation must respect — **effort: S/M** — *APPROVED (slim, 2026-07-07)*

**The gap.** Lore-grounding injects everything as equal-weight, advisory context. Nothing lets the author mark a subset as **immovable** — especially high-level facts that aren't a lore field at all (tense, POV, "never happens"). And the continuity guard (B31) has nothing to enforce *strictly*.

**Design (slim).** A per-project **`canon_rules: list[str]`** — a short, author-owned list of one-line rules. Injected into **every** generation stage's prompt with strong phrasing ("These are INVIOLABLE — never contradict"), and treated by B31 as **high-severity** (a canon violation is a warn/error; ordinary drift is info). Optional lighter secondary: a `canon: bool` flag on individual records to mark a specific record's facts as locked. No heavy system.

**Seeded rule categories (UI scaffolding, author edits freely).** The Canon Rules panel ships with these as collapsible prompts / example chips so it's never a blank box:
- **Voice & POV** — "Third-person limited, Maren's POV only — no head-hopping within a scene."
- **Tense** — "Past tense throughout."
- **Character fates & immutable traits** — "Maren dies in Ch. 12 and never reappears." / "Cee is an android and cannot lie."
- **World / magic-tech hard limits** — "Magic can't raise the dead." / "No tech beyond steam."
- **Timeline / chronology** — "The story spans one winter." / "No flashbacks before Ch. 5."
- **Relationship constraints** — "Tya and Cee don't meet until Act 3." / "No romance between Maren and the antagonist."
- **Never-happens (prohibitions)** — "The villain is never redeemed." / "No deus-ex-machina rescues." / "No modern slang."
- **Terminology & spelling** — "Always 'the Ashfall Compact' (capital A/C)." / "British spelling — colour, grey."
- **Content boundaries (adult)** — "All explicit content is between consenting adults." / "Violence stays off-page." *(pairs with the adult-content controls item)*
- **Prose guardrails** — "No em-dashes." / "Avoid 'suddenly' and 'very'." / "End scenes on a hook."

**Fit.** The teeth behind lore-grounding + B31: the author decides what's immovable (very much human-directs-the-story), and B31 enforces it strictly. Part of the consistency cluster (B31 guard / B32 canon lock / B33 character-state).

### B33. Character-state + lightweight timeline tracking — **effort: M+** — *APPROVED, sequenced AFTER B31/B32 (2026-07-07)*

**The gap.** `CharacterState` is a model (`knowledge_base.py`) that **nothing populates** — no agent maintains it. There is no timeline at all. So the system has no memory of what each character *knows / feels / where they are* at a given chapter, and no ordered sense of *when* events happen.

**What it does.**
- **Character state per chapter** — a lightweight snapshot maintained as chapters are approved: emotional state, key things they now *know* (revelations learned), location, physical condition.
- **Lightweight timeline** — an ordered list of key events tied to chapters ("Ch. 3: Maren learns Tya betrayed her").

**Why it matters.** It powers the **"knows something too early"** continuity check (B31) — the highest-value catch for mystery/thriller and impossible without who-knows-what-when. It gives generation **time-aware** context (the chapter writer already consumes `CharacterState` where present). It feeds pacing/structure analysis later.

**How.** After a chapter is approved, a small structured pass extracts state deltas + timeline events from the prose and stores them (cheap; reuses the extraction machinery + `bounded_map`). Surfaced read-only per character/chapter; editable.

**Sequencing (locked).** Build **after** B31 (guard) and B32 (canon lock) — those deliver most consistency value without it; B33 unlocks the deeper "knows too early" check and time-aware context when ready. Completes the consistency cluster (B31 / B32 / B33).

### B34. Human-directed revision loop — rewrite existing chapters with control — **effort: M** — *APPROVED, sequenced AFTER the step-by-step generation epic (2026-07-07)*

**The gap.** The step-by-step generation epic covers the **first draft** only. There is no equivalent for **rewriting** an existing chapter — `editor` / `style_editor` run automatically (or not at all), so the author can't drive a revision the way they can drive generation.

**What it does.** Point the same **approve / regenerate / guidance** controls at an existing chapter:
- Pick a chapter → give revision notes ("tighten the middle", "more tension in the confrontation", "she wouldn't say that") → **regenerate with that guidance**, or **hand-edit** directly.
- Scope: whole chapter, a scene, or a selected passage.
- Keep or discard; each attempt is **versioned** for rollback.

**Fit.** Revision is most of real writing; this applies the human-directed philosophy to the back half. Reuses the step-by-step control UX (approve/regenerate/guidance/reset) + the Versions machinery. A revision respects **canon (B32)** and can trigger a **continuity re-check (B31)** afterward.

**Sequencing (locked).** Build **after** the step-by-step generation epic — it shares that epic's UX and plumbing; the new part is passage/scene-scoped regeneration with notes + a diff (pairs with the diff-on-regenerate item).

### B35. Diff on regenerate — **effort: S** — *APPROVED as a cross-cutting requirement (2026-07-07)*

**The gap.** Regenerating anything (a stage, a chapter, a passage) silently *replaces* the old output — the author can't see what changed to judge whether the regen is better.

**What it does.** On any regenerate, show a **before/after diff** and offer **keep new / keep old / merge**. Prose → readable word-level diff; structured stages (outline, characters) → field-level diff. Could also show old-vs-suggested for "Apply suggested title".

**Not standalone — baked in.** This is a **cross-cutting requirement** of the step-by-step generation review panel and the revision loop (B34), not a separate tool. The Versions machinery already snapshots, so the data exists. A self-contained JS diff (inlined, per the offline/local constraint).

**Fit.** Makes the human-directed loop trustworthy: "regenerate" stops being a scary silent overwrite and becomes an informed choice — same theme as suggest-don't-overwrite and reset.

### B36. Advanced content-intensity controls (gated) — **effort: S/M** — *APPROVED (2026-07-07)*

**Purpose.** An optional per-scene/chapter/project control that lets the author steer the **tone, register, and intensity** of generated prose across a 1–5 scale (from mildest to most intense). Purely a generation steer — it adjusts the prompt only; it performs **no filtering of model output**. Scene-intent tags (e.g. "confrontation", "aftermath") and optional secondary tone dials ride the same mechanism, leaning on the existing `Scene.scene_type`.

**Gated & discreet (required part of the design).**
- **Off by default and not shown in the main UI.** Enabled only through an **Advanced settings** area (hard to find — not on the dashboard), which requires: (a) an explicit opt-in, (b) an **age affirmation (18+)**, and (c) acknowledgment of the usage disclaimer below.
- Until unlocked, the control and its detailed level definitions are **hidden** — nothing in the default UI indicates the capability, so it isn't obvious to a casual or underage viewer.
- **Neutral identifiers everywhere:** code/config/planning use generic names (e.g. `content_intensity`, levels 1–5). The prompt text that actually defines each level's register lives in a **gated, unlocked-only template** loaded at runtime — not inline in obvious source, and not enumerated in this public planning doc.
- Sensible neutral defaults so the app behaves identically when the feature is disabled.

**Usage disclaimer (shown at enable, must be acknowledged).** The software does not and cannot control the output of local/third-party LLMs, nor how the user uses them. The user is **solely responsible** for ensuring any generated content complies with the laws, ratings, and requirements of **their own jurisdiction**, and must be of legal age (18+). **No responsibility or liability is assumed or implied** for improper use or for content that violates the user's local laws.

**Storage / wiring.** The intensity level stores on Scene/Chapter (+ a project default) and injects register/tone guidance into the generation prompt only when the feature is enabled. Per-scene granularity rides with the chapter/scene-granularity slice; a per-project default can ship earlier. The gating + age affirmation + disclaimer + neutral naming are built together with the control, not bolted on later. Pairs with the B32 content-boundary rules.

### B37. Publish-ready export — DOCX → EPUB → PDF — **effort: M** — *APPROVED, delayed (2026-07-07)*

**The gap.** Export today is only `.txt` (plain prose) + a re-importable JSON bundle — no format you can hand to a reader or an editor. The pipeline stops just short of "a finished book."

**What it does.** Assemble the manuscript (chapters + title/author front matter + a table of contents + basic styling) into real documents, added as format options on the existing export UI. Pure **offline/local** assembly (no cloud conversion), per the local constraint.

**Order (locked).** **DOCX first** (for beta readers / editors who use Word), **then EPUB** (the real ebook format — sections, TOC, front matter), **then PDF later** (heavier; explicitly delayed).

**Notes.** Independent of everything else — no sequencing constraints beyond the internal DOCX→EPUB→PDF order; can slot in whenever. DOCX via a library or minimal OOXML; EPUB is a zip of XHTML + manifest (doable without heavy deps). A satisfying "get a real book out" item to interleave with the heavier work. Marked **delayed** — build after the higher-priority consistency/generation work.

### Story-structure / pacing analysis — 🧊 **PARKED (2026-07-07)**

Considered in the plan review; parked for now. A "zoom out on the whole book" view — act/structure balance, chapter word-count/pacing curve, tension/beat mapping (from `emotional_beat`/`scene_type`/arcs), arc/thread coverage. Weakest fit of the reviewed set: it's analysis not creation, overlaps the Stats page (readability), the continuity guard (B31), and the gap-finder, and its richest parts depend on B33 (timeline). If revived, the cheap wins (word-count curve + act ratios, zero-LLM) could be a small addition to the existing Stats page rather than a whole feature.

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

**Done (content pass — 2026-07-01):** Pages enabled (site live at
`https://mthous72.github.io/libriscribe/`). Rewrote intro / getting-started / usage for the web
app; added feature pages (providers & models incl. local LLM, lorebook + smart import incl.
SillyTavern/KoboldAI + references + OCR, brainstorm + Focus/sessions/Smart Apply/preview,
semantic search, versioning/export, stats + preview). Folded the **Writingway attribution** into
the docs intro **and** the README (deferred trigger fired — semantic/references/OCR/sessions
shipped). Disabled the default template blog (`blog: false`, removed sample posts) and restored
`onBrokenLinks: 'throw'`; docs build passes clean.

**Remaining:**
1. Ongoing: add/refresh a page whenever a new user-facing feature ships. The `agents/*` pages
   still describe the pipeline agents (roughly accurate) — light touch-up someday.
2. **Internal docs hygiene:** PLANNING.md is large (spec + backlog + history); when it gets
   unwieldy, split shipped specs into a `PLANNING-history.md` / CHANGELOG and keep this file to
   the live backlog.

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

---

## Epic B39: First-draft prose quality — de-scaffold, sanitize, non-overlapping scene beats — ✅ **BUILT (2026-07-08)**

> Slices A–C + automated D built same day (approved verbally). New `utils/prose_sanitizer.py`
> (+ `tests/test_prose_quality.py`, 20 tests, artifacts from the Helix draft as fixtures).
> Verified end-to-end against the real `test_novel-2` project: story export now has 1 chapter
> header, 0 scene labels, 0 mojibake, 0 double-hyphens. **Slice-D bake-off run 2026-07-09:**
> fresh generation confirmed clean (structure, encoding, echoes all fixed; disk/export bytes
> verified). Story .txt download now carries a UTF-8 BOM so Latin-1-defaulting editors stop
> rendering em dashes as "â" (the bake-off file *looked* garbled only in the viewer). Residuals
> observed → B40 below (phrase-tic repetition) + note that Slice C only bites when scenes are
> re-outlined, not on chapter rewrite against an old outline.

### B40. Deterministic repetition guard — scene-opening & phrase-tic ban list — ✅ **BUILT (2026-07-09)**

> Built as raised, plus per-user direction ("context to spare"): a **rolling all-scenes recap**
> — every scene of every previous chapter AND every scene written so far in the current one
> gets a compact entry (planned beat + actual opening + actual ending) in each scene prompt.
> New `utils/repetition_guard.py` (n-gram detector, name-aware so characters/places are never
> banned; ban-list block for generation, overuse-report block for the editor pass) +
> `scene_recap_block` in prose_steering. Scene prompt stack is now register > canon > all-scenes
> recap > verbatim continuity tail > ban list > brief, assembled in ONE shared
> `_build_scene_prompt`. **Also fixed:** the streaming write path (the default for the web UI)
> had NEVER carried the continuity/canon/register blocks — d27f8e2's continuity fix only
> applied to the non-streaming path; both paths now share the same stack. Real-project check:
> chapter-2 scene prompt ≈ 4k tokens with full recap. 410 tests pass
> (`tests/test_repetition_guard.py`).
>
> **Follow-up fix (2026-07-09):** "live stream preview was incomprehensible garbage" —
> root cause in `useWebSocket.ts`: the cleanup-triggered `onclose` scheduled a reconnect
> anyway, so every unmount / server restart / navigation stacked additional live sockets,
> and EACH appended every `stream_chunk` to the shared buffer (interleaved duplicate text;
> the saved chapter was always clean — server side was fine). Fixed: reconnect only for the
> active socket while mounted, stale sockets' events dropped, timer cleared, previous socket
> closed before opening a new one. Also: preview buffer now clears when a chapter run starts
> and labels scene boundaries ("────── Chapter 1 — Scene 2 ──────"). Frontend rebuilt.
>
> **v2 (2026-07-09, after bake-off round 2 — openings fixed, but word-level repetition and
> beat rehash remained):**
> 1. **Staggered-fragment merge** — one long repeated phrase used to surface as 3 overlapping
>    n-gram fragments; now chain-merged into the full phrase.
> 2. **Word-level bans** — single content words repeated conspicuously ("skin" ×19) are now
>    detected (name/stopword-aware, density threshold) and listed as "use at most once".
> 3. **Enforcement, not just instruction** — after each scene is generated, a deterministic
>    `find_violations` check (banned-phrase reuse, opening that mirrors an earlier scene)
>    triggers ONE regenerate-with-named-violations retry; the retry is kept only if
>    measurably fresher. Small models ignore advisory rules; this closes the loop.
> 4. **Progression contract** — scene prompts + recap now state: the scene must end in a
>    different story state than it began; anything already depicted must not be re-depicted —
>    continue from its aftermath ("every new scene progresses the story, not rehashes").
> Note: beat overlap ultimately originates in the outline (old S4/S5 were the same planned
> beat); a fresh outline generation gets Slice-C validation — chapter rewrites against an old
> outline can only soften it via #4.

### Reasoning-model support (LLM client) — ✅ **BUILT (2026-07-09)**
User switched to `qwen3.6-35b-a3b-uncensored-genesis-hermes` (Hermes-style reasoner) and every
stage failed with `empty_response`: the model spends its tokens in a private think channel
FIRST (measured ~2.5k thinking tokens for a two-sentence ask), so budgets sized for the answer
came back with `content=""`, `finish_reason=length`, all tokens counted as `reasoning_tokens`.
Built into `llm_client` (openai/openrouter/local paths):
1. **Escalating budget retry** — on `length` + reasoning tokens observed, re-call with
   +6144 then +16384 headroom (ordinary truncation without reasoning is NOT retried — scene
   caps stay intentional).
2. **Learned per-model allowance** — worst observed thinking cost (+1024 margin) is added
   preemptively to every later call for that model, including STREAMING (which can't retry).
3. **Think-tag hygiene** — `<think>/<reasoning>` blocks stripped from non-streaming responses;
   a stateful chunk-boundary-safe filter strips them from streams; `sanitize_prose` strips as
   belt-and-braces; chapter writer falls back to the non-streaming adaptive path when a
   streamed scene yields zero prose.
Live-verified against LM Studio: first call escalates and recovers; second call passes on the
learned allowance with no wasted attempt. `tests/test_reasoning_models.py` (14 tests).
**Operator note:** with a thinking model, 16k context is tight (≈7k prompt + 2.5k think + 5k
prose); prefer 24–32k if VRAM allows.

### B43. Import auto-repair — fix damaged JSON on import, report every fix — ✅ **BUILT (2026-07-09, user-directed)**
Trigger: a hand-merged bundle failed import with "Extra data" — two orphan duplicate chapter
blocks (merge debris dangling after their object closed, each dragging an extra `}`) plus a
missing comma. New `utils/json_repair.py`: strict parse first; on failure applies targeted
repairs — BOM strip, orphan-block removal (string-aware brace counting; orphan = key line
directly after `}`/`},` at deeper indent), missing-comma insertion, trailing-comma removal
(incl. Python 3.13+ "Illegal trailing comma" message), mojibake repair on parsed string
values — and returns a human-readable repair list. Unrepairable input re-raises the original
error. Both import doors (`/projects/import`, `/lore/parse`) accept a new `raw` field; the
frontend falls back to raw upload when client-side parse fails and shows "auto-repaired:
[list]". Verified end-to-end against the real broken file (3 repairs, imports clean).
`tests/test_json_repair.py` (11 tests). 447 total pass.

### B45. Story Workbench — granular, brainstorm-first UI restructure ✅ **BUILT — ALL 6 SLICES (2026-07-10, user-directed)**
User direction: "maximum control and brainstorming ability… work through every single object
within the JSON… one item at a time, in order, with the ability to go back and make updates
without changing the future content… Too much 'Big' automation… small bites of the whale."
Full plan: `~/.claude/plans/i-want-to-rethink-splendid-eich.md`.

**Binding decisions:** (1) a persistent three-pane workbench (story tree | item editor | docked
brainstorm pane) REPLACES the page-per-concern UI as THE project view — the brainstorm drawer
becomes a real docked pane; (2) ALL character work lives in lore (voice-profile generation
becomes a per-character lore action; the `characters` pipeline stage is removed; worldbuilding
same treatment, per-field); (3) milestone completion becomes AI-verified / HUMAN-approved —
AI writes only a `proposal` (verdict + evidence quote + reasoning), the user owns `status` and
can flip any flag anytime; the fake chapter-number auto-complete
(`ProjectManagerAgent._update_arc_milestones`) is deleted; (4) editing an earlier item never
cascades — advisory downstream-impact hints only.

**Slices (each independently shippable, verified against test_novel-2):**
1. ✅ **BUILT (2026-07-10)** Workbench shell at `/projects/:name/workbench` — `services/scene_prose.py`
   splitter, `GET …/scene-prose[/{s}]`, `GET …/workbench-tree` aggregate, `PUT …/chapters/{n}/meta`
   (chapter title/summary upsert — didn't exist anywhere); StoryTree (derived status dots) +
   ItemEditorHost + Prev/Next story walk + URL-addressable selection (`?sel=scene:3.2`);
   editors: Concept (w/ suggestion apply/dismiss), Outline (develop-remaining), Chapter (meta +
   prose + revise-diff + write-chapter), Scene (fields + prose view), World, generic lore-entity
   (FieldEditor stack EXTRACTED to `components/lore/fields.tsx` and re-imported by LorebookPage —
   no fork), Milestone (read-only until Slice 4); GenerationStrip. `tests/test_scene_prose.py`
   (10) → 461 pass; responsive suite grew to 56 (workbench at all phone widths).
2. ✅ **BUILT (2026-07-10)** Docked brainstorm pane — ALL drawer logic extracted to
   `components/BrainstormPanel.tsx` (variant drawer|docked; drawer is now a thin wrapper);
   chat focus extended to `concept | chapter ("3") | scene ("3.2")` with intent lenses, prose
   excerpts (head/tail, scene-scoped), scene-character briefs in surrounding lore; focus
   FOLLOWS tree selection (lock toggle); "Apply to this item" writes a reply into a chosen
   field of the focused scene/chapter/concept (spine-focused parse falls back to generic
   Apply-to-lore). `tests/test_chat_focus_spine.py` (5).
3. ✅ **BUILT (2026-07-10)** Small bites — `scene_prose.splice_scene` (byte-preserving,
   refuses unstructured) + `PUT …/scene-prose/{s}` (writes to the revised-preferred file);
   `services/scene_writer.py` + `POST …/scenes/{s}/write` — ONE scene with the full steering
   stack (canon/recap/continuity/guard + freshness enforcement + optional author guidance),
   diff→keep, never auto-saves; `POST …/chapters/{n}/develop-scenes`; per-character
   `POST …/voice-profile` (unsaved proposal); `POST …/worldbuilding/generate-field` (one
   grounded field per call). Scene prose editable inline. `tests/test_scene_writer.py` (12).
4. ✅ **BUILT (2026-07-10)** Real milestones — `MilestoneProposal` (additive default ⇒ zero
   migration), index-addressed milestone CRUD registered BEFORE the greedy `{arc_name:path}`
   routes, `POST /milestones/verify {chapter}` (utility model, head+tail prose, strict
   delivered-not-foreshadowed rubric), evidence-substring trust guard downgrades fabricated
   quotes to 'uncertain', accept/reject endpoints (accepting a not-delivered verdict RE-OPENS
   a faked flag), full MilestoneEditor (status flips freely — typical of all flags), tree
   'review' badges, ChapterEditor "Check milestones (AI)". THE FAKE numeric auto-complete
   (`ProjectManagerAgent._update_arc_milestones`) is DELETED. `tests/test_milestone_verifier.py` (12).
5. ✅ **BUILT (2026-07-10)** Impact hints — `services/impact.py` word-boundary scan (prose
   mentions + outline scene fields), `GET /{name}/impact/{entity}`, ImpactHint strip in lore
   editors: "Referenced in … — editing here never regenerates any of them." `tests/test_impact.py` (3).
6. ✅ **BUILT (2026-07-10)** Promotion — `/projects/:name` IS the workbench (header links:
   Wizard · Lore tools · Automation); old dashboard lives on at `/projects/:name/automation`
   ("Automation & settings": step/auto run, write-chapter, reset, exports, versions, LLM
   config + new "Batch tools…" cast/world); `STAGE_ORDER = concept→outline→chapters→formatting`,
   `next_step` skips the demoted stages, `start_from_stage=characters|worldbuilding` → 400
   pointing at `POST /{name}/tools/{stage}` (job-based `run_single_stage`, streaming+cancel);
   redirects: `/chapters/:n → ?sel=chapter:N`, `/outline → ?sel=outline`, `/workbench → /`;
   OutlinePage + ChapterEditorPage DELETED (rewrite-unlocked + locks absorbed into the
   workbench OutlineEditor); LorebookPage KEPT as "Lore tools" (deliberate deviation from the
   original delete plan — its Sandbox/Gaps/References/Graph/Import utilities have no workbench
   home yet); drawer mounts only on lorebook/wizard/automation. `tests/test_pipeline_demotion.py` (3).

**Verification (2026-07-10): 496 backend tests pass** (451 baseline + 45 new across
scene_prose/scene_writer/chat-focus/milestones/impact/demotion; 1 workflow_state assertion
updated for the demoted pipeline; KB template regenerated for the proposal field). Frontend
builds clean; **56 Playwright responsive checks pass** (workbench + automation at all phone
widths; legacy chapter-URL redirect exercised by the modal test). Live LLM actions (scene
write, voice profile, world field, milestone verify) await the user's LM Studio session.

### B44. "Develop remaining chapters" — intent-shaped outline continuation ✅ **BUILT (2026-07-09, user-directed)**
User feedback: the lock-then-"Regen Unlocked" flow was a Norman door — the natural task
("continue building the outline") required understanding an inverted, overwrite-by-default
model with a jargon button. Fixes:
1. **New primary action** `POST /{name}/develop-outline` + "Develop remaining" button:
   ADDITIVE by design — placeholder chapters get summary+scenes, real-summary-but-no-scenes
   chapters get scenes only, developed chapters are structurally untouched (they're passed as
   locked context). `OutlinerAgent.classify_development` buckets chapters (placeholder
   heuristics: blank / "to be developed" / "placeholder" title).
2. **Safe by default:** chapters with scenes now start LOCKED when the Outline page loads;
   rewriting developed work is opt-in.
3. **Honest destructive action:** "Regen Unlocked" renamed "Rewrite unlocked…", confirm
   dialog names exactly which chapters are rewritten and which are kept.
`tests/test_partial_outline.py` grew to 4 tests. 451 total pass. Frontend rebuilt.

### Fix — partial outline regen ("Regen Unlocked") now lore-grounded + milestone-aware ✅ (2026-07-09)
The lock-chapters + Regen-Unlocked flow (Outline page → `execute_partial`) already supports
"continue building scenes from where the outline is, without overwriting" — but its prompt
was bare (Phase-0 grounding never reached it) and ignored arc milestones. Now: the lore/canon
grounding block is prepended, and a **milestone roadmap** lists the author's planned beats per
regenerated chapter as binding requirements (completed milestones and other chapters'
milestones excluded). Token budget 3000→6000 for many-chapter regens. Regenerated chapters
still get Slice-C scene validation via the shared scene outliner.
`tests/test_partial_outline.py` (3 tests). 450 total pass.

### B42. Lore-safe character & worldbuilding generation — ✅ **BUILT (2026-07-09, user-directed)**
User directive: generation must NEVER overwrite lore; changes to existing entries are
suggestions requiring explicit approval. Previously: character stage overwrote same-name
lorebook characters field-by-field; worldbuilding stage replaced the ENTIRE worldbuilding
object (Phase 0 protected only concept/outline).
- **Characters:** prompt now carries the lore digest + an existing-characters directive
  ("build around them, don't recreate"). Name collisions no longer touch the KB — the
  generated profile lands in the **B27 sandbox** as a pending `update` candidate (voice
  profile of the existing character also untouched). New names still add directly.
- **Worldbuilding:** prompt lore-grounded; generated values fill EMPTY fields directly
  (nothing to protect), while fields the author already wrote become ONE pending sandbox
  candidate listing the conflicting fields. Wholesale replacement removed.
- **Sandbox:** new `worldbuilding` category (apply merges accepted field dicts via
  `merge_apply`'s existing worldbuilding path); Lorebook→Sandbox UI shows the new category
  and labels the new seed kinds. Frontend rebuilt.
- `tests/test_lore_safe_generation.py` (6 tests: no-overwrite, staging, accept-applies,
  blank-worldbuilding fast path). 436 total pass.
Bake-off residual: with prose-level continuity rules in place, a 12B writing model still opens
3 of 5 scenes with near-identical establishing shots ("smell of ozone and stale grease…",
"single flickering lamp") and recycles tics within one chapter ("as if burned" ×3, "heart
hammering against his ribs" ×4). Instruction-only steering ("don't reuse imagery") is too weak
for small local models. Idea: **deterministic** guard — after each scene, n-gram/phrase-scan
the prose so far, extract the distinctive repeated phrases and each scene's opening image, and
inject them into the next scene's prompt as an explicit named BAN LIST ("you may not use:
…"); optionally also a post-chapter repetition report (Gaps-style). Small models follow named
bans far better than abstract style rules. Effort: S/M. Depends on: nothing (extends
`continuity_block`).

**Trigger:** real chapter-1 output ("The Helix Chronicles", `test_novel-2.txt`, local Gemma
writing model). Diagnosis mapped every defect in that export to a specific code path. Note:
the draft **predates** today's continuity work (`d27f8e2` scene continuity + `c44a8d3` context
budgets) — the worst symptom (every scene re-opening with the same copper-air/ozone-workshop
establishing shot and recycled imagery) should already be substantially fixed; Slice D verifies.

**Defects found → root causes:**

| # | Symptom in the export | Root cause |
|---|----------------------|------------|
| 1 | `Scene 1: Maren navigates the claustroph...` headers, truncated mid-word, in the reader's text | `chapter_writer.py` builds scene titles as `summary[:30] + "..."` and **instructs the model to begin with that title**; export keeps heading text |
| 2 | Full scene summary echoed as the scene's first paragraph (title line then "Scene 1: Maren navigates the claustrophobic, neon-drenched slums…") | model told to open with the title; prompt shows the summary with no "don't restate it" rule |
| 3 | Chapter heading printed twice at the top | `export_story_text` adds a `Chapter n: title` header **and** `_strip_markdown` keeps the text of the chapter's `## Chapter n:` heading (only removes `#` marks) |
| 4 | Scenes 3, 4, 5 are the same story beat (diagnostic-touch-escalates), scene 5 nearly re-runs scene 4 | scene outlines generated without seeing sibling scenes; no distinct-beat/progression requirement, no dedup validation |
| 5 | Scene 5's own summary is truncated ("Maren realizes that CEE is not...") | scene outlining `max_tokens: 2000` too small for 3–5 detailed scenes → tail scene cut mid-sentence; parser accepts truncated summaries silently |
| 6 | Mojibake (`scrapâ€"the` rendered as `scrapâthe`), inconsistent `--` vs em dash, stray paragraph-leading hyphens (`-No scuffs`), `CEE'S` caps error | emitted by the local model itself (per-scene inconsistency; client decode paths are UTF-8-correct) — no sanitation pass exists |
| 7 | Editor pass would *re-add* the bold scene titles even if generation stopped emitting them | `agents/editor.py` prompt explicitly demands `**Scene X: Title**` on every scene |

### Slice A — scaffolding out of the prose (effort: S)
- `chapter_writer.py` (both `execute` and `execute_streaming`): **never ask the model to output
  the title**; drop the `IMPORTANT: Begin the scene with the title` line. Always prepend a
  delimiter in code. Delimiter becomes `### Scene N` (no summary fragment — the truncated-title
  hack dies). Frontend does not parse scene markers (checked), so format is free to change.
- `SCENE_PROMPT` / `ENRICHED_SCENE_PROMPT`: add — "Never restate, paraphrase, or reference the
  scene summary text itself; open in-scene with action, dialogue, or sensory detail."
- Belt-and-braces echo strip: after generation, if the scene's first non-empty line fuzzy-matches
  the scene summary (or starts with `Scene \d+:`), drop it.
- `agents/editor.py`: remove the two `**Scene X: Title**` enforcement instructions; preserve
  `### Scene N` delimiters instead.
- `export_story_text` (`project_service.py`): heading lines are **dropped entirely** (not
  de-marked); scene boundaries render as a blank line (or `* * *` — default blank line); the
  chapter header comes only from the KB title, killing the duplicate. Apply the same cleanup to
  the B37 DOCX exporter.

### Slice B — deterministic prose sanitizer (effort: S)
New `utils/prose_sanitizer.py`, applied to every generated **and revised** scene before it is
stored (chapter writer, B34 revision loop, editor/style passes):
- Mojibake repair: use `ftfy` if installed; else a built-in map of the common UTF-8-as-cp1252
  double-encodings (`â€"`→em dash, `â€™`→', `â€œ/â€`→"/", `Ã©`→é, lone `â`+space cases).
- Punctuation normalization: `--`/`—` unified (config: em dash default), collapse spaced hyphens
  used as dashes, strip stray paragraph-leading hyphens (`^-(?=[A-Z])`), straighten/curl quotes
  consistently, collapse >1 blank line.
- Word-level tics: fix `WORD'S`-style mid-word caps (`CEE'S` → `CEE's`).
- Pure functions + unit tests using the exact artifacts from this draft as fixtures.

### Slice C — scene-beat progression in outlining (effort: M)
- Scene outlining prompt: include the already-outlined sibling scenes and require each scene to
  advance a **distinct** beat (explicit "do not re-do a prior scene's beat; escalate or move").
- Parse-time validation: reject and regenerate (one retry) any scene whose summary ends
  truncated (mid-word / trailing `...`) or fuzzy-duplicates a sibling summary.
- Raise scene-outline `max_tokens` (2000 → 4000) so 5-scene chapters don't clip the tail.

### Slice D — verification bake-off (effort: S)
Regenerate this same chapter on the current build (post `d27f8e2`/`c44a8d3`) before and after
Slices A–C; keep `test_novel-2.txt` as the regression fixture. Success = no scaffold text, no
mojibake, no doubled headings, 0 near-duplicate scene beats, no truncated summaries.

**Order:** A + B first (cheap, directly visible to the reader), then C, D throughout.
**Dependencies:** none on other epics; touches B37 export and B34 revision paths only to reuse
the sanitizer/cleanup.
