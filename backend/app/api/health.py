"""Healthcheck endpoint para liveness/readiness desde IIS+ARR."""
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def healthz(request: Request):
    started_at: datetime | None = getattr(request.app.state, "started_at", None)
    if started_at is None:
        uptime_seconds = 0
    else:
        uptime_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())

    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": settings.app_version,
        "uptime_seconds": uptime_seconds,
        "db": db_status,
        "environment": settings.environment,
    }
