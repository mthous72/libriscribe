"""FastAPI app factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from libriscribe import __version__
from libriscribe.api.routers import projects, generation, settings, lorebook, ws, system
from libriscribe.utils.paths import get_frontend_dist


def create_app() -> FastAPI:
    app = FastAPI(
        title="LibriScribe",
        description="AI-powered book generation platform",
        version=__version__,
    )

    # CORS for local development (Vite dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(system.router)
    app.include_router(projects.router)
    app.include_router(generation.router)
    app.include_router(settings.router)
    app.include_router(lorebook.router)
    app.include_router(ws.router)

    # Serve React build if it exists
    frontend_dist = get_frontend_dist()
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
