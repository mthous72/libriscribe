from __future__ import annotations

from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    type: str
    project: str
    timestamp: str
    payload: dict = Field(default_factory=dict)


class WSClientMessage(BaseModel):
    action: str
    proceed: bool | None = None
    apply_ai_style: bool | None = None
