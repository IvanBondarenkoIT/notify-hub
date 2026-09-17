"""FastAPI application: health + events ingestion."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status

from notify_hub.config import Settings, get_settings
from notify_hub.db import init_db, session_scope
from notify_hub.models import EventAccepted, EventIn, HealthResponse
from notify_hub.outbox import accept_event

logger = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="DimKava Notify Hub", version="0.1.0")

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    def require_api_key(
        authorization: Optional[str] = Header(default=None),
        x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
    ) -> None:
        key: Optional[str] = x_api_key
        if not key and authorization:
            parts = authorization.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                key = parts[1].strip()
            else:
                key = authorization.strip()
        if not settings.is_valid_api_key(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse()

    @app.post(
        "/v1/events",
        response_model=EventAccepted,
        dependencies=[Depends(require_api_key)],
    )
    def post_event(body: EventIn) -> EventAccepted:
        with session_scope() as session:
            created, enqueued = accept_event(session, body, settings=settings)
            if created:
                return EventAccepted(
                    event_id=body.event_id,
                    status="accepted",
                    created=True,
                    outbox_enqueued=enqueued,
                )
            return EventAccepted(
                event_id=body.event_id,
                status="duplicate",
                created=False,
                outbox_enqueued=0,
            )

    return app
