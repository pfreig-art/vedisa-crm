"""Helpers para anotar SQLModels con metadata escalable.

Estrategia: el `description` se pone como kwarg nativo de Pydantic en
`Field(description=...)` (queda en `FieldInfo.description`). El resto de
metadata extra (business_meaning, examples, unit, calculated, legacy) vive
en un mapping de clase `__field_meta__: dict[str, dict]` indexado por
nombre de campo. La reflexion los une.

El motivo es que SQLModel.Field hace `**schema_extra` y colisiona con
`description` cuando se inyecta por dos rutas. Separar en dos canales evita
ese choque y mantiene la metadata co-located con el modelo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, get_args, get_origin, Union
import typing

from sqlmodel import SQLModel


# ---------------------------------------------------------------------------
# Helpers para anotar campos y clases
# ---------------------------------------------------------------------------

def field_meta(
    *,
    business_meaning: Optional[str] = None,
    examples: Optional[list] = None,
    unit: Optional[str] = None,
    calculated: bool = False,
    legacy: bool = False,
) -> dict[str, Any]:
    """Devuelve el dict de metadata extra (sin description; esa va en Field()).

    Se guarda en `Cls.__field_meta__["nombre_del_campo"]`.
    """
    out: dict[str, Any] = {}
    if business_meaning is not None:
        out["business_meaning"] = business_meaning
    if examples is not None:
        out["examples"] = examples
    if unit is not None:
        out["unit"] = unit
    if calculated:
        out["calculated"] = True
    if legacy:
        out["legacy"] = True
    return out


@dataclass
class EntityMeta:
    description: str
    business_meaning: Optional[str] = None
    lifecycle: Optional[str] = None


def entity_meta(
    *,
    description: str,
    business_meaning: Optional[str] = None,
    lifecycle: Optional[str] = None,
) -> EntityMeta:
    return EntityMeta(
        description=description,
        business_meaning=business_meaning,
        lifecycle=lifecycle,
    )


# ---------------------------------------------------------------------------
# Reflexion sobre SQLModel
# ---------------------------------------------------------------------------

def _normalize_type(annotation: Any) -> tuple[str, bool]:
    is_optional = False
    if get_origin(annotation) is Union:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]  # noqa: E721
        if len(non_none) == 1 and len(args) == 2:
            is_optional = True
            annotation = non_none[0]
    if annotation in (int, float, str, bool, bytes):
        return annotation.__name__, is_optional
    name = getattr(annotation, "__name__", None) or str(annotation)
    return name, is_optional


def _is_primary_key(model_cls: type, name: str) -> bool:
    try:
        table = model_cls.__table__  # type: ignore[attr-defined]
        col = table.columns.get(name)
        return bool(col is not None and col.primary_key)
    except Exception:
        return False


def extract_entity_metadata(model_cls: type[SQLModel]) -> dict[str, Any]:
    tablename = getattr(model_cls, "__tablename__", model_cls.__name__.lower())
    entity_meta_obj: Optional[EntityMeta] = getattr(model_cls, "__meta__", None)
    extras: dict[str, dict[str, Any]] = getattr(model_cls, "__field_meta__", {}) or {}

    fields_info = getattr(model_cls, "model_fields", {})
    annotations = typing.get_type_hints(model_cls)

    fields_out: list[dict[str, Any]] = []
    for name, info in fields_info.items():
        annot = annotations.get(name, str)
        type_name, is_optional = _normalize_type(annot)
        extra = extras.get(name, {})
        required = info.is_required() if hasattr(info, "is_required") else not is_optional
        primary_key = _is_primary_key(model_cls, name)

        fields_out.append(
            {
                "name": name,
                "type": type_name,
                "required": bool(required),
                "optional": bool(is_optional),
                "primary_key": primary_key,
                "description": getattr(info, "description", None),
                "business_meaning": extra.get("business_meaning"),
                "examples": extra.get("examples"),
                "unit": extra.get("unit"),
                "calculated": bool(extra.get("calculated", False)),
                "legacy": bool(extra.get("legacy", False)),
            }
        )

    return {
        "name": tablename,
        "class_name": model_cls.__name__,
        "description": entity_meta_obj.description if entity_meta_obj else None,
        "business_meaning": entity_meta_obj.business_meaning if entity_meta_obj else None,
        "lifecycle": entity_meta_obj.lifecycle if entity_meta_obj else None,
        "fields": fields_out,
    }


def _collect_recursive(
    cls: type, entidades: list[dict[str, Any]], seen: set[str]
) -> None:
    is_table = hasattr(cls, "__tablename__") and hasattr(cls, "__table__")
    if is_table and cls.__name__ not in seen:
        entidades.append(extract_entity_metadata(cls))
        seen.add(cls.__name__)
    for sub in cls.__subclasses__():
        _collect_recursive(sub, entidades, seen)


def extract_all_entities() -> list[dict[str, Any]]:
    from app.core import models  # noqa: F401

    entidades: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cls in SQLModel.__subclasses__():
        _collect_recursive(cls, entidades, seen)
    entidades.sort(key=lambda e: e["name"])
    return entidades
