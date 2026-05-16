"""Tests del endpoint GET /crm/alertas/recordatorio/{id}."""
from datetime import date, timedelta
from urllib.parse import unquote

import pytest


pytestmark = pytest.mark.asyncio


async def _crear(client, headers, nombre, fecha_limite):
    r = await client.post(
        "/crm/solicitudes",
        json={
            "nombre_corto": nombre,
            "fecha_limite": fecha_limite.isoformat(),
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_recordatorio_vencida(client, auth_headers):
    ayer = date.today() - timedelta(days=3)
    sol = await _crear(client, auth_headers, "Vencida hace 3 dias", ayer)

    r = await client.get(
        f"/crm/alertas/recordatorio/{sol['id']}", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "vencida hace" in body["asunto"].lower()
    assert "vencida hace 3 dias" in body["asunto"].lower()
    assert body["mailto_url"].startswith("mailto:?")
    # asunto y cuerpo correctamente codificados en la URL.
    assert "subject=" in body["mailto_url"]
    assert "body=" in body["mailto_url"]
    assert "vencida hace" in unquote(body["mailto_url"]).lower()
    assert body["dias_a_limite"] == -3


async def test_recordatorio_proxima(client, auth_headers):
    en_5 = date.today() + timedelta(days=5)
    sol = await _crear(client, auth_headers, "Proxima en 5 dias", en_5)

    r = await client.get(
        f"/crm/alertas/recordatorio/{sol['id']}", headers=auth_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert "vence en" in body["asunto"].lower()
    assert "vence en 5 dias" in body["asunto"].lower()
    assert "vence en" in unquote(body["mailto_url"]).lower()
    assert body["dias_a_limite"] == 5


async def test_recordatorio_admin_only(client, comercial_user):
    """El endpoint requiere rol admin (require_role('admin'))."""
    from app.core.auth import create_access_token

    token = create_access_token(
        {"sub": comercial_user.email, "rol": comercial_user.rol}
    )
    headers = {"Authorization": f"Bearer {token}"}
    # Necesitamos una solicitud cualquiera; la creamos como admin no es posible
    # con el client de comercial. Probamos con un id inventado: el guard de rol
    # se evalua antes de la consulta DB, asi que debe 403.
    r = await client.get(
        "/crm/alertas/recordatorio/no-existe", headers=headers
    )
    assert r.status_code == 403


async def test_recordatorio_solicitud_inexistente_404(client, auth_headers):
    r = await client.get(
        "/crm/alertas/recordatorio/no-existe", headers=auth_headers
    )
    assert r.status_code == 404
