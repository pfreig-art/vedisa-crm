"""Tests de regresion del hardening de auth (Sprint E3).

Cubre:
1. Endpoints que antes estaban sin Depends(get_current_user) y ahora
   exigen token por la dependencia global de include_router.
2. Login OK contra password normal.
3. Login con password >72 bytes no rompe (bcrypt 4.1+ truncado seguro).
4. Login con credenciales malas devuelve 401, no 500.
5. /healthz, /meta/schema y /auth/login siguen accesibles sin token.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.auth import _bcrypt_safe, hash_password, verify_password
from app.core.models import Usuario


# ---------------------------------------------------------------------------
# 1. 401 en endpoints que antes filtraban
# ---------------------------------------------------------------------------

ENDPOINTS_PROTEGIDOS = [
    ("GET", "/crm/dashboard"),
    ("GET", "/crm/dashboard/extended"),
    ("GET", "/crm/pipeline"),
    ("GET", "/crm/solicitudes"),
    ("GET", "/crm/solicitudes/export"),
    ("GET", "/crm/usuarios"),
    ("GET", "/crm/actuaciones"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ENDPOINTS_PROTEGIDOS)
async def test_endpoint_sin_token_devuelve_401(client, method, path):
    r = await client.request(method, path)
    assert r.status_code == 401, (
        f"{method} {path} deberia exigir auth pero devolvio {r.status_code}"
    )


@pytest.mark.asyncio
async def test_ai_brief_sin_token_devuelve_401(client):
    r = await client.post(
        "/ai/brief",
        json={"mode": "dashboard", "context": {}},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_protegido_con_token_responde_200(client, auth_headers):
    r = await client.get("/crm/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# 2. Endpoints publicos siguen abiertos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthz_publico(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_meta_schema_publico(client):
    r = await client.get("/meta/schema")
    assert r.status_code == 200
    body = r.json()
    assert "entities" in body and len(body["entities"]) > 0


@pytest.mark.asyncio
async def test_meta_glossary_publico(client):
    r = await client.get("/meta/glossary")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 3. Login funciona y no rompe con passwords largas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_ok_con_password_normal(client, admin_user):
    r = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "Admin12345!"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["email"] == admin_user.email


@pytest.mark.asyncio
async def test_login_credenciales_malas_devuelve_401_no_500(client, admin_user):
    r = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "wrong-password"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_password_mayor_de_72_bytes_no_rompe(client, session):
    """bcrypt >= 4.1 lanza ValueError si la password supera 72 bytes.

    El truncado defensivo en `_bcrypt_safe` debe permitir que el flujo
    de login sea estable: con password muy larga (cualquier valor)
    debe devolver 401, NO 500.
    """
    # Creamos un usuario cuyo hash se calcula a partir de los primeros
    # 72 bytes de una password larga, simulando un caso real donde el
    # admin puso una passphrase larga al registrarse.
    long_pw = "X" * 200  # 200 bytes ascii
    u = Usuario(
        id=str(uuid.uuid4()),
        email="long@vedisa.local",
        nombre="Long PW",
        hashed_password=hash_password(long_pw),  # _bcrypt_safe ya trunca
        rol="comercial",
        activo=True,
    )
    session.add(u)
    await session.commit()

    # Login con la misma password larga: debe funcionar.
    ok = await client.post(
        "/auth/login",
        data={"username": "long@vedisa.local", "password": long_pw},
    )
    assert ok.status_code == 200, ok.text

    # Login con otra password aun mas larga y distinta: 401, sin tracebacks.
    bad = await client.post(
        "/auth/login",
        data={"username": "long@vedisa.local", "password": "Y" * 500},
    )
    assert bad.status_code == 401


# ---------------------------------------------------------------------------
# 4. Helpers de bcrypt unitarios
# ---------------------------------------------------------------------------


def test_bcrypt_safe_no_modifica_passwords_cortas():
    assert _bcrypt_safe("admin123") == "admin123"


def test_bcrypt_safe_trunca_a_72_bytes():
    raw = "a" * 100
    out = _bcrypt_safe(raw)
    assert len(out.encode("utf-8")) <= 72


def test_bcrypt_safe_acepta_none():
    assert _bcrypt_safe(None) == ""


def test_verify_password_no_lanza_con_hash_corrupto():
    # Si pasamos un hash invalido, debe devolver False y no levantar.
    assert verify_password("anything", "not-a-bcrypt-hash") is False
    assert verify_password("anything", "") is False
    assert verify_password("", "$2b$12$abcdefghijklmno") is False


def test_hash_password_redondea_para_passwords_largas():
    # No debe lanzar ValueError con passwords > 72 bytes.
    h = hash_password("x" * 500)
    assert h.startswith("$2")  # bcrypt prefix
