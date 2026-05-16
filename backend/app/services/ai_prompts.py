"""Plantillas de prompt para el brief contextual del drawer IA (Sprint E2).

Construye los mensajes (system + user) que se envian al modelo. El system
incluye la identidad del asistente, el alcance restringido (solo CRM
Vedisa) y un resumen denso del schema. El user contiene la plantilla
especifica del modo + el contexto serializado a JSON (truncado).
"""
from __future__ import annotations

import json
import re
from typing import Any


MAX_CONTEXT_CHARS = 6000
MAX_SCHEMA_CHARS = 8000  # ~2000 tokens aprox


SYSTEM_BASE = (
    "Eres el asistente IA del CRM Vedisa. Tu unico alcance es ayudar al "
    "equipo comercial y de estudios a interpretar el pipeline, las "
    "solicitudes y las obras gestionadas con este CRM. "
    "No respondes preguntas fuera del dominio (no eres un buscador general "
    "ni un asistente de proposito general). "
    "Trabajas en castellano, con tono claro y profesional, sin emojis. "
    "Cuando el usuario pida un brief, devuelves SIEMPRE un unico objeto JSON "
    "valido sin texto adicional ni delimitadores Markdown. "
    "Schema de salida obligatorio:\n"
    "{\n"
    '  "summary": "1 frase de cabecera, max 140 caracteres",\n'
    '  "bullets": ["bullet 1", "bullet 2", "bullet 3"],\n'
    '  "suggested_questions": ["pregunta 1?", "pregunta 2?", "pregunta 3?"],\n'
    '  "chart_specs": [{"type": "donut|bar|line|kpi", "title": "...", '
    '"data": [{"name": "...", "value": 0}], "x": "name", "y": "value"}]\n'
    "}\n"
    "Reglas: max 5 bullets, max 4 suggested_questions, max 3 chart_specs. "
    "chart_specs.data puede ser lista vacia si no hay datos suficientes. "
    "Para type='kpi', usa una sola entrada en data con name=etiqueta y "
    "value=numero."
)


_USER_TEMPLATES: dict[str, str] = {
    "dashboard": (
        "Analiza el pipeline comercial. Identifica los 3 hallazgos mas "
        "importantes y propon 2 visualizaciones (chart_specs) que ayuden "
        "a decidir. Las visualizaciones deben basarse en los KPIs, embudo "
        "o forecast del contexto."
    ),
    "solicitud": (
        "Diagnostica esta oportunidad concreta. Evalua su estado actual, "
        "los riesgos visibles (fechas vencidas, oferta vs coste, falta de "
        "datos) y propon la siguiente accion comercial. Las "
        "visualizaciones, si las hay, deben centrarse en el detalle "
        "financiero de esta solicitud (margen vs coste, lineas de "
        "actuaciones)."
    ),
    "obra": (
        "Evalua el estado de esta obra/proyecto y los riesgos de plazo. "
        "Identifica que falta para cerrar la oferta o ejecutar la obra y "
        "propon hasta 2 visualizaciones que ayuden a anticipar problemas."
    ),
    "default": (
        "Resume el contexto actual del CRM en 3 lineas y propon hasta 2 "
        "visualizaciones utiles si el contexto lo permite."
    ),
}


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[: limit - 50] + "\n[...contexto truncado...]"


def build_brief_prompt(
    mode: str,
    context: dict | None,
    schema_summary: str = "",
) -> list[dict[str, str]]:
    """Construye los mensajes para una llamada al modelo.

    Devuelve una lista de dicts {role, content} compatible con el cliente
    OpenAI / el LLM router de Vedisa.
    """
    template = _USER_TEMPLATES.get(mode, _USER_TEMPLATES["default"])

    schema_block = ""
    if schema_summary:
        schema_block = (
            "\nResumen del dominio del CRM (para fundamentar tus respuestas):\n"
            + _truncate(schema_summary, MAX_SCHEMA_CHARS)
        )

    system_content = SYSTEM_BASE + schema_block

    ctx_json = json.dumps(context or {}, ensure_ascii=False, indent=2)
    ctx_block = _truncate(ctx_json, MAX_CONTEXT_CHARS)
    user_content = f"{template}\n\nContexto actual (JSON):\n{ctx_block}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Parser robusto del output del modelo
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE
)


def _coerce_str_list(value: Any, max_items: int = 8) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if x is not None][:max_items]
    if value is None:
        return []
    return [str(value)]


def _coerce_chart_specs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        spec_type = str(item.get("type", "")).lower()
        if spec_type not in {"donut", "pie", "bar", "line", "kpi"}:
            continue
        data = item.get("data", [])
        if not isinstance(data, list):
            data = []
        out.append(
            {
                "type": spec_type,
                "title": str(item.get("title", "")),
                "data": [
                    d for d in data if isinstance(d, dict)
                ][:24],
                "x": item.get("x", "name"),
                "y": item.get("y", "value"),
            }
        )
    return out


def parse_brief_response(raw: str) -> dict[str, Any]:
    """Extrae el JSON del output del modelo y valida el shape minimo.

    Acepta JSON limpio o envuelto en ```json ... ```. Si no consigue
    parsearlo, devuelve un dict vacio normalizado (no levanta excepcion).
    """
    if not raw or not isinstance(raw, str):
        return _empty()

    # Caso 1: JSON directo.
    candidate = raw.strip()
    obj: Any = None
    try:
        obj = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        # Caso 2: extraer del primer code fence ```json ... ```.
        m = _JSON_FENCE_RE.search(candidate)
        if m:
            try:
                obj = json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                obj = None
        # Caso 3: primer bloque que parezca un objeto JSON.
        if obj is None:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start != -1 and end > start:
                try:
                    obj = json.loads(candidate[start : end + 1])
                except (json.JSONDecodeError, ValueError):
                    obj = None

    if not isinstance(obj, dict):
        return _empty()

    summary = str(obj.get("summary", "")).strip()
    return {
        "summary": summary[:280] if summary else "",
        "bullets": _coerce_str_list(obj.get("bullets"), max_items=5),
        "suggested_questions": _coerce_str_list(
            obj.get("suggested_questions"), max_items=4
        ),
        "chart_specs": _coerce_chart_specs(obj.get("chart_specs")),
    }


def _empty() -> dict[str, Any]:
    return {
        "summary": "",
        "bullets": [],
        "suggested_questions": [],
        "chart_specs": [],
    }


def fallback_response(reason: str = "") -> dict[str, Any]:
    """Respuesta canonica cuando el provider falla o el JSON no parsea."""
    return {
        "summary": "No se pudo generar brief automatico.",
        "bullets": [],
        "suggested_questions": [],
        "chart_specs": [],
        "_fallback_reason": reason,
    }
