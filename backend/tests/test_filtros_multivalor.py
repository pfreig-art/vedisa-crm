"""Tests de filtros multi-valor del listado GET /crm/solicitudes."""

import pytest


pytestmark = pytest.mark.asyncio


async def _create(client, headers, payload):
    r = await client.post("/crm/solicitudes", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_filtro_estado_dos_valores(client, auth_headers):
    await _create(
        client, auth_headers, {"nombre_corto": "S1", "estado": "En Estudio"}
    )
    await _create(
        client,
        auth_headers,
        {
            "nombre_corto": "S2",
            "estado": "Enviada",
            "oferta": 1000,
            "fecha_enviado": "2026-02-01",
        },
    )
    await _create(
        client,
        auth_headers,
        {
            "nombre_corto": "S3",
            "estado": "Adjudicada",
            "oferta": 2000,
            "fecha_enviado": "2026-02-01",
            "fecha_cierre_cliente": "2026-03-01",
        },
    )

    r = await client.get(
        "/crm/solicitudes",
        params=[("estado", "Enviada"), ("estado", "Adjudicada")],
        headers=auth_headers,
    )
    items = r.json()["items"]
    nombres = {i["nombre_corto"] for i in items}
    assert nombres == {"S2", "S3"}


async def test_filtro_prioridad_dos_valores(client, auth_headers):
    await _create(
        client, auth_headers, {"nombre_corto": "Alta", "prioridad": "alta"}
    )
    await _create(
        client, auth_headers, {"nombre_corto": "Media", "prioridad": "media"}
    )
    await _create(
        client, auth_headers, {"nombre_corto": "Baja", "prioridad": "baja"}
    )

    r = await client.get(
        "/crm/solicitudes",
        params=[("prioridad", "alta"), ("prioridad", "media")],
        headers=auth_headers,
    )
    items = r.json()["items"]
    nombres = {i["nombre_corto"] for i in items}
    assert nombres == {"Alta", "Media"}


async def test_filtro_rango_fechas(client, auth_headers):
    await _create(
        client,
        auth_headers,
        {"nombre_corto": "Enero", "fecha_solicitud": "2026-01-15"},
    )
    await _create(
        client,
        auth_headers,
        {"nombre_corto": "Junio", "fecha_solicitud": "2026-06-15"},
    )
    await _create(
        client,
        auth_headers,
        {"nombre_corto": "Diciembre", "fecha_solicitud": "2026-12-15"},
    )

    r = await client.get(
        "/crm/solicitudes",
        params={"fecha_desde": "2026-05-01", "fecha_hasta": "2026-10-31"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    nombres = {i["nombre_corto"] for i in items}
    assert nombres == {"Junio"}
