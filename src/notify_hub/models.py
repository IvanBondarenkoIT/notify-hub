"""Pydantic API models and domain helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EventTargets(BaseModel):
    chat_ids: List[int] = Field(default_factory=list)
    user_ids: List[int] = Field(default_factory=list)


class EscalateTo(BaseModel):
    chat_ids: List[int] = Field(default_factory=list)


class EventIn(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=256)
    type: str = Field(..., min_length=1, max_length=256)
    severity: Optional[str] = "info"
    source: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["public"])
    targets: EventTargets = Field(default_factory=EventTargets)
    require_ack: bool = False
    ack_timeout_minutes: Optional[int] = None
    escalate_to: EscalateTo = Field(default_factory=EscalateTo)
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("channels")
    @classmethod
    def normalize_channels(cls, value: List[str]) -> List[str]:
        allowed = {"public", "private", "personal"}
        if not value:
            return ["public"]
        normalized = []
        for ch in value:
            name = (ch or "").strip().lower()
            if name in allowed and name not in normalized:
                normalized.append(name)
        return normalized or ["public"]


class EventAccepted(BaseModel):
    event_id: str
    status: str
    created: bool
    outbox_enqueued: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "notify-hub"
