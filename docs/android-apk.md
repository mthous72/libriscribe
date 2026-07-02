# Building a self-contained LibriScribe Android APK

This produces an installable `.apk` that bundles the **whole app** — the Python
FastAPI backend *and* the built React UI — running entirely on the phone. Only
the LLM calls go off-device (LM Studio over Tailscale, or OpenRouter). End-user
experience is what you'd expect: install the APK, tap the icon, use it. No
Termux, no manual `pip`, no separate steps.

> **Status:** the `android/` directory is a complete, reviewable **scaffold**
> plus the LibriScribe-side hooks needed to embed it. It has not been compiled
> here (an Android SDK/NDK is required, and the one native gate below must be
> resolved on your build machine). Treat the steps below as the recipe to turn
> the scaffold into a signed APK.

## Architecture

```
┌─────────────────────── Android device ───────────────────────┐
│  MainActivity (WebView)  ──http://127.0.0.1:8000──▶  uvicorn  │
│                                                       │       │
│  ServerService (foreground + wake lock)               │       │
│    starts Chaquopy CPython, runs serve_embedded()     ▼       │
│                                              FastAPI + agents  │
└───────────────────────────────────────────────────────┬──────┘
                                                          │ HTTPS
                              LM Studio (PC, over Tailscale) / OpenRouter
```

- **Embedded server:** `libriscribe.server.serve_embedded()` runs uvicorn on the
  pure-Python asyncio loop (no uvloop/httptools) bound to loopback.
- **Assets:** the built `frontend/dist` and `prompts/` are packaged into the APK
  and unpacked to app storage on first launch; `LIBRISCRIBE_BASE_DIR` /
  `LIBRISCRIBE_DATA_DIR` point path resolution at them (see
  `src/libriscribe/utils/paths.py`).
- **No native code except one wheel** — see below.

## What's included vs. dropped on mobile

All the heavy native deps are already lazily imported with graceful fallbacks,
so the app runs without them:

| Feature | Desktop dep | On the APK |
|---|---|---|
| Core: projects, generation, chapters, lore, export | pure-Python | ✅ included |
| LLM providers (LM Studio, OpenRouter, OpenAI, Anthropic) | `openai`, `anthropic` (pure) | ✅ included |
| Keyword retrieval | `rank-bm25` (pure) | ✅ included |
| Semantic retrieval | `numpy` | ⛔ dropped → falls back to keyword |
| OCR / scanned-doc reference import | `pymupdf`, `pytesseract`, Tesseract binary | ⛔ dropped |
| System tray | `pystray`, `Pillow` | ⛔ N/A on Android |
| Gemini | `google-genai` | ⛔ omitted (add back if needed) |

The lean dependency list lives in `android/app/build.gradle` (the `chaquopy` pip
block). LibriScribe's own source is put on the Python path via
`sourceSets.main.python.srcDir "../../src"`, so it is **not** pip-installed from
`setup.py` and never drags in the desktop-only extras.

## The one native gate: `pydantic-core`

FastAPI + settings use pydantic v2, whose `pydantic-core` is a compiled **Rust**
extension. It is the only mandatory non-pure-Python dependency. Before building,
confirm one of:

1. **Chaquopy ships it** for your `version` (3.11) and ABIs (`arm64-v8a`,
   `x86_64`). Check the Chaquopy package list / just let the `pip` block try — if
   it resolves, you're done.
2. **You supply a wheel.** Build `pydantic-core` for the Android targets with
   [maturin] + the NDK and drop the wheels where Chaquopy can find them
   (`pip { install "pydantic-core", { ... } }` / a local wheel dir), e.g.
   `maturin build --release --target aarch64-linux-android` (and
   `x86_64-linux-android`) with `CARGO_NDK`/`cargo-ndk` configured.

If neither is workable, the fallback is a (larger) refactor to pydantic v1,
which is pure-Python — avoid unless forced.

## Prerequisites

- Android Studio (Ladybug or newer) with **SDK 34** and the **NDK** installed.
- JDK 17.
- Node 20 (to build the web UI).
- Rust + `cargo-ndk` **only if** you must build the `pydantic-core` wheel.

## Build steps

```bash
# 1. Build the web UI (staged into the APK's assets by the stageAssets task)
cd frontend && npm ci && npm run build && cd ..

# 2. Build the APK
cd android
./gradlew assembleDebug        # or assembleRelease with a real signing config
# output: android/app/build/outputs/apk/…/app-*.apk
```

Open `android/` in Android Studio instead if you prefer — it will sync the
plugin versions in `build.gradle` against your installed tooling. First build is
slow (Chaquopy downloads CPython + wheels).

### Release signing

`app/build.gradle` currently points `release` at the debug signing config as a
placeholder. Create a keystore and a real `signingConfigs.release` before
distributing (`keytool -genkey -v -keystore libriscribe.jks ...`).

## Connecting to your LLM

- **LM Studio over Tailscale:** in the app → Settings, set provider **Local
  (OpenAI-compatible)** and base URL to `http://<pc>.<tailnet>.ts.net:1234/v1`
  (enable "Serve on Local Network" in LM Studio so it binds beyond localhost).
- **OpenRouter:** set the OpenRouter key in Settings.

Both use the pure-Python `openai` client — no native code, no extra permissions
beyond `INTERNET`.

## Runtime notes / gotchas

- **Long generations:** the foreground service + `PARTIAL_WAKE_LOCK` keep the
  server alive with the screen off. `MainActivity.onDestroy` currently stops the
  service ("close = stop"); remove that call if you want runs to continue after
  the UI is dismissed.
- **WebSocket streaming:** the UI already selects `ws://` for the loopback
  origin; `usesCleartextTraffic="true"` permits the localhost connection.
- **Storage:** projects and `.env` live under the app's private `filesDir`.
  Uninstalling removes them — wire an export/backup flow (the app already has
  project export) if that matters.
- **ABIs:** ship `arm64-v8a` for phones; keep `x86_64` only for the emulator.
  Every ABI needs a matching `pydantic-core` wheel.

## Files in this scaffold

```
android/
  settings.gradle, build.gradle, gradle.properties
  app/build.gradle                      # Android + Chaquopy config, lean pip list, asset staging
  app/src/main/AndroidManifest.xml      # permissions, launcher activity, foreground service
  app/src/main/java/com/libriscribe/app/
      MainActivity.kt                   # WebView; waits for /api/health then loads
      ServerService.kt                  # foreground service; unpacks assets; starts Python
  app/src/main/python/android_main.py   # sets env, calls serve_embedded()
  app/src/main/res/values/strings.xml
```

LibriScribe-side hooks (already in the repo):
- `libriscribe.server.serve_embedded(host, port)` — tray/browser-free entry point.
- `LIBRISCRIBE_BASE_DIR` / `LIBRISCRIBE_DATA_DIR` overrides in
  `libriscribe.utils.paths`.

[maturin]: https://www.maturin.rs/
