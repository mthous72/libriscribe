# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Installation
```bash
pip install -e .
```

### Run the application (web server)
```bash
libriscribe
# Opens browser at http://127.0.0.1:8000
```

### Run frontend dev server (for development)
```bash
cd frontend && npm install && npm run dev
# Vite dev server at http://localhost:5173, proxies /api and /ws to :8000
```

### Build frontend for production
```bash
cd frontend && npm run build
# Output in frontend/dist/, served by FastAPI StaticFiles
```

### Run all tests
```bash
PYTHONPATH=src python -m pytest tests/
```

### Run a single test file
```bash
PYTHONPATH=src python -m pytest tests/test_retrieval_pipeline.py
```

### Run a single test case
```bash
PYTHONPATH=src python -m pytest tests/test_retrieval_pipeline.py::RetrievalPipelineTests::test_keyword_and_fallback_search
```

### Verify imports
```bash
PYTHONPATH=src python -c 'import libriscribe.server'
```

## Architecture

### Package layout
- `src/libriscribe/` — main package (installed via `pip install -e .` from `setup.py`)
- `src/libriscribe/api/` — FastAPI routers, schemas, and dependency injection
- `src/libriscribe/services/` — generation pipeline orchestration, job management, streaming bridge
- `frontend/` — React + Vite + TypeScript + Tailwind CSS frontend
- `prompts/templates/` — external YAML prompt templates for each agent (editable without touching Python code)
- `examples/` — starter expert config files (JSON and YAML)
- `tests/` — standard `unittest`-based tests; all require `PYTHONPATH=src`
- `projects/` — runtime output directory where generated book projects are written

### Entry point
`libriscribe/server.py` launches uvicorn serving the FastAPI app and auto-opens the browser. The app factory is in `api/app.py`.

### Web architecture
```
Browser (React + Vite)
    <-> REST (axios)      <-> WebSocket
FastAPI (uvicorn, localhost:8000)
    <-> asyncio.to_thread()
Existing agents (sync Python)
    <-> EventCallback
LLMClient (sync, with streaming Iterator[str])
```

### API structure
- `api/routers/projects.py` — project CRUD, chapters, files, download, cost
- `api/routers/generation.py` — start/cancel/resume generation pipeline
- `api/routers/settings.py` — API key config (reads/writes .env)
- `api/routers/lorebook.py` — characters, locations, lore entries, arcs, worldbuilding, xref, search, scenes
- `api/routers/ws.py` — WebSocket `/ws/{project_name}` for real-time events

### Event callback pattern
All agents use `EventCallback = Callable[[str, Any], None]` from `agent_base.py`. Agents call `self.emit(event_type, payload)` instead of printing. The FastAPI service layer injects a thread-safe callback that pushes to an `asyncio.Queue` via `loop.call_soon_threadsafe()`.

### Agent system
`ProjectManagerAgent` (`agents/project_manager.py`) is the orchestrator. It owns a shared `LLMClient` instance and instantiates all specialized agents, passing the client and event_callback to each. All agents inherit from `Agent` (`agents/agent_base.py`) and implement `execute()`.

Agent roster: `ConceptGeneratorAgent`, `OutlinerAgent`, `CharacterGeneratorAgent`, `WorldbuildingAgent`, `ChapterWriterAgent`, `EditorAgent`, `ContentReviewerAgent`, `ResearcherAgent`, `OptimizedFormattingAgent`, `StyleEditorAgent`, `PlagiarismCheckerAgent`, `FactCheckerAgent`.

### Generation pipeline
`services/generation_service.py` runs the pipeline via `asyncio.to_thread()`. Human review uses `threading.Event` to block the pipeline thread while the WebSocket receives the user's decision.

### LLM client & fallback routing (`utils/llm_client.py`)
`LLMClient` is the single unified interface for all providers: `openai`, `claude`, `google_ai_studio`, `deepseek`, `mistral`, `openrouter`. It supports a configurable fallback chain — on recoverable failures (timeout, 429, 5xx, empty response, invalid JSON after repair attempt) it walks the chain and retries on the next route.

Key methods:
- `generate_content()` — plain text generation
- `generate_content_with_json_repair()` — generates and auto-repairs malformed JSON
- `generate_content_streaming()` — returns `Iterator[str]` for real-time token streaming

### Settings (`settings.py`)
`Settings` is a `pydantic-settings` model loaded from `.env`. API keys and default model IDs for all providers are declared here. Copy `.env.example` to `.env` and populate keys before running.

### Knowledge base & project data (`knowledge_base.py`, `configuration.py`)
`ProjectKnowledgeBase` is the in-memory data model for a book project (title, genre, characters, chapters, worldbuilding, locations, lore_entries, story_arcs, etc.). It is serialized to `project_data.json` inside the project directory.

### Lorebook models
- `Location` — name, description, significance, associated_characters, first_appearance, tags
- `LoreEntry` — name, entry_type, description, significance, related_entities, first_appearance, tags
- `StoryArc` — name, description, arc_type, chapters_involved, characters_involved, status, resolution_notes

### Retrieval system (`retrieval/`)
Local keyword search and cross-reference indexing — no external vector DB required.

- `models.py` — `RetrievalDocument`, `RetrievalChunk`, `RetrievalConfig`, `SearchResult`, `CrossReferenceEntry`
- `document_builder.py` — converts KB fields, locations, lore entries, and prose chapters into `RetrievalDocument` objects
- `chunking.py` — splits documents into overlapping chunks respecting paragraph boundaries
- `keyword_index.py` — BM25 (rank-bm25) or pure-Python TF-IDF fallback
- `cross_reference.py` — maps entity co-occurrences across chapters
- `index_manager.py` — orchestrates rebuild and hash-based incremental refresh
- `search_service.py` — `SearchServiceImpl` (active), `NullSearchService` (no-op)

### Frontend structure
- `frontend/src/api/client.ts` — typed API client (axios)
- `frontend/src/hooks/useWebSocket.ts` — WS connection with auto-reconnect
- `frontend/src/store/generationSlice.ts` — Zustand store for generation state
- Pages: HomePage, NewProjectPage, ProjectDashboard, ChapterEditorPage, LorebookPage, OutlinePage, SettingsPage

### Cost tracking (`utils/cost_tracker.py`)
`CostTracker` logs every LLM call to `llm_usage.jsonl` with provider, model, token counts, and USD cost.
