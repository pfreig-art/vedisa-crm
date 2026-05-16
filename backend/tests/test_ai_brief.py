"""Tests del endpoint POST /ai/brief (Sprint E2)."""
import json

import pytest

from app.providers.base import LLMResponse


@pytest.fixture
def mock_llm_ok(monkeypatch):
    """Sustituye llm_router.generate por una respuesta JSON sintetica."""
    payload = {
        "summary": "Pipeline saludable con 3 oportunidades en Enviada.",
        "bullets": [
            "Mayor concentracion en Adjudicada.",
            "2 solicitudes vencidas.",
            "Margen medio 28%.",
        ],
        "suggested_questions": [
            "Que solicitudes deberia priorizar hoy?",
            "Cual es el margen real del trimestre?",
        ],
        "chart_specs": [
            {
                "type": "donut",
                "title": "Estados",
                "data": [
                    {"name": "En Estudio", "value": 5},
                    {"name": "Enviada", "value": 3},
                ],
                "x": "name",
                "y": "value",
            },
            {
                "type": "kpi",
                "title": "Margen medio",
                "data": [{"name": "%", "value": 28}],
                "x": "name",
                "y": "value",
            },
        ],
    }

    async def fake_generate(request, provider_name=None):
        return LLMResponse(
            content=json.dumps(payload, ensure_ascii=False),
            provider=provider_name or "openai",
            model="gpt-4o",
            tokens_used=420,
            latency_ms=312,
            raw={},
        )

    monkeypatch.setattr(
        "app.api.ai.llm_router.generate", fake_generate, raising=True
    )
    return payload


@pytest.fixture
def mock_llm_invalid(monkeypatch):
    """Sustituye llm_router.generate por una respuesta no-JSON."""
    async def fake_generate(request, provider_name=None):
        return LLMResponse(
            content="Lo siento, no puedo responder en formato JSON aqui.",
            provider=provider_name or "openai",
            model="gpt-4o",
            tokens_used=50,
            latency_ms=120,
            raw={},
        )

    monkeypatch.setattr(
        "app.api.ai.llm_router.generate", fake_generate, raising=True
    )


@pytest.fixture
def mock_llm_raise(monkeypatch):
    """Hace que el router falle (simula provider caido)."""
    async def fake_generate(request, provider_name=None):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.api.ai.llm_router.generate", fake_generate, raising=True
    )


@pytest.fixture(autouse=True)
def reset_brief_cache():
    """Limpia el cache global antes y despues de cada test."""
    from app.api.ai import _reset_brief_cache

    _reset_brief_cache()
    yield
    _reset_brief_cache()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brief_sin_auth_devuelve_401(client):
    r = await client.post("/ai/brief", json={"mode": "dashboard"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_brief_dashboard_con_mock_devuelve_200_y_estructura(
    client, auth_headers, mock_llm_ok
):
    r = await client.post(
        "/ai/brief",
        json={"mode": "dashboard", "context": {"kpis": {"oferta_total": 100000}}},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("summary", "bullets", "suggested_questions", "chart_specs",
                "model", "provider", "tokens_used", "latency_ms"):
        assert key in body, f"missing key {key}"
    assert "Pipeline saludable" in body["summary"]
    assert len(body["bullets"]) == 3
    assert len(body["chart_specs"]) == 2
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o"
    # Header de cache: primera llamada no cacheada.
    assert r.headers.get("X-Brief-Cached") == "false"


@pytest.mark.asyncio
async def test_brief_segunda_llamada_misma_clave_es_cache_hit(
    client, auth_headers, mock_llm_ok
):
    body_in = {"mode": "dashboard", "context": {"x": 1}}
    r1 = await client.post("/ai/brief", json=body_in, headers=auth_headers)
    assert r1.status_code == 200
    assert r1.headers.get("X-Brief-Cached") == "false"

    r2 = await client.post("/ai/brief", json=body_in, headers=auth_headers)
    assert r2.status_code == 200
    assert r2.headers.get("X-Brief-Cached") == "true"
    # Mismo payload servido del cache.
    assert r2.json()["summary"] == r1.json()["summary"]


@pytest.mark.asyncio
async def test_brief_force_refresh_ignora_cache(
    client, auth_headers, mock_llm_ok
):
    body_in = {"mode": "dashboard", "context": {"y": 2}}
    r1 = await client.post("/ai/brief", json=body_in, headers=auth_headers)
    assert r1.status_code == 200

    r2 = await client.post(
        "/ai/brief",
        json={**body_in, "force_refresh": True},
        headers=auth_headers,
    )
    assert r2.status_code == 200
    assert r2.headers.get("X-Brief-Cached") == "false"


@pytest.mark.asyncio
async def test_brief_provider_devuelve_texto_no_json_fallback_200(
    client, auth_headers, mock_llm_invalid
):
    r = await client.post(
        "/ai/brief",
        json={"mode": "solicitud", "context": {"codigo": "SOL-2026-0001"}},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    # Fallback graceful.
    assert "No se pudo generar" in body["summary"]
    assert body["bullets"] == []
    assert body["chart_specs"] == []


@pytest.mark.asyncio
async def test_brief_provider_excepcion_fallback_200(
    client, auth_headers, mock_llm_raise
):
    r = await client.post(
        "/ai/brief",
        json={"mode": "obra", "context": {}},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bullets"] == []
    assert body["chart_specs"] == []
    # Fallback NO se cachea: si vuelve a pedir, vuelve a intentar (no cached).
    r2 = await client.post(
        "/ai/brief",
        json={"mode": "obra", "context": {}},
        headers=auth_headers,
    )
    assert r2.headers.get("X-Brief-Cached") == "false"


# ---------------------------------------------------------------------------
# Unit tests del parser de respuesta
# ---------------------------------------------------------------------------

def test_parse_brief_response_json_limpio():
    from app.services.ai_prompts import parse_brief_response

    raw = json.dumps({
        "summary": "OK",
        "bullets": ["a", "b"],
        "suggested_questions": ["q1?"],
        "chart_specs": [],
    })
    parsed = parse_brief_response(raw)
    assert parsed["summary"] == "OK"
    assert parsed["bullets"] == ["a", "b"]


def test_parse_brief_response_envuelto_en_code_fence():
    from app.services.ai_prompts import parse_brief_response

    raw = "Claro, aqui tienes el brief:\n```json\n{\"summary\": \"Texto\", \"bullets\": [], \"suggested_questions\": [], \"chart_specs\": []}\n```\n"
    parsed = parse_brief_response(raw)
    assert parsed["summary"] == "Texto"


def test_parse_brief_response_chart_specs_filtra_tipos_invalidos():
    from app.services.ai_prompts import parse_brief_response

    raw = json.dumps({
        "summary": "x",
        "chart_specs": [
            {"type": "donut", "title": "ok", "data": [{"name": "a", "value": 1}]},
            {"type": "scatter", "title": "no-soportado"},  # filtrado
            {"type": "kpi", "title": "K", "data": [{"name": "n", "value": 42}]},
        ],
    })
    parsed = parse_brief_response(raw)
    tipos = [c["type"] for c in parsed["chart_specs"]]
    assert tipos == ["donut", "kpi"]
