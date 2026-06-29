"""System endpoints: health/identity, UI state, and shutdown.

- GET  /api/health   — identity probe used for single-instance detection.
- GET  /api/ui-state — current dirty/active-generation flags.
- POST /api/ui-state — frontend reports its dirty/active-generation state.
- POST /api/shutdown — request a clean server shutdown (web-UI Quit path).
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from libriscribe import __version__, runtime

router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    app: str = "libriscribe"
    version: str = __version__


class UiState(BaseModel):
    dirty: bool = False
    active_generation: bool = False


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ui-state", response_model=UiState)
def read_ui_state() -> UiState:
    return UiState(**runtime.get_ui_state())


@router.post("/ui-state", response_model=UiState)
def write_ui_state(body: UiState) -> UiState:
    updated = runtime.set_ui_state(
        dirty=body.dirty, active_generation=body.active_generation
    )
    return UiState(**updated)


@router.post("/shutdown")
def shutdown() -> dict:
    runtime.request_shutdown()
    return {"status": "shutting_down"}
