"""Endpoints publicos de auto-descripcion del dominio (Sprint E1).

GET /meta/schema    — esquema completo: entidades, relaciones, enums,
                       reglas de negocio y endpoints. SIN auth.
GET /meta/glossary  — glosario de terminos de negocio extraido de
                       business_meaning. SIN auth.

NO exponen datos: solo metadata estructural. No filtran secrets ni
DATABASE_URL — esos NO se leen en este modulo. La respuesta se cachea en
memoria del worker uvicorn y se reconstruye al reiniciar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.metadata import extract_all_entities
from app.services.business_rules import serialize_rules


router = APIRouter()


SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Datos estaticos del dominio
# ---------------------------------------------------------------------------

ENUMS: dict[str, list[str]] = {
    "estado_solicitud": [
        "En Estudio", "Enviada", "Adjudicada", "Rechazada", "Descartada",
    ],
    "prioridad": ["alta", "media", "baja"],
    "rol_usuario": ["admin", "comercial", "tecnico"],
    "equipo_usuario": ["comercial", "estudios", "direccion", "administracion"],
    "contacto_tipo": [
        "administracion", "tecnico_obra", "ensena_obra",
        "presidente", "propiedad", "otro",
    ],
    "audit_accion": [
        "create", "update", "delete", "estado_change", "actuaciones_update",
    ],
}


RELATIONS: list[dict[str, Any]] = [
    {
        "from": "solicitudes.comercial",
        "to": "usuarios.id",
        "type": "many_to_one",
    },
    {
        "from": "solicitudes.tecnico_estudios",
        "to": "usuarios.id",
        "type": "many_to_one",
    },
    {
        "from": "solicitud_actuaciones.solicitud_id",
        "to": "solicitudes.id",
        "type": "many_to_one",
        "cascade": "delete",
    },
    {
        "from": "solicitud_actuaciones.actuacion_id",
        "to": "actuaciones.id",
        "type": "many_to_one",
    },
    {
        "from": "solicitud_contactos.solicitud_id",
        "to": "solicitudes.id",
        "type": "many_to_one",
        "cascade": "delete",
    },
    {
        "from": "audit_log.solicitud_id",
        "to": "solicitudes.id",
        "type": "many_to_one",
        "cascade": "delete",
    },
    {
        "from": "audit_log.usuario_id",
        "to": "usuarios.id",
        "type": "many_to_one",
    },
    {
        "from": "ai_audit_log.solicitud_id",
        "to": "solicitudes.id",
        "type": "many_to_one",
    },
    {
        "from": "ai_audit_log.usuario_id",
        "to": "usuarios.id",
        "type": "many_to_one",
    },
]


# Paths internos de FastAPI que NO queremos en /meta/schema:
_PATHS_OCULTOS = {
    "/openapi.json",
    "/docs",
    "/redoc",
    "/docs/oauth2-redirect",
}


def _extract_endpoints(openapi_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana app.openapi() en una lista de operaciones publicables."""
    out: list[dict[str, Any]] = []
    paths = openapi_schema.get("paths", {}) or {}
    for path, ops in paths.items():
        if path in _PATHS_OCULTOS:
            continue
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(op, dict):
                continue
            summary = op.get("summary")
            description = op.get("description")
            purpose = description or summary
            tags = op.get("tags", []) or []
            out.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "purpose": purpose,
                    "tags": tags,
                }
            )
    out.sort(key=lambda x: (x["path"], x["method"]))
    return out


# ---------------------------------------------------------------------------
# Cache por proceso
# ---------------------------------------------------------------------------

_schema_cache: Optional[dict[str, Any]] = None
_glossary_cache: Optional[dict[str, Any]] = None


def _build_schema(request: Request) -> dict[str, Any]:
    openapi_schema = request.app.openapi()
    return {
        "app": {
            "name": "Vedisa CRM",
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities": extract_all_entities(),
        "relations": RELATIONS,
        "enums": ENUMS,
        "business_rules": serialize_rules(),
        "endpoints": _extract_endpoints(openapi_schema),
    }


# Terminos clave que generan entradas de glosario al aparecer en
# business_meaning de algun campo o entidad.
_TERMINOS_GLOSARIO: dict[str, str] = {
    "oferta": "Importe que Vedisa propone facturar al cliente si se adjudica el proyecto.",
    "coste": "Coste interno estimado del proyecto; entrada manual del tecnico de estudios.",
    "margen": "Diferencia entre oferta y coste, expresada como porcentaje (margen_pct).",
    "cobertura": "Porcentaje del coste sobre la oferta; complemento de margen_pct.",
    "coeficiente": "Cociente oferta / coste. Indicador rapido de rentabilidad de la oferta.",
    "actuacion": "Tipo de obra del catalogo (fachada, cubierta, SATE...) que aplica a una solicitud.",
    "pipeline": "Conjunto de solicitudes en curso renderizado como kanban por estado.",
    "embudo": "Vista del pipeline orientada a conversion (creadas -> enviadas -> adjudicadas).",
    "aging": "Tiempo transcurrido desde la creacion de la solicitud sin cerrarse.",
    "alerta": "Solicitud con fecha_limite vencida o proxima (<=7 dias).",
    "recordatorio": "Mailto prerellenado que el admin envia para empujar una solicitud en alerta.",
    "solicitud": "Oportunidad comercial; unidad central del CRM. Sinonimo: oportunidad / proyecto.",
    "comercial": "Usuario con rol comercial; tipicamente lleva la relacion con el cliente.",
    "tecnico": "Usuario con rol tecnico; participa en estudios y valoracion de coste.",
    "auditoria": "Bitacora append-only en audit_log con cada cambio sobre solicitudes.",
}


def _build_glossary() -> dict[str, dict[str, Any]]:
    """Construye el glosario reflexivamente cruzando los terminos clave con
    los campos / entidades cuyo business_meaning los menciona."""
    entidades = extract_all_entities()
    out: dict[str, dict[str, Any]] = {}
    for termino, definicion in _TERMINOS_GLOSARIO.items():
        appears_in: list[str] = []
        t = termino.lower()
        for ent in entidades:
            ent_bm = (ent.get("business_meaning") or "").lower()
            ent_desc = (ent.get("description") or "").lower()
            if t in ent_bm or t in ent_desc:
                appears_in.append(ent["name"])
            for f in ent["fields"]:
                bm = (f.get("business_meaning") or "").lower()
                desc = (f.get("description") or "").lower()
                if t in bm or t in desc:
                    appears_in.append(f"{ent['name']}.{f['name']}")
        out[termino] = {
            "definition": definicion,
            "appears_in": sorted(set(appears_in)),
        }
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/meta/schema",
    summary="Esquema completo del dominio del CRM Vedisa",
    description=(
        "Devuelve la metadata estructurada del CRM (entidades, relaciones, "
        "enums, reglas de negocio y endpoints) para que cualquier agente / IA "
        "entienda el modelo sin leer todo el codigo. Publico (no requiere auth)."
    ),
)
async def meta_schema(request: Request) -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = _build_schema(request)
    return _schema_cache


@router.get(
    "/meta/glossary",
    summary="Glosario de terminos de negocio",
    description=(
        "Diccionario plano termino -> definicion + listado de campos / "
        "entidades donde aparece. Construido reflexivamente desde "
        "business_meaning. Publico (no requiere auth)."
    ),
)
async def meta_glossary() -> dict[str, dict[str, Any]]:
    global _glossary_cache
    if _glossary_cache is None:
        _glossary_cache = _build_glossary()
    return _glossary_cache


def _reset_caches() -> None:
    """Reinicia las caches; util para tests que modifiquen los modelos."""
    global _schema_cache, _glossary_cache
    _schema_cache = None
    _glossary_cache = None
