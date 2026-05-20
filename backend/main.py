"""Vedisa CRM - FastAPI Application Entry Point"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.logging_middleware import request_logging_middleware
from app.core.auth import get_current_user, hash_password, verify_password
from app.api.crm import router as crm_router
from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router
from app.api.health import router as health_router
from app.api.meta import router as meta_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events.

    Warmup: precalentamos pool DB y bcrypt para que el primer login no
    pague la latencia de inicializacion (que en NSSM cold-start puede
    rondar los 7-8s). Esto convierte el primer login en ~250ms estables.
    """
    app.state.started_at = datetime.now(timezone.utc)
    await create_db_and_tables()
    # Warmup bcrypt: la primera llamada inicializa el backend nativo.
    try:
        warm_hash = hash_password("__warmup__")
        verify_password("__warmup__", warm_hash)
    except Exception:
        # No bloqueamos el arranque si el warmup falla.
        pass
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
#
# Politica de auth: por contrato del proyecto el login es obligatorio en
# TODAS las rutas excepto /healthz, /auth/* y /meta/*. Aplicamos la
# dependencia de autenticacion a nivel de include_router para que
# cualquier handler nuevo nazca protegido sin depender de que el autor
# se acuerde de poner Depends(get_current_user) en la firma. La
# dependencia se cachea por request, asi que repetirla en handlers que
# ya la tenian no penaliza performance.
auth_required = [Depends(get_current_user)]

app.include_router(health_router, tags=["Health"])
app.include_router(meta_router, tags=["Meta"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(
    crm_router, prefix="/crm", tags=["CRM"], dependencies=auth_required,
)
app.include_router(
    ai_router, prefix="/ai", tags=["IA"], dependencies=auth_required,
)
app.include_router(
    notifications_router, tags=["notifications"], dependencies=auth_required,
)


@app.get("/health")
async def health_check():
    """Legacy health endpoint (compat). Use /healthz para diagnostico completo."""
    return {"status": "ok", "version": settings.app_version}
