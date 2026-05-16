"""Tests de /crm/alertas y de /crm/dashboard/extended."""
from datetime import date, timedelta

import pytest


pytestmark = pytest.mark.asyncio


async def _create(client, headers, nombre, fecha_limite=None, estado="En Estudio"):
    body = {"nombre_corto": nombre, "estado": estado}
    if fecha_limite is not None:
        body["fecha_limite"] = fecha_limite.isoformat()
    r = await client.post("/crm/solicitudes", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_alerta_vencida(client, auth_headers):
    ayer = date.today() - timedelta(days=1)
    sol = await _create(client, auth_headers, "Vencida ayer", ayer)

    r = await client.get("/crm/alertas", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    ids_vencidas = {v["id"] for v in body["vencidas"]}
    assert sol["id"] in ids_vencidas
    # dias_a_limite negativo
    item = next(v for v in body["vencidas"] if v["id"] == sol["id"])
    assert item["dias_a_limite"] < 0


async def test_alerta_proxima(client, auth_headers):
    en_5 = date.today() + timedelta(days=5)
    sol = await _create(client, auth_headers, "Proxima en 5", en_5)

    r = await client.get("/crm/alertas", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    ids_proximas = {p["id"] for p in body["proximas"]}
    assert sol["id"] in ids_proximas
    item = next(p for p in body["proximas"] if p["id"] == sol["id"])
    assert 0 <= item["dias_a_limite"] <= 7


async def test_alerta_30_dias_no_aparece(client, auth_headers):
    en_30 = date.today() + timedelta(days=30)
    sol = await _create(client, auth_headers, "Lejana 30 dias", en_30)

    r = await client.get("/crm/alertas", headers=auth_headers)
    body = r.json()
    todos = {x["id"] for x in body["vencidas"] + body["proximas"]}
    assert sol["id"] not in todos


async def test_dashboard_extended_estructura(client, auth_headers):
    r = await client.get("/crm/dashboard/extended", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    # El endpoint expone estos 3 bloques. kpis y embudo viven en /crm/dashboard.
    for k in ("heatmap", "top_comerciales", "mix_actuaciones"):
        assert k in body, f"clave {k} ausente en /dashboard/extended"
    assert isinstance(body["heatmap"], list)
    assert isinstance(body["top_comerciales"], list)
    assert isinstance(body["mix_actuaciones"], list)


async def test_dashboard_basico_kpis_y_forecast(client, auth_headers):
    """Los KPIs / embudo viven en /crm/dashboard (no en extended)."""
    r = await client.get("/crm/dashboard", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    for k in (
        "total_solicitudes",
        "en_estudio",
        "ofertadas",
        "ganadas",
        "perdidas",
        "tasa_conversion",
        "oferta_total",
        "forecast_mensual",
    ):
        assert k in body, f"KPI {k} ausente"
