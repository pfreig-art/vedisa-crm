"""Catalogo declarativo de reglas de negocio del CRM Vedisa.

Es la documentacion canonica de las reglas que viven en el codigo
(business_logic.py, api/crm.py, api/auth.py, api/health.py...). Se sirve
desde /meta/schema para que cualquier agente / IA entienda el dominio sin
leer el codigo, y se renderiza como tabla en docs/DOMAIN.md.

Cada regla con un id estable tipo 'BR-SOL-001' para poder referenciarla
desde issues, PRs y prompts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class BusinessRule:
    id: str
    description: str
    applies_to: str
    condition: str
    effect: str
    severity: str  # "error" | "warning" | "info"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Reglas catalogadas
# ---------------------------------------------------------------------------

BUSINESS_RULES: list[BusinessRule] = [
    # --- Transiciones de estado --------------------------------------------
    BusinessRule(
        id="BR-SOL-001",
        description="Una solicitud solo puede pasar a Enviada si tiene fecha_enviado y oferta > 0.",
        applies_to="solicitudes",
        condition="estado == 'Enviada' AND (fecha_enviado IS NULL OR oferta <= 0)",
        effect="POST/PUT/PATCH responden HTTP 422 con detail.errors.",
        severity="error",
    ),
    BusinessRule(
        id="BR-SOL-002",
        description="Una solicitud solo puede pasar a Adjudicada si tiene fecha_cierre_cliente y oferta > 0.",
        applies_to="solicitudes",
        condition="estado == 'Adjudicada' AND (fecha_cierre_cliente IS NULL OR oferta <= 0)",
        effect="POST/PUT/PATCH responden HTTP 422 con detail.errors.",
        severity="error",
    ),
    BusinessRule(
        id="BR-SOL-003",
        description="Una solicitud solo puede pasar a Rechazada si tiene fecha_cierre_cliente.",
        applies_to="solicitudes",
        condition="estado == 'Rechazada' AND fecha_cierre_cliente IS NULL",
        effect="POST/PUT/PATCH responden HTTP 422 con detail.errors.",
        severity="error",
    ),
    BusinessRule(
        id="BR-SOL-004",
        description="Las fechas deben respetar el orden cronologico: fecha_solicitud <= fecha_reunion <= fecha_visita <= fecha_enviado <= fecha_cierre_cliente.",
        applies_to="solicitudes",
        condition="Cualquier par consecutivo de fechas presentes esta invertido.",
        effect="POST/PUT responden HTTP 422 con detail.errors enumerando los pares en conflicto.",
        severity="error",
    ),

    # --- Calculos financieros ---------------------------------------------
    BusinessRule(
        id="BR-FIN-001",
        description="margen_pct = round((oferta - coste) / oferta * 100, 2) cuando oferta > 0.",
        applies_to="solicitudes.margen_pct",
        condition="oferta > 0 AND coste IS NOT NULL",
        effect="margen_pct se recalcula server-side en POST/PUT; el cliente NO puede sobreescribirlo.",
        severity="info",
    ),
    BusinessRule(
        id="BR-FIN-002",
        description="cobertura_pct = round(coste / oferta * 100, 2) cuando oferta > 0.",
        applies_to="solicitudes.cobertura_pct",
        condition="oferta > 0 AND coste IS NOT NULL",
        effect="cobertura_pct se recalcula server-side en POST/PUT.",
        severity="info",
    ),
    BusinessRule(
        id="BR-FIN-003",
        description="coeficiente = round(oferta / coste, 2) cuando oferta > 0 y coste > 0.",
        applies_to="solicitudes.coeficiente",
        condition="oferta > 0 AND coste > 0",
        effect="coeficiente se recalcula server-side; null si coste = 0.",
        severity="info",
    ),

    # --- Alertas ------------------------------------------------------------
    BusinessRule(
        id="BR-ALR-001",
        description="Una solicitud aparece como 'vencida' si fecha_limite < hoy y estado in (En Estudio, Enviada).",
        applies_to="solicitudes",
        condition="(fecha_limite - hoy).days < 0",
        effect="Aparece en /crm/alertas bajo la clave 'vencidas' y dispara recordatorios.",
        severity="warning",
    ),
    BusinessRule(
        id="BR-ALR-002",
        description="Una solicitud aparece como 'proxima' si 0 <= dias_a_limite <= 7 y estado in (En Estudio, Enviada).",
        applies_to="solicitudes",
        condition="0 <= (fecha_limite - hoy).days <= 7",
        effect="Aparece en /crm/alertas bajo la clave 'proximas'.",
        severity="info",
    ),

    # --- Auditoria ----------------------------------------------------------
    BusinessRule(
        id="BR-AUD-001",
        description="Cualquier UPDATE en solicitudes registra una fila por campo cambiado en audit_log con accion='update'.",
        applies_to="audit_log",
        condition="PUT /crm/solicitudes/{id} con campos modificados.",
        effect="Insercion automatica en audit_log; el historial se lee desde GET /crm/solicitudes/{id}/historial.",
        severity="info",
    ),
    BusinessRule(
        id="BR-AUD-002",
        description="Cambio de estado se audita como accion='estado_change' (PATCH /estado).",
        applies_to="audit_log",
        condition="PATCH /crm/solicitudes/{id}/estado",
        effect="Fila en audit_log con accion='estado_change', campo='estado'.",
        severity="info",
    ),
    BusinessRule(
        id="BR-AUD-003",
        description="Reemplazo de actuaciones se audita como accion='actuaciones_update' con valor_anterior/valor_nuevo en JSON.",
        applies_to="audit_log",
        condition="PUT /crm/solicitudes/{id}/actuaciones que produce cambios.",
        effect="Una unica fila en audit_log con el diff serializado.",
        severity="info",
    ),

    # --- Permisos / acceso --------------------------------------------------
    BusinessRule(
        id="BR-PRM-001",
        description="El PDF de oferta solo se genera si la solicitud esta en estado Enviada o Adjudicada.",
        applies_to="solicitudes",
        condition="estado NOT IN ('Enviada', 'Adjudicada')",
        effect="GET /crm/solicitudes/{id}/oferta.pdf responde HTTP 400.",
        severity="error",
    ),
    BusinessRule(
        id="BR-PRM-002",
        description="GET /crm/alertas/recordatorio/{id} esta restringido a usuarios con rol admin.",
        applies_to="usuarios.rol",
        condition="rol != 'admin'",
        effect="Endpoint devuelve HTTP 403.",
        severity="error",
    ),
    BusinessRule(
        id="BR-PRM-003",
        description="Si el usuario no es admin, /crm/alertas filtra solo a solicitudes donde es comercial o tecnico_estudios.",
        applies_to="solicitudes",
        condition="current_user.rol != 'admin'",
        effect="WHERE comercial = current_user.id OR tecnico_estudios = current_user.id.",
        severity="info",
    ),
    BusinessRule(
        id="BR-PRM-004",
        description="Login con usuario inactivo responde HTTP 403 con detail 'Usuario desactivado'.",
        applies_to="usuarios.activo",
        condition="activo == False",
        effect="POST /auth/login devuelve 403; las credenciales correctas no bastan.",
        severity="error",
    ),
]


def rules_for_entity(entity_name: str) -> list[BusinessRule]:
    """Filtra reglas por entidad (matching parcial sobre applies_to)."""
    return [r for r in BUSINESS_RULES if entity_name in r.applies_to]


def serialize_rules() -> list[dict[str, Any]]:
    """Serializa todas las reglas a dicts para JSON / docs."""
    return [r.to_dict() for r in BUSINESS_RULES]
