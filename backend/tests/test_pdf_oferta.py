"""Tests del endpoint GET /crm/solicitudes/{id}/oferta.pdf."""
import pytest


pytestmark = pytest.mark.asyncio


async def _crear_solicitud_en_estado(
    client, auth_headers, nombre, estado, **extras
):
    """Crea una solicitud directamente en el estado pedido.

    Necesitamos saltar las validaciones del POST que exigen fechas concretas
    cuando estado in ('Enviada', 'Adjudicada'). Lo hacemos creando primero
    En Estudio y luego usando PATCH /estado (la transicion no exige fechas).
    """
    base = {"nombre_corto": nombre}
    base.update(extras)
    r = await client.post("/crm/solicitudes", json=base, headers=auth_headers)
    assert r.status_code == 201, r.text
    sol = r.json()
    if estado != "En Estudio":
        r2 = await client.patch(
            f"/crm/solicitudes/{sol['id']}/estado",
            json={"estado": estado},
            headers=auth_headers,
        )
        assert r2.status_code == 200, r2.text
        sol = r2.json()
    return sol


async def test_pdf_rechazado_en_estudio(client, auth_headers):
    sol = await _crear_solicitud_en_estado(
        client, auth_headers, "Solo estudio", "En Estudio"
    )
    r = await client.get(
        f"/crm/solicitudes/{sol['id']}/oferta.pdf", headers=auth_headers
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "En Estudio" in detail or "Enviada" in detail


async def test_pdf_ok_en_adjudicada(client, auth_headers):
    sol = await _crear_solicitud_en_estado(
        client,
        auth_headers,
        "Adjudicada PDF",
        "Adjudicada",
        oferta=12000.0,
        coste=9000.0,
    )
    r = await client.get(
        f"/crm/solicitudes/{sol['id']}/oferta.pdf", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    # Cabecera magica de PDF.
    assert r.content[:4] == b"%PDF"
    # Content-Disposition con nombre coherente.
    cd = r.headers.get("content-disposition", "")
    assert "oferta_" in cd
    assert ".pdf" in cd
    assert sol["codigo"] in cd


async def test_pdf_ok_en_enviada(client, auth_headers):
    sol = await _crear_solicitud_en_estado(
        client, auth_headers, "Enviada PDF", "Enviada", oferta=5000.0
    )
    r = await client.get(
        f"/crm/solicitudes/{sol['id']}/oferta.pdf", headers=auth_headers
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


async def test_pdf_solicitud_inexistente_404(client, auth_headers):
    r = await client.get(
        "/crm/solicitudes/no-existe/oferta.pdf", headers=auth_headers
    )
    assert r.status_code == 404
