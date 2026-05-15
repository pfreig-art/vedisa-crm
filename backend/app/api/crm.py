"""Endpoints CRM - Solicitudes, Pipeline y Dashboard."""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

# ---- Schemas read models -----------------------------------------

class ContactoRef(BaseModel):
    nombre: str
    rol: str
    telefono: Optional[str] = None
    email: Optional[str] = None


class SolicitudListItem(BaseModel):
    id: str
    codigo: str
    nombre_corto: str
    poblacion: Optional[str] = None
    estado: str
    kanban_column: str
    color_estado: str
    prioridad: str
    comercial: Optional[str] = None
    tecnico_estudios: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    fecha_limite: Optional[datetime] = None
    aging_dias: Optional[int] = None
    oferta: Optional[float] = None


class SolicitudFront(BaseModel):
    id: str
    codigo: str
    nombre_corto: str
    estudio_direccion: Optional[str] = None
    poblacion: Optional[str] = None
    estado: str
    prioridad: str
    comercial: Optional[str] = None
    tecnico_estudios: Optional[str] = None
    fechas: dict = {}
    presupuesto: dict = {}
    contactos: list[ContactoRef] = []
    actuaciones: list[str] = []
    observaciones: Optional[str] = None
    kpis: dict = {}


class PipelineColumn(BaseModel):
    estado: str
    label: str
    color: str
    solicitudes: list[SolicitudListItem]


class EstadoTransition(BaseModel):
    nuevo_estado: str
    motivo: Optional[str] = None


# ---- Mock data helper (sustituir por queries reales) --------------

ESTADO_COLORS = {
    "Pte. Aprobacion": "#94a3b8",
    "Aprobado": "#22c55e",
    "Pte. Visita": "#f59e0b",
    "En Estudio": "#3b82f6",
    "Enviada": "#8b5cf6",
    "Pte. Cierre": "#f97316",
    "Adjudicada": "#10b981",
    "Rechazado": "#ef4444",
    "Descartada": "#6b7280",
}

KANBAN_ORDER = list(ESTADO_COLORS.keys())


# ---- Endpoints ---------------------------------------------------

@router.get("/solicitudes", response_model=list[SolicitudListItem])
async def list_solicitudes(
    estado: Optional[str] = Query(None),
    comercial: Optional[str] = Query(None),
    tecnico: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Lista server-side de solicitudes con filtros y paginacion."""
    # TODO: implementar query real a PostgreSQL
    return []


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudFront)
async def get_solicitud(solicitud_id: str):
    """Ficha completa de una solicitud."""
    # TODO: implementar query real
    raise HTTPException(404, f"Solicitud {solicitud_id} no encontrada")


@router.get("/pipeline", response_model=list[PipelineColumn])
async def get_pipeline(
    comercial: Optional[str] = Query(None),
    tecnico: Optional[str] = Query(None),
):
    """Columnas del kanban pipeline con tarjetas por estado."""
    # TODO: implementar query real
    columns = [
        PipelineColumn(
            estado=estado,
            label=estado,
            color=color,
            solicitudes=[],
        )
        for estado, color in ESTADO_COLORS.items()
    ]
    return columns


@router.patch("/solicitudes/{solicitud_id}/estado")
async def update_estado(
    solicitud_id: str,
    transition: EstadoTransition,
):
    """Transicion de estado con registro en historial."""
    # TODO: validar transicion, guardar historial, emitir evento
    return {
        "solicitud_id": solicitud_id,
        "nuevo_estado": transition.nuevo_estado,
        "ok": True,
    }


@router.get("/dashboard")
async def get_dashboard():
    """Snapshot de KPIs del CRM de solicitudes."""
    # TODO: reemplazar con queries reales a PostgreSQL
    return {
        "total_solicitudes": 0,
        "en_estudio": 0,
        "ofertadas": 0,
        "ganadas": 0,
        "perdidas": 0,
        "aging_promedio": 0.0,
        "tasa_conversion": 0.0,
        "oferta_total": 0.0,
    }


@router.get("/solicitudes/{solicitud_id}/context")
async def get_solicitud_context(solicitud_id: str):
    """Construye el AIContextBundle para el drawer IA de una solicitud."""
    # TODO: usar ContextBuilder service para ensamblar datos reales
    return {
        "solicitud_id": solicitud_id,
        "estado": "desconocido",
        "comercial": None,
        "tecnico_estudios": None,
        "fechas": {},
        "presupuesto": {},
        "contactos": [],
        "actuaciones": [],
        "historial_reciente": [],
    }
