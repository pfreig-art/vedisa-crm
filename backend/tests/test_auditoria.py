"""Tests del flujo de auditoria automatica al editar solicitudes."""
import pytest


pytestmark = pytest.mark.asyncio


async def test_dos_updates_en_campos_distintos_generan_historial_desc(
    client, auth_headers
):
    create = await client.post(
        "/crm/solicitudes",
        json={"nombre_corto": "Audit Multi", "oferta": 1000},
        headers=auth_headers,
    )
    sid = create.json()["id"]

    # Update 1: cambia oferta.
    r1 = await client.put(
        f"/crm/solicitudes/{sid}", json={"oferta": 2000}, headers=auth_headers
    )
    assert r1.status_code == 200

    # Update 2: cambia poblacion.
    r2 = await client.put(
        f"/crm/solicitudes/{sid}",
        json={"poblacion": "Barcelona"},
        headers=auth_headers,
    )
    assert r2.status_code == 200

    hist = await client.get(
        f"/crm/solicitudes/{sid}/historial", headers=auth_headers
    )
    assert hist.status_code == 200
    entries = hist.json()

    # Esperamos al menos 1 create + 1 update oferta + 1 update poblacion.
    acciones = [(e["accion"], e["campo"]) for e in entries]
    assert ("update", "oferta") in acciones
    assert ("update", "poblacion") in acciones

    # Orden DESC por created_at.
    times = [e["created_at"] for e in entries]
    assert times == sorted(times, reverse=True)

    # Cada entrada de update tiene valor_anterior y valor_nuevo.
    update_oferta = next(
        e for e in entries if e["accion"] == "update" and e["campo"] == "oferta"
    )
    assert update_oferta["valor_anterior"] == "1000.0"
    assert update_oferta["valor_nuevo"] == "2000.0"

    # Usuario serializado en el historial.
    assert update_oferta["usuario_nombre"]
    assert update_oferta["usuario_iniciales"] is not None
