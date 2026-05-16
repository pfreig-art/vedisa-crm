"""Vedisa CRM - FastAPI Application Entry Point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.api.crm import router as crm_router
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Vedisa CRM API",
    description="CRM Vedisa con drawer IA contextual y proveedores LLM intercambiables",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,

    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(crm_router, prefix="/crm", tags=["CRM"])
app.include_router(ai_router, prefix="/ai", tags=["IA"])
app.include_router(notifications_router, tags=["notifications"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}
