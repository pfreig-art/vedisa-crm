"""Tests de POST/PUT/GET /crm/solicitudes incluyendo validaciones y financiero."""
import pytest


pytestmark = pytest.mark.asyncio


async def test_crear_solicitud_basica(client, auth_headers):
    r = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Obra Test", "estado": "En Estudio"},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nombre_corto"] == "Obra Test"
    assert body["estado"] == "En Estudio"
    assert body["codigo"].startswith("SOL-")
    assert body["id"]


async def test_crear_solicitud_calcula_financieros(client, auth_headers):
    r = await client.post(
        "/crm/solicitudes",
        json={
            "nombre_corto": "Calculo financiero",
            "oferta": 12000,
            "coste": 9000,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["cobertura_pct"] == 75.0
    assert body["coeficiente"] == 1.33
    assert body["margen_pct"] == 25.0


async def test_crear_enviada_sin_fecha_enviado_422(client, auth_headers):
    r = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Mala Enviada", "estado": "Enviada", "oferta": 1000},
        headers=auth_headers,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "errors" in detail
    assert any("fecha_enviado" in e for e in detail["errors"])


async def test_crear_adjudicada_sin_cierre_422(client, auth_headers):
    r = await client.post(
        "/crm/solicitudes",
        json={
            "nombre_corto": "Mala Adj",
            "estado": "Adjudicada",
            "oferta": 5000,
            "fecha_enviado": "2026-01-15",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any("fecha_cierre_cliente" in e for e in detail["errors"])


async def test_listar_solicitudes_incluye_campos_financieros(client, auth_headers):
    """Hotfix Sprint C: SolicitudItem debe exponer coste, cobertura_pct,
    coeficiente y margen_pct en la respuesta del listado."""
    create = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Listado fin", "oferta": 10000, "coste": 7000},
        headers=auth_headers,
    )
    assert create.status_code == 201

    r = await client.get("/crm/solicitudes", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    item = next(i for i in items if i["nombre_corto"] == "Listado fin")
    # Las 4 claves deben existir en el SolicitudItem serializado.
    for k in ("coste", "cobertura_pct", "coeficiente", "margen_pct"):
        assert k in item, f"campo {k} ausente en SolicitudItem"
    assert item["coste"] == 7000
    assert item["cobertura_pct"] == 70.0
    assert item["margen_pct"] == 30.0


async def test_listado_filtro_estado_multivalor(client, auth_headers):
    """?estado=Enviada&estado=Adjudicada devuelve SOLO esos estados."""
    # 3 solicitudes con estados distintos.
    await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "A", "estado": "En Estudio"},
        headers=auth_headers,
    )
    await client.post(
        "/crm/solicitudes",
        json={
            "nombre_corto": "B",
            "estado": "Enviada",
            "oferta": 5000,
            "fecha_enviado": "2026-02-01",
        },
        headers=auth_headers,
    )
    await client.post(
        "/crm/solicitudes",
        json={
            "nombre_corto": "C",
            "estado": "Adjudicada",
            "oferta": 7000,
            "fecha_enviado": "2026-02-01",
            "fecha_cierre_cliente": "2026-03-01",
        },
        headers=auth_headers,
    )

    r = await client.get(
        "/crm/solicitudes",
        params=[("estado", "Enviada"), ("estado", "Adjudicada")],
        headers=auth_headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    nombres = {i["nombre_corto"] for i in items}
    assert "A" not in nombres
    assert "B" in nombres
    assert "C" in nombres


async def test_put_solicitud_cambiando_oferta_genera_audit(client, auth_headers):
    create = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Audit oferta", "oferta": 1000, "coste": 500},
        headers=auth_headers,
    )
    sid = create.json()["id"]

    # Cambiar oferta -> auditoria registra cambios.
    upd = await client.put(
        f"/crm/solicitudes/{sid}",
        json={"oferta": 2000},
        headers=auth_headers,
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["oferta"] == 2000

    hist = await client.get(
        f"/crm/solicitudes/{sid}/historial", headers=auth_headers
    )
    assert hist.status_code == 200
    entries = hist.json()
    # Hay al menos: create + cambio oferta + recalculo margen/cobertura/coeficiente.
    campos = [e["campo"] for e in entries if e["accion"] == "update"]
    assert "oferta" in campos


async def test_patch_estado_genera_audit_estado_change(client, auth_headers):
    create = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Patch estado"},
        headers=auth_headers,
    )
    sid = create.json()["id"]

    r = await client.patch(
        f"/crm/solicitudes/{sid}/estado",
        json={"estado": "Descartada"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text

    hist = await client.get(
        f"/crm/solicitudes/{sid}/historial", headers=auth_headers
    )
    acciones = [e["accion"] for e in hist.json()]
    assert "estado_change" in acciones
