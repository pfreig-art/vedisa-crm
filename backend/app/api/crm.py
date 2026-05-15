"""CRM API - Solicitudes, Pipeline, Dashboard con PostgreSQL real."""
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from app.core.database import get_session
from app.core.models import Solicitud
import math

router = APIRouter()

# -- Schemas ----------------------------------------------------------

class ContactoRef(BaseModel):
    nombre: str
    rol: str
    telefono: Optional[str] = None
    email: Optional[str] = None

class SolicitudItem(BaseModel):
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
    fecha_solicitud: Optional[date] = None
    fecha_limite: Optional[date] = None
    aging_dias: Optional[int] = None
    oferta: Optional[float] = None

    class Config:
        from_attributes = True

class SolicitudFront(SolicitudItem):
    estudio_direccion: Optional[str] = None
    presupuesto: Optional[str] = None
    contactos: Optional[str] = None
    actuaciones: Optional[str] = None
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True

class PipelineColumn(BaseModel):
    estado: str
    label: str
    color: str
    count: int
    total_oferta: float
    items: List[SolicitudItem]

class PaginatedSolicitudes(BaseModel):
    items: List[SolicitudItem]
    total: int
    page: int
    page_size: int
    pages: int

class EstadoUpdate(BaseModel):
    estado: str

# -- Estado meta -------------------------------------------------------

ESTADO_META = {
    "En Estudio":  {"label": "En Estudio",  "color": "#6366f1"},
    "Enviada":     {"label": "Pte. Cierre", "color": "#f59e0b"},
    "Adjudicada":  {"label": "Adjudicada",  "color": "#10b981"},
    "Rechazada":   {"label": "Rechazada",   "color": "#ef4444"},
    "Descartada":  {"label": "Descartada",  "color": "#6b7280"},
}

# -- Endpoints ---------------------------------------------------------

@router.get("/solicitudes", response_model=PaginatedSolicitudes)
async def list_solicitudes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: Optional[str] = Query(None),
    comercial: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_session),
):
    q = select(Solicitud)
    if estado:
        q = q.where(Solicitud.estado == estado)
    if comercial:
        q = q.where(Solicitud.comercial == comercial)
    if prioridad:
        q = q.where(Solicitud.prioridad == prioridad)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(Solicitud.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedSolicitudes(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )

@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudFront)
async def get_solicitud(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    sol = result.scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return sol

@router.get("/solicitudes/{solicitud_id}/context")
async def get_solicitud_context(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    sol = result.scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {
        "id": sol.id,
        "codigo": sol.codigo,
        "nombre_corto": sol.nombre_corto,
        "estado": sol.estado,
        "prioridad": sol.prioridad,
        "comercial": sol.comercial,
        "tecnico_estudios": sol.tecnico_estudios,
        "oferta": sol.oferta,
        "aging_dias": sol.aging_dias,
        "observaciones": sol.observaciones,
        "actuaciones": sol.actuaciones,
    }

@router.patch("/solicitudes/{solicitud_id}/estado")
async def update_estado(
    solicitud_id: str,
    body: EstadoUpdate,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    sol = result.scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if body.estado not in ESTADO_META:
        raise HTTPException(status_code=400, detail=f"Estado invalido: {body.estado}")
    sol.estado = body.estado
    sol.kanban_column = ESTADO_META[body.estado]["label"]
    sol.color_estado = ESTADO_META[body.estado]["color"]
    sol.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(sol)
    return {"ok": True, "estado": sol.estado}

@router.get("/pipeline", response_model=List[PipelineColumn])
async def get_pipeline(db: AsyncSession = Depends(get_session)):
    columns = []
    for estado, meta in ESTADO_META.items():
        q = select(Solicitud).where(Solicitud.estado == estado)
        result = await db.execute(q)
        items = result.scalars().all()
        total_oferta = sum(s.oferta or 0 for s in items)
        columns.append(PipelineColumn(
            estado=estado,
            label=meta["label"],
            color=meta["color"],
            count=len(items),
            total_oferta=total_oferta,
            items=items,
        ))
    return columns

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud))
    seed = result.scalars().all()

    total = len(seed)
    en_estudio = sum(1 for s in seed if s.estado == "En Estudio")
    ofertadas = sum(1 for s in seed if s.estado in ["Enviada", "Pte. Cierre"])
    ganadas = sum(1 for s in seed if s.estado == "Adjudicada")
    perdidas = sum(1 for s in seed if s.estado in ["Rechazada", "Descartada"])
    aging_vals = [s.aging_dias for s in seed if s.aging_dias]
    aging_prom = round(sum(aging_vals) / len(aging_vals), 1) if aging_vals else 0
    ofertas = [s.oferta for s in seed if s.oferta]
    oferta_total = sum(ofertas)
    adjudicadas_oferta = sum(s.oferta or 0 for s in seed if s.estado == "Adjudicada")
    rechazadas_oferta = sum(s.oferta or 0 for s in seed if s.estado in ["Rechazada", "Descartada"])
    tasa = round((adjudicadas_oferta / (adjudicadas_oferta + rechazadas_oferta)) * 100, 1) if (adjudicadas_oferta + rechazadas_oferta) else 0

    comerciales_set = set(s.comercial for s in seed if s.comercial)
    comerciales = [
        {
            "nombre": c,
            "total": sum(1 for s in seed if s.comercial == c),
            "adjudicadas": sum(1 for s in seed if s.comercial == c and s.estado == "Adjudicada"),
            "oferta": sum(s.oferta or 0 for s in seed if s.comercial == c),
        }
        for c in comerciales_set
    ]

    return {
        "total_solicitudes": total,
        "en_estudio": en_estudio,
        "ofertadas": ofertadas,
        "ganadas": ganadas,
        "perdidas": perdidas,
        "aging_promedio": aging_prom,
        "tasa_conversion": tasa,
        "oferta_total": oferta_total,
        "pipeline_por_estado": [
            {
                "estado": e,
                "count": sum(1 for s in seed if s.estado == e),
                "total_oferta": sum(s.oferta or 0 for s in seed if s.estado == e),
                "color": m["color"]
            }
            for e, m in ESTADO_META.items()
        ],
        "comerciales": comerciales,
    }
