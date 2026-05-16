"""Tests de los endpoints /auth/*: login y change-password."""
import pytest

from tests.conftest import ADMIN_PASSWORD


pytestmark = pytest.mark.asyncio


# --- LOGIN ----------------------------------------------------------------

async def test_login_ok(client, admin_user):
    r = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["email"] == admin_user.email
    assert body["rol"] == "admin"
    assert body["nombre"] == admin_user.nombre


async def test_login_password_incorrecta(client, admin_user):
    r = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "wrong-password"},
    )
    assert r.status_code == 401
    assert "incorrectos" in r.json()["detail"].lower()


async def test_login_usuario_inexistente(client, admin_user):
    r = await client.post(
        "/auth/login",
        data={"username": "noexiste@vedisa.local", "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 401


async def test_login_usuario_inactivo(client, inactive_user):
    r = await client.post(
        "/auth/login",
        data={"username": inactive_user.email, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 403
    assert "desactivado" in r.json()["detail"].lower()


# --- CHANGE-PASSWORD ------------------------------------------------------

async def test_change_password_ok(client, admin_user, auth_headers):
    r = await client.post(
        "/auth/change-password",
        json={
            "password_actual": ADMIN_PASSWORD,
            "password_nueva": "NewPassword456!",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    # Login con la antigua falla; con la nueva funciona.
    r_old = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": ADMIN_PASSWORD},
    )
    assert r_old.status_code == 401

    r_new = await client.post(
        "/auth/login",
        data={"username": admin_user.email, "password": "NewPassword456!"},
    )
    assert r_new.status_code == 200


async def test_change_password_actual_incorrecta(client, auth_headers):
    r = await client.post(
        "/auth/change-password",
        json={"password_actual": "WRONG", "password_nueva": "AlgoLargo123!"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "actual" in r.json()["detail"].lower()


async def test_change_password_nueva_muy_corta(client, auth_headers):
    r = await client.post(
        "/auth/change-password",
        json={"password_actual": ADMIN_PASSWORD, "password_nueva": "abc"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "6" in r.json()["detail"] or "caracteres" in r.json()["detail"].lower()
