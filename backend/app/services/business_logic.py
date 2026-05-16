"""Logica de negocio pura para el CRM Vedisa — Sprint C."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog


# ---------------------------------------------------------------------------
# 1.1 Calculos financieros
# ---------------------------------------------------------------------------

def calcular_financiero(oferta: Optional[float], coste: Optional[float]) -> dict:
    """Devuelve {margen_pct, cobertura_pct, coeficiente} calculados.

    Si oferta y coste estan presentes y oferta > 0 y coste > 0, calcula los
    tres indicadores. En caso contrario, devuelve None para los campos que no
    se puedan calcular. Redondea a 2 decimales.
    """
    margen_pct: Optional[float] = None
    cobertura_pct: Optional[float] = None
    coeficiente: Optional[float] = None

    if oferta is not None and coste is not None and oferta > 0:
        margen_pct = round((oferta - coste) / oferta * 100, 2)
        cobertura_pct = round(coste / oferta * 100, 2)
        if coste > 0:
            coeficiente = round(oferta / coste, 2)

    return {
        "margen_pct": margen_pct,
        "cobertura_pct": cobertura_pct,
        "coeficiente": coeficiente,
    }


# ---------------------------------------------------------------------------
# 1.2 Validaciones por estado
# ---------------------------------------------------------------------------

def validar_solicitud_para_estado(solicitud_data: dict, estado: str) -> list[str]:
    """Devuelve lista de errores. Vacia si todo OK."""
    errors: list[str] = []

    if estado == "Enviada":
        if not solicitud_data.get("fecha_enviado"):
            errors.append("Estado 'Enviada' requiere fecha_enviado")
        oferta = solicitud_data.get("oferta")
        if not oferta or oferta <= 0:
            errors.append("Estado 'Enviada' requiere oferta > 0")

    elif estado == "Adjudicada":
        if not solicitud_data.get("fecha_cierre_cliente"):
            errors.append("Estado 'Adjudicada' requiere fecha_cierre_cliente")
        oferta = solicitud_data.get("oferta")
        if not oferta or oferta <= 0:
            errors.append("Estado 'Adjudicada' requiere oferta > 0")

    elif estado == "Rechazada":
        if not solicitud_data.get("fecha_cierre_cliente"):
            errors.append("Estado 'Rechazada' requiere fecha_cierre_cliente")

    # "Descartada" y "En Estudio": sin requisitos

    return errors


# ---------------------------------------------------------------------------
# 1.3 Validacion de fechas
# ---------------------------------------------------------------------------

def _parse_date(v: Any) -> Optional[date]:
    """Convierte string ISO, date o datetime a date. Devuelve None si falla."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except (ValueError, TypeError):
        return None


def validar_fechas(fechas: dict) -> list[str]:
    """Valida el orden logico de las fechas de una solicitud.

    Orden esperado: fecha_solicitud <= fecha_reunion <= fecha_visita
                    <= fecha_enviado <= fecha_cierre_cliente.
    fecha_limite es informativa y no rompe el flujo.
    Solo valida las fechas que esten presentes.
    """
    ORDEN = [
        "fecha_solicitud",
        "fecha_reunion",
        "fecha_visita",
        "fecha_enviado",
        "fecha_cierre_cliente",
    ]

    errors: list[str] = []
    parsed: dict[str, date] = {}

    for campo in ORDEN:
        val = fechas.get(campo)
        if val is not None:
            d = _parse_date(val)
            if d is not None:
                parsed[campo] = d

    # Comparar pares consecutivos que esten presentes
    present_campos = [c for c in ORDEN if c in parsed]
    for i in range(len(present_campos) - 1):
        c1 = present_campos[i]
        c2 = present_campos[i + 1]
        if parsed[c1] > parsed[c2]:
            errors.append(
                f"{c2} ({parsed[c2].isoformat()}) no puede ser anterior a "
                f"{c1} ({parsed[c1].isoformat()})"
            )

    return errors


# ---------------------------------------------------------------------------
# 1.4 Calculo dias_a_limite (no persistido)
# ---------------------------------------------------------------------------

def calcular_dias_a_limite(fecha_limite: Optional[date]) -> Optional[int]:
    """Dias desde hoy hasta fecha_limite. Negativo si ya paso. None si no hay fecha."""
    if fecha_limite is None:
        return None
    return (fecha_limite - date.today()).days


# ---------------------------------------------------------------------------
# 2.3 Hook de auditoria
# ---------------------------------------------------------------------------

async def registrar_cambios(
    db: AsyncSession,
    solicitud_id: str,
    usuario_id: Optional[str],
    accion: str,
    cambios: dict[str, tuple[Any, Any]],
) -> None:
    """Inserta una fila por cada campo cambiado en audit_log.

    Para accion='create' o 'delete', inserta una sola fila con campo=None.
    Filtra campos sin cambios (anterior == nuevo).
    Serializa valores a str (None -> '').
    """
    import uuid as _uuid_mod

    def _str(v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    if accion in ("create", "delete"):
        # Una sola fila sin campo especifico
        log = AuditLog(
            id=str(_uuid_mod.uuid4()),
            solicitud_id=solicitud_id,
            usuario_id=usuario_id,
            accion=accion,
            campo=None,
            valor_anterior=None,
            valor_nuevo=None,
            created_at=datetime.utcnow(),
        )
        db.add(log)
    else:
        for campo, (anterior, nuevo) in cambios.items():
            if anterior == nuevo:
                continue
            log = AuditLog(
                id=str(_uuid_mod.uuid4()),
                solicitud_id=solicitud_id,
                usuario_id=usuario_id,
                accion=accion,
                campo=campo,
                valor_anterior=_str(anterior),
                valor_nuevo=_str(nuevo),
                created_at=datetime.utcnow(),
            )
            db.add(log)
