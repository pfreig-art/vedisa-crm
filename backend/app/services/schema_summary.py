"""Resumidor del schema del dominio para el system prompt de la IA.

Toma la metadata generada por `extract_all_entities()` y las reglas de
`BUSINESS_RULES`, y produce un texto denso <= ~2000 tokens que va al system
prompt del modelo. Asi la IA tiene contexto del dominio sin pegar el JSON
crudo de /meta/schema (que ocupa 50+ KB).

Cache 5 min por proceso uvicorn.
"""
from __future__ import annotations

import time
from typing import Any

from app.core.metadata import extract_all_entities
from app.services.business_rules import BUSINESS_RULES


_CACHE_TTL_SECONDS = 300
_cache: dict[str, Any] = {"summary": None, "expires_at": 0.0}


def _format_entity(ent: dict[str, Any]) -> str:
    name = ent.get("name") or ent.get("class_name", "")
    desc = (ent.get("description") or "").strip()
    lifecycle = (ent.get("lifecycle") or "").strip()
    head = f"- {name}"
    if desc:
        head += f": {desc}"
    if lifecycle:
        head += f" Lifecycle: {lifecycle}"

    # Campos clave: PK, indexados, calculados, legacy y con examples.
    key_fields: list[str] = []
    for f in ent.get("fields", []):
        flags = []
        if f.get("primary_key"):
            flags.append("PK")
        if f.get("calculated"):
            flags.append("calc")
        if f.get("legacy"):
            flags.append("legacy")
        if f.get("unit"):
            flags.append(f.get("unit"))
        examples = f.get("examples")
        if examples:
            ex = ", ".join(str(x) for x in examples[:5])
            flags.append(f"ej {ex}")
        flag_s = f" [{' '.join(flags)}]" if flags else ""
        key_fields.append(f"{f['name']}({f['type']}){flag_s}")
    if key_fields:
        head += "\n    Campos: " + ", ".join(key_fields)
    return head


def _format_rule(rule_dict: dict[str, Any]) -> str:
    return (
        f"- {rule_dict['id']} ({rule_dict['severity']}, "
        f"{rule_dict['applies_to']}): {rule_dict['description']}"
    )


def build_schema_summary() -> str:
    """Construye el resumen denso. Llamada directa, sin cache."""
    entidades = extract_all_entities()

    lines: list[str] = []
    lines.append("=== Entidades del CRM Vedisa ===")
    for ent in entidades:
        lines.append(_format_entity(ent))

    lines.append("")
    lines.append("=== Reglas de negocio criticas ===")
    for rule in BUSINESS_RULES:
        lines.append(_format_rule(rule.to_dict()))

    lines.append("")
    lines.append(
        "=== Enums ===\n"
        "- estado_solicitud: En Estudio, Enviada, Adjudicada, Rechazada, Descartada\n"
        "- prioridad: alta, media, baja\n"
        "- rol_usuario: admin, comercial, tecnico\n"
        "- audit_accion: create, update, delete, estado_change, actuaciones_update"
    )

    return "\n".join(lines)


def get_schema_summary() -> str:
    """Devuelve el resumen cacheado durante 5 min."""
    now = time.monotonic()
    if _cache["summary"] is not None and _cache["expires_at"] > now:
        return _cache["summary"]  # type: ignore[return-value]
    summary = build_schema_summary()
    _cache["summary"] = summary
    _cache["expires_at"] = now + _CACHE_TTL_SECONDS
    return summary


def reset_cache() -> None:
    """Util para tests."""
    _cache["summary"] = None
    _cache["expires_at"] = 0.0
