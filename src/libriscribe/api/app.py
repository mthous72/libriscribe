"""FastAPI app factory."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from libriscribe import __version__
from libriscribe.api.routers import projects, generation, settings, lorebook, ws, system, chat
from libriscribe.utils.paths import get_frontend_dist


class SPAStaticFiles(StaticFiles):
    """Serve the built SPA, falling back to index.html for client-side routes.

    Client routes like /settings or /projects/x have no file on disk; a hard
    navigation or refresh would 404. Fall back to index.html so React Router can
    render them. API misses (path starting with "api") are left as real 404s.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise


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
    app.include_router(chat.router)
    app.include_router(projects.router)
    app.include_router(generation.router)
    app.include_router(settings.router)
    app.include_router(lorebook.router)
    app.include_router(ws.router)

    # Serve React build if it exists (with SPA fallback for client-side routes)
    frontend_dist = get_frontend_dist()
    if frontend_dist.exists():
        app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
