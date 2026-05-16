"""CRM API - Solicitudes, Pipeline, Dashboard con PostgreSQL real."""
import io
import csv
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
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
    total_pages: int

class EstadoUpdate(BaseModel):
    estado: str
    kanban_column: Optional[str] = None
    color_estado: Optional[str] = None

# -- Endpoints --------------------------------------------------------

@router.get("/solicitudes", response_model=PaginatedSolicitudes)
async def list_solicitudes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: Optional[str] = None,
    comercial: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    q = select(Solicitud)
    filters = []
    if estado:
        filters.append(Solicitud.estado == estado)
    if comercial:
        filters.append(Solicitud.comercial == comercial)
    if search:
        filters.append(
            Solicitud.nombre_corto.ilike(f"%{search}%")
            | Solicitud.codigo.ilike(f"%{search}%")
        )
    if filters:
        q = q.where(and_(*filters))

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return PaginatedSolicitudes(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 1,
    )

@router.get("/solicitudes/export")
async def export_solicitudes(
    formato: str = Query("csv", regex="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_session),
):
    """Exporta todas las solicitudes en CSV o Excel."""
    result = await db.execute(select(Solicitud).order_by(Solicitud.created_at.desc()))
    rows = result.scalars().all()

    campos = [
        "codigo", "nombre_corto", "poblacion", "estado", "prioridad",
        "comercial", "tecnico_estudios", "fecha_solicitud", "fecha_limite",
        "oferta", "aging_dias", "created_at",
    ]

    if formato == "xlsx":
        try:
            import openpyxl
        except ImportError:
            raise HTTPException(status_code=500, detail="openpyxl no instalado")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Solicitudes"
        ws.append(campos)
        for s in rows:
            ws.append([str(getattr(s, c) or "") for c in campos])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=solicitudes.xlsx"},
        )
    else:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(campos)
        for s in rows:
            writer.writerow([str(getattr(s, c) or "") for c in campos])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=solicitudes.csv"},
        )

@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudFront)
async def get_solicitud(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return s

@router.get("/solicitudes/{solicitud_id}/context")
async def get_solicitud_context(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return {
        "solicitud_id": s.id,
        "codigo": s.codigo,
        "nombre_corto": s.nombre_corto,
        "estado": s.estado,
        "comercial": s.comercial,
        "oferta": s.oferta,
        "aging_dias": s.aging_dias,
        "observaciones": s.observaciones,
        "contactos": s.contactos,
        "actuaciones": s.actuaciones,
    }

@router.patch("/solicitudes/{solicitud_id}/estado")
async def update_estado(
    solicitud_id: str,
    body: EstadoUpdate,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    s.estado = body.estado
    if body.kanban_column:
        s.kanban_column = body.kanban_column
    if body.color_estado:
        s.color_estado = body.color_estado
    s.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(s)
    return s

@router.get("/pipeline")
async def get_pipeline(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud))
    all_rows = result.scalars().all()
    columnas = [
        {"estado": "En Estudio", "label": "En Estudio", "color": "#6366f1"},
        {"estado": "Ofertada", "label": "Ofertada", "color": "#f59e0b"},
        {"estado": "Ganada", "label": "Ganada", "color": "#10b981"},
        {"estado": "Perdida", "label": "Perdida", "color": "#ef4444"},
    ]
    pipeline = []
    for col in columnas:
        items = [s for s in all_rows if s.estado == col["estado"]]
        pipeline.append({
            "estado": col["estado"],
            "label": col["label"],
            "color": col["color"],
            "count": len(items),
            "total_oferta": round(sum(s.oferta or 0 for s in items), 2),
            "items": items,
        })
    return pipeline

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_session)):
    """KPIs: conversion, aging, financiero, tiempo_medio, forecast mensual."""
    result = await db.execute(select(Solicitud))
    all_rows = result.scalars().all()

    total = len(all_rows)
    en_estudio = sum(1 for s in all_rows if s.estado == "En Estudio")
    ofertadas = sum(1 for s in all_rows if s.estado == "Ofertada")
    ganadas = sum(1 for s in all_rows if s.estado == "Ganada")
    perdidas = sum(1 for s in all_rows if s.estado == "Perdida")
    tasa_conversion = round(ganadas / total, 4) if total > 0 else 0.0
    oferta_total = round(sum(s.oferta or 0 for s in all_rows), 2)

    # Tiempo medio de cierre (dias)
    cerradas = [s for s in all_rows if s.estado in ("Ganada", "Perdida") and s.fecha_solicitud]
    if cerradas:
        tiempo_medio = round(
            sum((date.today() - s.fecha_solicitud).days for s in cerradas) / len(cerradas), 1
        )
    else:
        tiempo_medio = 0.0

    # Aging promedio
    con_aging = [s for s in all_rows if s.aging_dias is not None]
    aging_promedio = round(sum(s.aging_dias for s in con_aging) / len(con_aging), 1) if con_aging else 0.0

    # Forecast mensual: ultimos 6 meses
    hoy = date.today()
    forecast_meses = []
    for i in range(5, -1, -1):
        # Primer dia del mes i meses atras
        mes = hoy.month - i
        anio = hoy.year
        while mes <= 0:
            mes += 12
            anio -= 1
        mes_inicio = date(anio, mes, 1)
        if mes == 12:
            mes_fin = date(anio + 1, 1, 1)
        else:
            mes_fin = date(anio, mes + 1, 1)
        ganadas_mes = [
            s for s in all_rows
            if s.estado == "Ganada"
            and s.fecha_solicitud
            and mes_inicio <= s.fecha_solicitud < mes_fin
        ]
        forecast_meses.append({
            "mes": mes_inicio.strftime("%b %Y"),
            "ganadas": len(ganadas_mes),
            "oferta": round(sum(s.oferta or 0 for s in ganadas_mes), 2),
        })

    return {
        "total_solicitudes": total,
        "en_estudio": en_estudio,
        "ofertadas": ofertadas,
        "ganadas": ganadas,
        "perdidas": perdidas,
        "tasa_conversion": tasa_conversion,
        "oferta_total": oferta_total,
        "aging_promedio": aging_promedio,
        "tiempo_medio_cierre": tiempo_medio,
        "forecast_mensual": forecast_meses,
    }

