"""Tests del endpoint GET/PUT /crm/solicitudes/{id}/actuaciones (bloque C)."""
import pytest


pytestmark = pytest.mark.asyncio


async def _seed_actuaciones(client, auth_headers, session):
    """Inserta tres actuaciones de catalogo para los tests."""
    from app.core.models import Actuacion

    for slug, nombre, orden in [
        ("fachada", "Fachada", 10),
        ("cubierta", "Cubierta", 20),
        ("zbcc", "ZBCC", 30),
    ]:
        session.add(Actuacion(id=slug, nombre=nombre, orden=orden, activo=True))
    await session.commit()


async def _crear_solicitud(client, auth_headers, nombre="Test"):
    r = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": nombre},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_put_actuaciones_persiste_con_m2_e_importe(
    client, auth_headers, session
):
    await _seed_actuaciones(client, auth_headers, session)
    sol = await _crear_solicitud(client, auth_headers, "Con actuaciones")

    payload = {
        "actuaciones": [
            {"actuacion_id": "fachada", "m2": 120.5, "importe": 9500.0},
            {"actuacion_id": "cubierta", "m2": 80.0, "importe": 4000.0},
        ]
    }
    r = await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json=payload,
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text

    g = await client.get(
        f"/crm/solicitudes/{sol['id']}/actuaciones", headers=auth_headers
    )
    assert g.status_code == 200
    items = g.json()
    assert len(items) == 2
    by_id = {i["actuacion_id"]: i for i in items}
    assert by_id["fachada"]["m2"] == 120.5
    assert by_id["fachada"]["importe"] == 9500.0
    assert by_id["fachada"]["actuacion_nombre"] == "Fachada"
    assert by_id["cubierta"]["m2"] == 80.0


async def test_put_actuaciones_upsert_borra_anade_actualiza(
    client, auth_headers, session
):
    await _seed_actuaciones(client, auth_headers, session)
    sol = await _crear_solicitud(client, auth_headers, "Upsert")

    # Estado inicial: fachada + cubierta.
    await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json={
            "actuaciones": [
                {"actuacion_id": "fachada", "m2": 100, "importe": 5000},
                {"actuacion_id": "cubierta", "m2": 50, "importe": 2000},
            ]
        },
        headers=auth_headers,
    )

    # Nuevo set: borra cubierta, actualiza fachada, anade zbcc.
    await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json={
            "actuaciones": [
                {"actuacion_id": "fachada", "m2": 150, "importe": 7500},
                {"actuacion_id": "zbcc", "m2": 20, "importe": 1000},
            ]
        },
        headers=auth_headers,
    )

    items = (
        await client.get(
            f"/crm/solicitudes/{sol['id']}/actuaciones", headers=auth_headers
        )
    ).json()
    by_id = {i["actuacion_id"]: i for i in items}
    assert set(by_id.keys()) == {"fachada", "zbcc"}
    assert by_id["fachada"]["m2"] == 150  # actualizado
    assert by_id["fachada"]["importe"] == 7500


async def test_put_actuaciones_id_inexistente_422(
    client, auth_headers, session
):
    await _seed_actuaciones(client, auth_headers, session)
    sol = await _crear_solicitud(client, auth_headers, "Bad id")

    r = await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json={"actuaciones": [{"actuacion_id": "no-existe", "m2": 1}]},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "no-existe" in str(r.json()["detail"]).lower()


async def test_put_actuaciones_audit_log(client, auth_headers, session):
    await _seed_actuaciones(client, auth_headers, session)
    sol = await _crear_solicitud(client, auth_headers, "Audit")

    await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json={
            "actuaciones": [
                {"actuacion_id": "fachada", "m2": 50, "importe": 3000}
            ]
        },
        headers=auth_headers,
    )

    hist = await client.get(
        f"/crm/solicitudes/{sol['id']}/historial", headers=auth_headers
    )
    assert hist.status_code == 200
    acciones = [e["accion"] for e in hist.json()]
    assert "actuaciones_update" in acciones
    entry = next(
        e for e in hist.json() if e["accion"] == "actuaciones_update"
    )
    assert entry["campo"] == "actuaciones"
    # valor_nuevo es JSON con el nombre de la actuacion.
    assert "fachada" in entry["valor_nuevo"].lower() or "Fachada" in entry["valor_nuevo"]


async def test_put_actuaciones_legacy_payload(client, auth_headers, session):
    """El formato legacy {actuacion_ids: [...]} sigue funcionando."""
    await _seed_actuaciones(client, auth_headers, session)
    sol = await _crear_solicitud(client, auth_headers, "Legacy")

    r = await client.put(
        f"/crm/solicitudes/{sol['id']}/actuaciones",
        json={"actuacion_ids": ["fachada", "cubierta"]},
        headers=auth_headers,
    )
    assert r.status_code == 200

    items = (
        await client.get(
            f"/crm/solicitudes/{sol['id']}/actuaciones", headers=auth_headers
        )
    ).json()
    ids = {i["actuacion_id"] for i in items}
    assert ids == {"fachada", "cubierta"}
    # m2 e importe nulos cuando se usa el formato legacy.
    for i in items:
        assert i["m2"] is None
        assert i["importe"] is None
