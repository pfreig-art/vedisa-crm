"""Fixtures pytest comunes para los tests del backend.

Todos los tests usan SQLite in-memory (asyncpg/Postgres no se toca).
La app se importa una sola vez por sesion y se le aplica un override de
`get_session` que devuelve sesiones contra el engine in-memory.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator

# IMPORTANTE: forzar SQLite in-memory ANTES de importar la app, porque
# database.py crea el engine global a partir de settings.DATABASE_URL al
# importar el modulo. El healthcheck usa ese engine directamente.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# Importamos modelos antes que la app para que SQLModel registre las tablas.
from app.core import models  # noqa: F401
from app.core.auth import hash_password, create_access_token
from app.core import database as core_database
from app.core.database import get_session
from app.core.models import Actuacion, Usuario
from main import app as fastapi_app


# ---------------------------------------------------------------------------
# Engine + session de test (SQLite in-memory)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def engine_test():
    """Engine async SQLite in-memory compartido entre conexiones del test.

    StaticPool + check_same_thread=False permite que todas las conexiones
    abiertas durante el test compartan la misma DB en memoria. Sin esto,
    cada AsyncSession abriria un :memory: distinto y los datos del fixture
    no serian visibles desde el cliente HTTP.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine_test) -> AsyncGenerator[AsyncSession, None]:
    """AsyncSession ligada al engine_test. Rollback al final."""
    SessionLocal = sessionmaker(
        bind=engine_test, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as s:
        try:
            yield s
        finally:
            await s.rollback()


@pytest_asyncio.fixture(scope="function")
async def app_test(engine_test):
    """FastAPI app con dependency override de get_session.

    Mantiene el mismo engine durante el test para que los datos creados via
    fixture sean visibles desde el cliente HTTP y viceversa.
    """
    SessionLocal = sessionmaker(
        bind=engine_test, class_=AsyncSession, expire_on_commit=False
    )

    async def _get_session_override() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = _get_session_override
    # Simulamos lo que hace el lifespan startup sin crear tablas (ya creadas).
    import datetime
    fastapi_app.state.started_at = datetime.datetime.now(datetime.timezone.utc)

    # Healthcheck usa core_database.engine directamente y health.py lo
    # importa por nombre; reapuntar ambos al engine de test.
    from app.api import health as health_module
    original_core_engine = core_database.engine
    original_health_engine = health_module.engine
    core_database.engine = engine_test
    health_module.engine = engine_test
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()
        core_database.engine = original_core_engine
        health_module.engine = original_health_engine


@pytest_asyncio.fixture(scope="function")
async def client(app_test) -> AsyncGenerator[AsyncClient, None]:
    """httpx.AsyncClient apuntando a la app via ASGITransport."""
    transport = ASGITransport(app=app_test)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Datos seed: admin y catalogo de actuaciones
# ---------------------------------------------------------------------------

ADMIN_PASSWORD = "Admin12345!"


@pytest_asyncio.fixture(scope="function")
async def admin_user(session: AsyncSession) -> Usuario:
    """Crea un usuario admin activo y lo devuelve."""
    u = Usuario(
        id=str(uuid.uuid4()),
        email="admin@vedisa.local",
        nombre="Admin Test",
        hashed_password=hash_password(ADMIN_PASSWORD),
        rol="admin",
        activo=True,
        iniciales="AT",
        color="#6366f1",
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture(scope="function")
async def comercial_user(session: AsyncSession) -> Usuario:
    """Crea un usuario comercial activo."""
    u = Usuario(
        id=str(uuid.uuid4()),
        email="comercial@vedisa.local",
        nombre="Comercial Test",
        hashed_password=hash_password(ADMIN_PASSWORD),
        rol="comercial",
        activo=True,
        iniciales="CT",
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture(scope="function")
async def inactive_user(session: AsyncSession) -> Usuario:
    """Crea un usuario inactivo (para test de 403 en login)."""
    u = Usuario(
        id=str(uuid.uuid4()),
        email="inactivo@vedisa.local",
        nombre="Inactivo",
        hashed_password=hash_password(ADMIN_PASSWORD),
        rol="comercial",
        activo=False,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


def _make_token(user: Usuario) -> str:
    return create_access_token({"sub": user.email, "rol": user.rol})


@pytest_asyncio.fixture(scope="function")
async def admin_token(admin_user: Usuario) -> str:
    return _make_token(admin_user)


@pytest_asyncio.fixture(scope="function")
async def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture(scope="function")
async def actuacion_sample(session: AsyncSession) -> Actuacion:
    """Crea una actuacion de catalogo (id=fachada)."""
    a = Actuacion(id="fachada", nombre="Fachada", orden=10, activo=True)
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Compat: pytest-asyncio en modo auto necesita event_loop scope coherente.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop para toda la sesion de tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
