"""Tests unitarios de la construccion del prompt del brief IA.

Cubre la deteccion de contexto vacio (`_looks_empty`) y la inyeccion de
la pista al modelo cuando no hay datos operativos. No requiere acceso a
la BBDD ni al LLM router: trabaja directamente sobre la funcion.
"""
from __future__ import annotations

from app.services.ai_prompts import (
    SYSTEM_BASE,
    _looks_empty,
    build_brief_prompt,
)


# ---------------------------------------------------------------------------
# _looks_empty
# ---------------------------------------------------------------------------


def test_looks_empty_none() -> None:
    assert _looks_empty(None) is True


def test_looks_empty_dict_vacio() -> None:
    assert _looks_empty({}) is True


def test_looks_empty_kpis_a_cero() -> None:
    ctx = {
        "total_solicitudes": 0,
        "en_estudio": 0,
        "ofertadas": 0,
        "ganadas": 0,
        "tasa_conversion": 0,
        "oferta_total": 0,
        "forecast_mensual": [],
    }
    assert _looks_empty(ctx) is True


def test_looks_empty_kpis_a_cero_con_subdict_vacio() -> None:
    ctx = {
        "kpis": {"total_solicitudes": 0, "ganadas": 0},
        "alertas": None,
        "mix_actuaciones": [],
    }
    assert _looks_empty(ctx) is True


def test_looks_empty_con_un_kpi_positivo() -> None:
    ctx = {"total_solicitudes": 0, "ganadas": 1}
    assert _looks_empty(ctx) is False


def test_looks_empty_con_lista_no_vacia() -> None:
    ctx = {"forecast_mensual": [{"mes": "2026-05", "oferta": 0}]}
    assert _looks_empty(ctx) is False


def test_looks_empty_con_string_util() -> None:
    ctx = {"nota": "comentario", "total": 0}
    assert _looks_empty(ctx) is False


def test_looks_empty_con_string_solo_espacios() -> None:
    ctx = {"nota": "   ", "total": 0}
    assert _looks_empty(ctx) is True


# ---------------------------------------------------------------------------
# build_brief_prompt
# ---------------------------------------------------------------------------


def test_build_brief_prompt_inyecta_hint_si_contexto_vacio() -> None:
    msgs = build_brief_prompt("dashboard", {}, schema_summary="")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"].startswith(SYSTEM_BASE[:40])
    user = msgs[1]["content"]
    assert "IMPORTANTE" in user
    assert "no inventes" in user.lower()
    assert "chart_specs debe ser una lista vacia" in user


def test_build_brief_prompt_no_inyecta_hint_con_contexto_real() -> None:
    ctx = {
        "kpis": {"total_solicitudes": 11, "ganadas": 3},
        "forecast_mensual": [{"mes": "2026-05", "oferta": 12000}],
    }
    msgs = build_brief_prompt("dashboard", ctx, schema_summary="")
    user = msgs[1]["content"]
    assert "IMPORTANTE" not in user
    assert "Contexto actual (JSON)" in user


def test_build_brief_prompt_incluye_schema_summary_en_system() -> None:
    schema = "Entidad Solicitud: campos id, estado, oferta_total."
    msgs = build_brief_prompt("default", None, schema_summary=schema)
    sys_msg = msgs[0]["content"]
    assert "Resumen del dominio" in sys_msg
    assert schema in sys_msg


def test_build_brief_prompt_modo_desconocido_cae_en_default() -> None:
    msgs = build_brief_prompt("modo_que_no_existe", {"x": 1}, schema_summary="")
    user = msgs[1]["content"]
    # El template default empieza con "Resume el contexto actual del CRM..."
    assert "Resume el contexto actual del CRM" in user
