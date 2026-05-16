"""Vedisa CRM - FastAPI Application Entry Point"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.logging_middleware import request_logging_middleware
from app.api.crm import router as crm_router
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router
from app.api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    app.state.started_at = datetime.now(timezone.utc)
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Vedisa CRM API",
    description="CRM Vedisa con drawer IA contextual y proveedores LLM intercambiables",
    version=settings.app_version,
    lifespan=lifespan,
)

# Request logging estructurado (debe ir antes de CORS para medir latencia real).
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(crm_router, prefix="/crm", tags=["CRM"])
app.include_router(ai_router, prefix="/ai", tags=["IA"])
app.include_router(notifications_router, tags=["notifications"])


@app.get("/health")
async def health_check():
    """Legacy health endpoint (compat). Use /healthz para diagnostico completo."""
    return {"status": "ok", "version": settings.app_version}
