"""CRM API - Solicitudes, Pipeline, Dashboard con PostgreSQL real."""
import io
import csv
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from app.core.database import get_session
from app.core.models import (
    Solicitud,
    Usuario,
    AuditLog,
    SolicitudContacto,
    Actuacion,
    SolicitudActuacion,
)
from app.core.auth import hash_password, require_role, get_current_user
from app.services.business_logic import (
    calcular_financiero,
    validar_solicitud_para_estado,
    validar_fechas,
    calcular_dias_a_limite,
    registrar_cambios,
)
import math
import uuid as _uuid

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
    coste: Optional[float] = None
    cobertura_pct: Optional[float] = None
    coeficiente: Optional[float] = None
    margen_pct: Optional[float] = None
    dias_a_limite: Optional[int] = None

    class Config:
        from_attributes = True

class SolicitudFront(SolicitudItem):
    # Campos legacy
    estudio_direccion: Optional[str] = None
    presupuesto: Optional[str] = None
    contactos: Optional[str] = None
    actuaciones: Optional[str] = None
    observaciones: Optional[str] = None
    # Sprint A: direccion / fechas extra
    tipo_via: Optional[str] = None
    numero: Optional[str] = None
    cp: Optional[str] = None
    fecha_reunion: Optional[date] = None
    fecha_visita: Optional[date] = None
    fecha_enviado: Optional[date] = None
    fecha_cierre_cliente: Optional[date] = None
    descripcion: Optional[str] = None
    # Sprint A: financiero extra
    cobertura_pct: Optional[float] = None
    coste: Optional[float] = None
    coeficiente: Optional[float] = None
    margen_pct: Optional[float] = None
    # Sprint D bloque C: lineas de actuacion con m2 / importe.
    actuaciones_asignadas: List[dict] = []

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


# -- AuditLog schemas --------------------------------------------------

class AuditLogOut(BaseModel):
    id: str
    solicitud_id: str
    usuario_id: Optional[str] = None
    usuario_nombre: Optional[str] = None
    usuario_iniciales: Optional[str] = None
    usuario_color: Optional[str] = None
    accion: str
    campo: Optional[str] = None
    valor_anterior: Optional[str] = None
    valor_nuevo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# -- Helpers ----------------------------------------------------------

def _solicitud_to_front(s: Solicitud) -> dict:
    """Convierte un objeto Solicitud a dict con dias_a_limite calculado."""
    d = {}
    for col in Solicitud.__table__.columns:
        d[col.name] = getattr(s, col.name)
    d["dias_a_limite"] = calcular_dias_a_limite(s.fecha_limite)
    return d


# -- Endpoints --------------------------------------------------------

@router.get("/solicitudes", response_model=PaginatedSolicitudes)
async def list_solicitudes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    # Filtros simples legacy
    search: Optional[str] = None,
    # Sprint C: filtros multi-valor
    estado: List[str] = Query(default=[]),
    prioridad: List[str] = Query(default=[]),
    comercial: List[str] = Query(default=[]),
    tecnico: List[str] = Query(default=[]),
    actuacion: List[str] = Query(default=[]),
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: AsyncSession = Depends(get_session),
):
    q = select(Solicitud)
    filters = []

    # Filtros multi-valor (OR dentro del filtro, AND entre filtros)
    if estado:
        filters.append(or_(*[Solicitud.estado == e for e in estado]))
    if prioridad:
        filters.append(or_(*[Solicitud.prioridad == p for p in prioridad]))
    if comercial:
        filters.append(or_(*[Solicitud.comercial == c for c in comercial]))
    if tecnico:
        filters.append(or_(*[Solicitud.tecnico_estudios == t for t in tecnico]))
    if search:
        filters.append(
            Solicitud.nombre_corto.ilike(f"%{search}%")
            | Solicitud.codigo.ilike(f"%{search}%")
        )
    if fecha_desde:
        filters.append(Solicitud.fecha_solicitud >= fecha_desde)
    if fecha_hasta:
        filters.append(Solicitud.fecha_solicitud <= fecha_hasta)

    # Filtro por actuacion: requiere JOIN con solicitud_actuaciones
    if actuacion:
        actuacion_subq = (
            select(SolicitudActuacion.solicitud_id)
            .where(SolicitudActuacion.actuacion_id.in_(actuacion))
            .distinct()
            .scalar_subquery()
        )
        filters.append(Solicitud.id.in_(actuacion_subq))

    if filters:
        q = q.where(and_(*filters))

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items_raw = result.scalars().all()

    # Enriquecer con dias_a_limite
    items = []
    for s in items_raw:
        item_dict = _solicitud_to_front(s)
        items.append(SolicitudItem(**{k: item_dict[k] for k in SolicitudItem.model_fields if k in item_dict}))

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

@router.get("/solicitudes/{solicitud_id}/historial", response_model=List[AuditLogOut])
async def get_historial(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Historial de auditoria de una solicitud, ordenado por fecha desc."""
    # Verificar que la solicitud existe
    sol = (await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))).scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    logs_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.solicitud_id == solicitud_id)
        .order_by(AuditLog.created_at.desc())
    )
    logs = logs_result.scalars().all()

    # Cargar usuarios para enriquecer la respuesta
    usuario_ids = {log.usuario_id for log in logs if log.usuario_id}
    usuarios_map: dict = {}
    if usuario_ids:
        u_result = await db.execute(select(Usuario).where(Usuario.id.in_(usuario_ids)))
        for u in u_result.scalars().all():
            usuarios_map[u.id] = u

    out = []
    for log in logs:
        u = usuarios_map.get(log.usuario_id) if log.usuario_id else None
        out.append(AuditLogOut(
            id=log.id,
            solicitud_id=log.solicitud_id,
            usuario_id=log.usuario_id,
            usuario_nombre=u.nombre if u else None,
            usuario_iniciales=u.iniciales if u else None,
            usuario_color=u.color if u else None,
            accion=log.accion,
            campo=log.campo,
            valor_anterior=log.valor_anterior,
            valor_nuevo=log.valor_nuevo,
            created_at=log.created_at,
        ))
    return out


@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudFront)
async def get_solicitud(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    d = _solicitud_to_front(s)

    # Lineas de actuaciones (Sprint D bloque C).
    act_q = await db.execute(
        select(SolicitudActuacion, Actuacion)
        .join(Actuacion, Actuacion.id == SolicitudActuacion.actuacion_id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
        .order_by(Actuacion.orden)
    )
    d["actuaciones_asignadas"] = [
        {
            "actuacion_id": sa.actuacion_id,
            "actuacion_nombre": ac.nombre,
            "m2": sa.m2,
            "importe": sa.importe,
        }
        for sa, ac in act_q.all()
    ]
    return SolicitudFront(**{k: d[k] for k in SolicitudFront.model_fields if k in d})

@router.get("/solicitudes/{solicitud_id}/context")
async def get_solicitud_context(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    # Cargar actuaciones N-N y contactos hijos
    act_q = (
        select(Actuacion.nombre)
        .join(SolicitudActuacion, SolicitudActuacion.actuacion_id == Actuacion.id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
        .order_by(Actuacion.orden)
    )
    actuaciones_norm = [r[0] for r in (await db.execute(act_q)).all()]
    contactos_q = await db.execute(
        select(SolicitudContacto).where(SolicitudContacto.solicitud_id == solicitud_id)
    )
    contactos_norm = [
        {"tipo": c.tipo, "nombre": c.nombre, "telefono": c.telefono, "email": c.email}
        for c in contactos_q.scalars().all()
    ]
    return {
        "solicitud_id": s.id,
        "codigo": s.codigo,
        "nombre_corto": s.nombre_corto,
        "poblacion": s.poblacion,
        "estado": s.estado,
        "prioridad": s.prioridad,
        "comercial": s.comercial,
        "tecnico_estudios": s.tecnico_estudios,
        "oferta": s.oferta,
        "cobertura_pct": s.cobertura_pct,
        "coste": s.coste,
        "coeficiente": s.coeficiente,
        "margen_pct": s.margen_pct,
        "aging_dias": s.aging_dias,
        "fecha_solicitud": s.fecha_solicitud,
        "fecha_limite": s.fecha_limite,
        "fecha_reunion": s.fecha_reunion,
        "fecha_visita": s.fecha_visita,
        "fecha_enviado": s.fecha_enviado,
        "fecha_cierre_cliente": s.fecha_cierre_cliente,
        "descripcion": s.descripcion,
        "observaciones": s.observaciones,
        "contactos": contactos_norm or s.contactos,
        "actuaciones": actuaciones_norm or s.actuaciones,
    }

@router.patch("/solicitudes/{solicitud_id}/estado")
async def update_estado(
    solicitud_id: str,
    body: EstadoUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    estado_anterior = s.estado
    s.estado = body.estado
    if body.kanban_column:
        s.kanban_column = body.kanban_column
    if body.color_estado:
        s.color_estado = body.color_estado
    s.updated_at = datetime.utcnow()
    await db.flush()

    # Auditoria del cambio de estado
    await registrar_cambios(
        db=db,
        solicitud_id=solicitud_id,
        usuario_id=current_user.id,
        accion="estado_change",
        cambios={"estado": (estado_anterior, body.estado)},
    )

    await db.commit()
    await db.refresh(s)
    return s


# -- Sprint C: Alertas ------------------------------------------------

@router.get("/alertas")
async def get_alertas(
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Devuelve solicitudes vencidas y proximas a vencer.

    Solo incluye solicitudes en estados 'En Estudio' o 'Enviada'.
    Si el usuario no es admin, filtra a solo sus solicitudes.
    """
    hoy = date.today()
    limite_proximas = hoy + timedelta(days=7)

    q = select(Solicitud).where(
        Solicitud.estado.in_(["En Estudio", "Enviada"]),
        Solicitud.fecha_limite.isnot(None),
    )

    # Filtrar por usuario si no es admin
    if current_user.rol != "admin":
        q = q.where(
            or_(
                Solicitud.comercial == current_user.id,
                Solicitud.tecnico_estudios == current_user.id,
            )
        )

    result = await db.execute(q)
    all_sols = result.scalars().all()

    # Cargar comerciales para label
    comercial_ids = {s.comercial for s in all_sols if s.comercial}
    comerciales_map: dict = {}
    if comercial_ids:
        u_result = await db.execute(select(Usuario).where(Usuario.id.in_(comercial_ids)))
        for u in u_result.scalars().all():
            comerciales_map[u.id] = u.nombre

    vencidas = []
    proximas = []

    for s in all_sols:
        if s.fecha_limite is None:
            continue
        dias = (s.fecha_limite - hoy).days
        item = {
            "id": s.id,
            "codigo": s.codigo,
            "nombre_corto": s.nombre_corto,
            "fecha_limite": s.fecha_limite.isoformat(),
            "dias_a_limite": dias,
            "comercial": comerciales_map.get(s.comercial or "", None) if s.comercial else None,
        }
        if dias < 0:
            vencidas.append(item)
        elif dias <= 7:
            proximas.append(item)

    # Ordenar: vencidas de mas antigua a mas reciente, proximas de mas proxima a mas lejana
    vencidas.sort(key=lambda x: x["dias_a_limite"])
    proximas.sort(key=lambda x: x["dias_a_limite"])

    return {
        "vencidas": vencidas,
        "proximas": proximas,
        "total_vencidas": len(vencidas),
        "total_proximas": len(proximas),
    }


# -- Sprint C: Dashboard extended -------------------------------------

@router.get("/dashboard/extended")
async def get_dashboard_extended(db: AsyncSession = Depends(get_session)):
    """KPIs extendidos: top comerciales, mix actuaciones, heatmap mensual."""
    result = await db.execute(select(Solicitud))
    all_rows = result.scalars().all()

    hoy = date.today()

    # Heatmap: ultimos 12 meses
    heatmap = []
    for i in range(11, -1, -1):
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
        count = sum(
            1 for s in all_rows
            if s.fecha_solicitud and mes_inicio <= s.fecha_solicitud < mes_fin
        )
        heatmap.append({
            "mes": mes_inicio.strftime("%b %Y"),
            "mes_key": mes_inicio.strftime("%Y-%m"),
            "count": count,
        })

    # Top 5 comerciales por oferta adjudicada
    comercial_totales: dict = {}
    for s in all_rows:
        if s.estado == "Adjudicada" and s.comercial and s.oferta:
            comercial_totales[s.comercial] = comercial_totales.get(s.comercial, 0) + s.oferta

    top_ids = sorted(comercial_totales.keys(), key=lambda k: comercial_totales[k], reverse=True)[:5]
    top_comerciales = []
    if top_ids:
        u_result = await db.execute(select(Usuario).where(Usuario.id.in_(top_ids)))
        usuarios_map = {u.id: u for u in u_result.scalars().all()}
        for uid in top_ids:
            u = usuarios_map.get(uid)
            top_comerciales.append({
                "id": uid,
                "nombre": u.nombre if u else uid,
                "iniciales": u.iniciales if u else None,
                "color": u.color if u else None,
                "oferta_total": round(comercial_totales[uid], 2),
            })

    # Mix actuaciones: top 5 por count en solicitudes de los ultimos 12 meses
    # (filtradas por fecha_solicitud); si no hay fecha se incluye igual para
    # no perder datos historicos sin fecha.
    desde_12m = date(hoy.year - 1, hoy.month, 1)
    act_result = await db.execute(
        select(SolicitudActuacion.actuacion_id, func.count().label("cnt"))
        .join(Solicitud, Solicitud.id == SolicitudActuacion.solicitud_id)
        .where(
            or_(
                Solicitud.fecha_solicitud.is_(None),
                Solicitud.fecha_solicitud >= desde_12m,
            )
        )
        .group_by(SolicitudActuacion.actuacion_id)
        .order_by(func.count().desc())
        .limit(5)
    )
    act_rows = act_result.all()
    actuacion_ids = [r[0] for r in act_rows]
    mix_actuaciones = []
    if actuacion_ids:
        ac_result = await db.execute(select(Actuacion).where(Actuacion.id.in_(actuacion_ids)))
        act_map = {a.id: a.nombre for a in ac_result.scalars().all()}
        for aid, cnt in act_rows:
            mix_actuaciones.append({
                "id": aid,
                "nombre": act_map.get(aid, aid),
                "count": cnt,
            })

    return {
        "heatmap": heatmap,
        "top_comerciales": top_comerciales,
        "mix_actuaciones": mix_actuaciones,
    }


@router.get("/pipeline")
async def get_pipeline(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Solicitud))
    all_rows = result.scalars().all()
    columnas = [
        {"estado": "En Estudio", "label": "En Estudio", "color": "#6366f1"},
        {"estado": "Enviada", "label": "Enviada", "color": "#f59e0b"},
        {"estado": "Adjudicada", "label": "Adjudicada", "color": "#10b981"},
        {"estado": "Rechazada", "label": "Rechazada", "color": "#ef4444"},
        {"estado": "Descartada", "label": "Descartada", "color": "#6b7280"},
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
    ofertadas = sum(1 for s in all_rows if s.estado == "Enviada")
    ganadas = sum(1 for s in all_rows if s.estado == "Adjudicada")
    perdidas = sum(1 for s in all_rows if s.estado in ("Rechazada", "Descartada"))
    tasa_conversion = round(ganadas / total, 4) if total > 0 else 0.0
    oferta_total = round(sum(s.oferta or 0 for s in all_rows), 2)

    # Tiempo medio de cierre (dias)
    cerradas = [s for s in all_rows if s.estado in ("Adjudicada", "Rechazada", "Descartada") and s.fecha_solicitud]
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
            if s.estado == "Adjudicada"
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



# -- CRUD completo --------------------------------------------------

class SolicitudCreate(BaseModel):
    nombre_corto: str
    codigo: Optional[str] = None
    poblacion: Optional[str] = None
    estado: str = "En Estudio"
    kanban_column: str = "En Estudio"
    color_estado: str = "#6366f1"
    prioridad: str = "media"
    comercial: Optional[str] = None
    tecnico_estudios: Optional[str] = None
    fecha_solicitud: Optional[date] = None
    fecha_limite: Optional[date] = None
    oferta: Optional[float] = None
    presupuesto: Optional[str] = None
    estudio_direccion: Optional[str] = None
    observaciones: Optional[str] = None
    contactos: Optional[str] = None
    actuaciones: Optional[str] = None
    # Sprint A
    tipo_via: Optional[str] = None
    numero: Optional[str] = None
    cp: Optional[str] = None
    fecha_reunion: Optional[date] = None
    fecha_visita: Optional[date] = None
    fecha_enviado: Optional[date] = None
    fecha_cierre_cliente: Optional[date] = None
    descripcion: Optional[str] = None
    cobertura_pct: Optional[float] = None
    coste: Optional[float] = None
    coeficiente: Optional[float] = None
    margen_pct: Optional[float] = None

class SolicitudUpdate(BaseModel):
    nombre_corto: Optional[str] = None
    poblacion: Optional[str] = None
    estado: Optional[str] = None
    kanban_column: Optional[str] = None
    color_estado: Optional[str] = None
    prioridad: Optional[str] = None
    comercial: Optional[str] = None
    tecnico_estudios: Optional[str] = None
    fecha_solicitud: Optional[date] = None
    fecha_limite: Optional[date] = None
    oferta: Optional[float] = None
    presupuesto: Optional[str] = None
    estudio_direccion: Optional[str] = None
    observaciones: Optional[str] = None
    contactos: Optional[str] = None
    actuaciones: Optional[str] = None
    # Sprint A
    tipo_via: Optional[str] = None
    numero: Optional[str] = None
    cp: Optional[str] = None
    fecha_reunion: Optional[date] = None
    fecha_visita: Optional[date] = None
    fecha_enviado: Optional[date] = None
    fecha_cierre_cliente: Optional[date] = None
    descripcion: Optional[str] = None
    cobertura_pct: Optional[float] = None
    coste: Optional[float] = None
    coeficiente: Optional[float] = None
    margen_pct: Optional[float] = None

import uuid


@router.post("/solicitudes", status_code=201)
async def create_solicitud(
    body: SolicitudCreate,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[Usuario] = Depends(get_current_user),
):
    """Crea una nueva solicitud con validaciones y calculo financiero."""
    now = datetime.utcnow()
    codigo = body.codigo or f"SOL-{now.year}-{str(uuid.uuid4())[:4].upper()}"
    data = body.model_dump(exclude_unset=True)
    data.pop("codigo", None)

    # Validaciones de estado
    estado = data.get("estado", "En Estudio")
    errores_estado = validar_solicitud_para_estado(data, estado)
    if errores_estado:
        raise HTTPException(status_code=422, detail={"errors": errores_estado})

    # Validaciones de fechas
    campos_fecha = {k: data.get(k) for k in [
        "fecha_solicitud", "fecha_reunion", "fecha_visita",
        "fecha_enviado", "fecha_cierre_cliente", "fecha_limite",
    ]}
    errores_fechas = validar_fechas(campos_fecha)
    if errores_fechas:
        raise HTTPException(status_code=422, detail={"errors": errores_fechas})

    # Calcular financiero (backend es fuente de verdad)
    fin = calcular_financiero(data.get("oferta"), data.get("coste"))
    data.update(fin)

    s = Solicitud(
        id=str(uuid.uuid4()),
        codigo=codigo,
        aging_dias=0,
        created_at=now,
        **data,
    )
    db.add(s)
    await db.flush()

    # Auditoria
    await registrar_cambios(
        db=db,
        solicitud_id=s.id,
        usuario_id=current_user.id if current_user else None,
        accion="create",
        cambios={},
    )

    await db.commit()
    await db.refresh(s)
    return s

@router.put("/solicitudes/{solicitud_id}")
async def update_solicitud(
    solicitud_id: str,
    body: SolicitudUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[Usuario] = Depends(get_current_user),
):
    """Actualiza cualquier campo de una solicitud con validaciones y calculo financiero."""
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    updates = body.model_dump(exclude_unset=True)

    # Estado a usar para validaciones (el nuevo si se cambia, sino el existente)
    estado = updates.get("estado", s.estado)

    # Construir dict completo con valores actuales + updates para validar
    current_dict: dict = {
        "fecha_solicitud": s.fecha_solicitud,
        "fecha_reunion": s.fecha_reunion,
        "fecha_visita": s.fecha_visita,
        "fecha_enviado": s.fecha_enviado,
        "fecha_cierre_cliente": s.fecha_cierre_cliente,
        "fecha_limite": s.fecha_limite,
        "oferta": s.oferta,
        "coste": s.coste,
    }
    merged = {**current_dict, **updates}

    # Validaciones de estado
    errores_estado = validar_solicitud_para_estado(merged, estado)
    if errores_estado:
        raise HTTPException(status_code=422, detail={"errors": errores_estado})

    # Validaciones de fechas
    errores_fechas = validar_fechas({k: merged.get(k) for k in [
        "fecha_solicitud", "fecha_reunion", "fecha_visita",
        "fecha_enviado", "fecha_cierre_cliente", "fecha_limite",
    ]})
    if errores_fechas:
        raise HTTPException(status_code=422, detail={"errors": errores_fechas})

    # Calcular financiero
    oferta = updates.get("oferta", s.oferta)
    coste = updates.get("coste", s.coste)
    fin = calcular_financiero(oferta, coste)
    updates.update(fin)

    # Registrar cambios para auditoria
    cambios: dict = {}
    for field, new_val in updates.items():
        old_val = getattr(s, field, None)
        if old_val != new_val:
            cambios[field] = (old_val, new_val)

    for field, value in updates.items():
        setattr(s, field, value)
    s.updated_at = datetime.utcnow()
    await db.flush()

    if cambios:
        await registrar_cambios(
            db=db,
            solicitud_id=solicitud_id,
            usuario_id=current_user.id if current_user else None,
            accion="update",
            cambios=cambios,
        )

    await db.commit()
    await db.refresh(s)
    return s

@router.delete("/solicitudes/{solicitud_id}", status_code=204)
async def delete_solicitud(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[Usuario] = Depends(get_current_user),
):
    """Elimina una solicitud."""
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Auditoria antes de borrar
    await registrar_cambios(
        db=db,
        solicitud_id=solicitud_id,
        usuario_id=current_user.id if current_user else None,
        accion="delete",
        cambios={},
    )
    await db.flush()

    await db.delete(s)
    await db.commit()


# =====================================================================
# Sprint A: Contactos por solicitud
# =====================================================================

CONTACTO_TIPOS = {
    "administracion", "tecnico_obra", "ensena_obra",
    "presidente", "propiedad", "otro",
}


class ContactoCreate(BaseModel):
    tipo: str
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    notas: Optional[str] = None


class ContactoUpdate(BaseModel):
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    notas: Optional[str] = None


class ContactoOut(BaseModel):
    id: str
    solicitud_id: str
    tipo: str
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    notas: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/solicitudes/{solicitud_id}/contactos", response_model=List[ContactoOut])
async def list_contactos(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(SolicitudContacto).where(SolicitudContacto.solicitud_id == solicitud_id)
    )
    return result.scalars().all()


@router.post("/solicitudes/{solicitud_id}/contactos", response_model=ContactoOut, status_code=201)
async def create_contacto(
    solicitud_id: str,
    body: ContactoCreate,
    db: AsyncSession = Depends(get_session),
):
    if body.tipo not in CONTACTO_TIPOS:
        raise HTTPException(status_code=422, detail=f"tipo invalido. Valores: {sorted(CONTACTO_TIPOS)}")
    # Verificar que existe la solicitud
    sol = (await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))).scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    c = SolicitudContacto(
        id=str(_uuid.uuid4()),
        solicitud_id=solicitud_id,
        tipo=body.tipo,
        nombre=body.nombre,
        telefono=body.telefono,
        email=body.email,
        notas=body.notas,
        created_at=datetime.utcnow(),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.put("/contactos/{contacto_id}", response_model=ContactoOut)
async def update_contacto(
    contacto_id: str,
    body: ContactoUpdate,
    db: AsyncSession = Depends(get_session),
):
    c = (await db.execute(select(SolicitudContacto).where(SolicitudContacto.id == contacto_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "tipo" in data and data["tipo"] not in CONTACTO_TIPOS:
        raise HTTPException(status_code=422, detail="tipo invalido")
    for k, v in data.items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/contactos/{contacto_id}", status_code=204)
async def delete_contacto(contacto_id: str, db: AsyncSession = Depends(get_session)):
    c = (await db.execute(select(SolicitudContacto).where(SolicitudContacto.id == contacto_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    await db.delete(c)
    await db.commit()


# =====================================================================
# Sprint A: Catalogo de actuaciones y asignacion N-N
# =====================================================================

class ActuacionOut(BaseModel):
    id: str
    nombre: str
    orden: int
    activo: bool

    class Config:
        from_attributes = True


@router.get("/actuaciones", response_model=List[ActuacionOut])
async def list_actuaciones(db: AsyncSession = Depends(get_session)):
    """Catalogo maestro de actuaciones (las 15 del mockup)."""
    result = await db.execute(
        select(Actuacion).where(Actuacion.activo == True).order_by(Actuacion.orden)
    )
    return result.scalars().all()


class SolicitudActuacionOut(BaseModel):
    """Representacion de una actuacion asignada a una solicitud."""
    actuacion_id: str
    actuacion_nombre: str
    m2: Optional[float] = None
    importe: Optional[float] = None


@router.get(
    "/solicitudes/{solicitud_id}/actuaciones",
    response_model=List[SolicitudActuacionOut],
)
async def list_solicitud_actuaciones(
    solicitud_id: str, db: AsyncSession = Depends(get_session)
):
    """Actuaciones asignadas a una solicitud con m2/importe por linea."""
    q = (
        select(SolicitudActuacion, Actuacion)
        .join(Actuacion, Actuacion.id == SolicitudActuacion.actuacion_id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
        .order_by(Actuacion.orden)
    )
    result = await db.execute(q)
    return [
        SolicitudActuacionOut(
            actuacion_id=sa.actuacion_id,
            actuacion_nombre=ac.nombre,
            m2=sa.m2,
            importe=sa.importe,
        )
        for sa, ac in result.all()
    ]


class ActuacionLineaIn(BaseModel):
    actuacion_id: str
    m2: Optional[float] = None
    importe: Optional[float] = None


class ActuacionAssignBody(BaseModel):
    """Cuerpo del PUT. Acepta el formato nuevo (lineas con m2/importe) o el
    legacy (lista plana de ids) para no romper integraciones existentes."""
    actuaciones: Optional[List[ActuacionLineaIn]] = None
    actuacion_ids: Optional[List[str]] = None

    def normalizar(self) -> List[ActuacionLineaIn]:
        if self.actuaciones is not None:
            return self.actuaciones
        if self.actuacion_ids is not None:
            return [ActuacionLineaIn(actuacion_id=a) for a in self.actuacion_ids]
        return []


@router.put("/solicitudes/{solicitud_id}/actuaciones")
async def set_solicitud_actuaciones(
    solicitud_id: str,
    body: ActuacionAssignBody,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[Usuario] = Depends(get_current_user),
):
    """Upsert del set completo de actuaciones de una solicitud.

    Acepta tanto el formato nuevo `{actuaciones: [{actuacion_id, m2, importe}]}`
    como el legacy `{actuacion_ids: [...]}` para retrocompatibilidad. Registra
    el cambio en audit_log con accion='actuaciones_update'.
    """
    import json as _json

    sol = (
        await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    ).scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    lineas = body.normalizar()
    ids_pedidos = [linea.actuacion_id for linea in lineas]

    if ids_pedidos:
        existentes = await db.execute(
            select(Actuacion.id, Actuacion.nombre).where(
                Actuacion.id.in_(ids_pedidos)
            )
        )
        rows = existentes.all()
        nombres_catalogo = {row[0]: row[1] for row in rows}
        invalidas = set(ids_pedidos) - set(nombres_catalogo.keys())
        if invalidas:
            raise HTTPException(
                status_code=422,
                detail=f"Actuaciones no validas: {sorted(invalidas)}",
            )
    else:
        nombres_catalogo = {}

    # Estado anterior (para audit log) con nombres del catalogo.
    previo_q = await db.execute(
        select(SolicitudActuacion, Actuacion)
        .join(Actuacion, Actuacion.id == SolicitudActuacion.actuacion_id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
    )
    previo_rows = previo_q.all()
    anterior_resumen = [
        {
            "actuacion_id": sa.actuacion_id,
            "nombre": ac.nombre,
            "m2": sa.m2,
            "importe": sa.importe,
        }
        for sa, ac in previo_rows
    ]

    # Upsert: borra las que ya no estan, inserta/actualiza las pedidas.
    previas_map = {sa.actuacion_id: sa for sa, _ in previo_rows}
    ids_pedidos_set = set(ids_pedidos)
    ids_previos_set = set(previas_map.keys())

    # Borrar las que sobran.
    for aid_borrar in ids_previos_set - ids_pedidos_set:
        await db.delete(previas_map[aid_borrar])

    # Insertar o actualizar las pedidas.
    for linea in lineas:
        prev = previas_map.get(linea.actuacion_id)
        if prev is not None:
            prev.m2 = linea.m2
            prev.importe = linea.importe
            db.add(prev)
        else:
            db.add(
                SolicitudActuacion(
                    solicitud_id=solicitud_id,
                    actuacion_id=linea.actuacion_id,
                    m2=linea.m2,
                    importe=linea.importe,
                    created_at=datetime.utcnow(),
                )
            )

    await db.flush()

    nuevo_resumen = [
        {
            "actuacion_id": linea.actuacion_id,
            "nombre": nombres_catalogo.get(linea.actuacion_id, linea.actuacion_id),
            "m2": linea.m2,
            "importe": linea.importe,
        }
        for linea in lineas
    ]

    # Auditoria: una sola fila con accion='actuaciones_update'.
    if anterior_resumen != nuevo_resumen:
        from app.core.models import AuditLog as _AuditLog
        import uuid as _uuid

        db.add(
            _AuditLog(
                id=str(_uuid.uuid4()),
                solicitud_id=solicitud_id,
                usuario_id=current_user.id if current_user else None,
                accion="actuaciones_update",
                campo="actuaciones",
                valor_anterior=_json.dumps(anterior_resumen, default=str),
                valor_nuevo=_json.dumps(nuevo_resumen, default=str),
                created_at=datetime.utcnow(),
            )
        )

    await db.commit()
    return {
        "solicitud_id": solicitud_id,
        "actuaciones": nuevo_resumen,
    }


# =====================================================================
# Sprint D bloque C: PDF de oferta
# =====================================================================

_ESTADOS_OFERTA_PDF = {"Enviada", "Adjudicada"}


@router.get("/solicitudes/{solicitud_id}/oferta.pdf")
async def descargar_oferta_pdf(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Genera y descarga el PDF de oferta de una solicitud.

    Solo disponible si la solicitud esta en estado 'Enviada' o 'Adjudicada'.
    """
    from fastapi import Response
    from app.services.pdf_oferta import generar_pdf_oferta

    s = (
        await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    ).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if s.estado not in _ESTADOS_OFERTA_PDF:
        raise HTTPException(
            status_code=400,
            detail=(
                f"La oferta PDF solo se puede generar en estados "
                f"{sorted(_ESTADOS_OFERTA_PDF)}; estado actual: {s.estado}"
            ),
        )

    actuaciones_q = await db.execute(
        select(SolicitudActuacion, Actuacion.nombre)
        .join(Actuacion, Actuacion.id == SolicitudActuacion.actuacion_id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
        .order_by(Actuacion.orden)
    )
    actuaciones = [(sa, nombre) for sa, nombre in actuaciones_q.all()]

    pdf_bytes = generar_pdf_oferta(s, actuaciones, current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="oferta_{s.codigo}.pdf"',
        },
    )


# =====================================================================
# Sprint D bloque C: Recordatorios mailto para admin
# =====================================================================


@router.get("/alertas/recordatorio/{solicitud_id}")
async def alerta_recordatorio_mailto(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("admin")),
):
    """Devuelve asunto, cuerpo y mailto_url prerellenado para un recordatorio.

    El admin abre su cliente de correo con `window.location.href = mailto_url`
    y elige el destinatario. No se envia nada desde el servidor.
    """
    import os
    import urllib.parse as _urlparse

    s = (
        await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    ).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    hoy = date.today()
    dias = (
        (s.fecha_limite - hoy).days if s.fecha_limite else None
    )
    if dias is None:
        situacion = "sin fecha limite asignada"
        asunto = f"[Vedisa] Recordatorio: {s.codigo}"
    elif dias < 0:
        situacion = f"vencida hace {abs(dias)} dias"
        asunto = f"[Vedisa] Recordatorio: {s.codigo} vencida hace {abs(dias)} dias"
    else:
        situacion = f"vence en {dias} dias"
        asunto = f"[Vedisa] Recordatorio: {s.codigo} vence en {dias} dias"

    public_url = os.environ.get("APP_PUBLIC_URL", "http://localhost").rstrip("/")
    enlace = f"{public_url}/?solicitud={s.id}"

    cuerpo_lineas = [
        "Hola,",
        "",
        "Te escribo para recordarte el estado de la siguiente solicitud:",
        "",
        f"  Codigo: {s.codigo}",
        f"  Nombre: {s.nombre_corto}",
        f"  Estado: {s.estado}",
        f"  Fecha limite: {s.fecha_limite.isoformat() if s.fecha_limite else '-'}",
        f"  Situacion: {situacion}",
        "",
        f"Detalle en el CRM: {enlace}",
        "",
        "Gracias,",
        f"{current_user.nombre}",
    ]
    cuerpo = "\n".join(cuerpo_lineas)

    mailto_url = (
        "mailto:?"
        f"subject={_urlparse.quote(asunto)}"
        f"&body={_urlparse.quote(cuerpo)}"
    )

    return {
        "asunto": asunto,
        "cuerpo": cuerpo,
        "mailto_url": mailto_url,
        "dias_a_limite": dias,
    }


# =====================================================================
# Sprint A: Usuarios (lectura + actualizacion de metadatos)
# =====================================================================

class UsuarioOut(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    activo: bool
    equipo: Optional[str] = None
    iniciales: Optional[str] = None
    color: Optional[str] = None
    cargo: Optional[str] = None

    class Config:
        from_attributes = True


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    equipo: Optional[str] = None
    iniciales: Optional[str] = None
    color: Optional[str] = None
    cargo: Optional[str] = None


USUARIO_EQUIPOS = {"comercial", "estudios", "direccion", "administracion"}


@router.get("/usuarios", response_model=List[UsuarioOut])
async def list_usuarios(
    activo: Optional[bool] = None,
    equipo: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    """Lista usuarios. Util para selects de comercial/tecnico en el frontend."""
    q = select(Usuario)
    if activo is not None:
        q = q.where(Usuario.activo == activo)
    if equipo:
        q = q.where(Usuario.equipo == equipo)
    q = q.order_by(Usuario.nombre)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/usuarios/{usuario_id}", response_model=UsuarioOut)
async def get_usuario(usuario_id: str, db: AsyncSession = Depends(get_session)):
    u = (await db.execute(select(Usuario).where(Usuario.id == usuario_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return u


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioOut)
async def update_usuario(
    usuario_id: str,
    body: UsuarioUpdate,
    db: AsyncSession = Depends(get_session),
    _: Usuario = Depends(require_role("admin")),
):
    """Actualiza metadatos (equipo, iniciales, color, cargo, activo). No toca password. Solo admin."""
    u = (await db.execute(select(Usuario).where(Usuario.id == usuario_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "equipo" in data and data["equipo"] is not None and data["equipo"] not in USUARIO_EQUIPOS:
        raise HTTPException(status_code=422, detail=f"equipo invalido. Valores: {sorted(USUARIO_EQUIPOS)}")
    for k, v in data.items():
        setattr(u, k, v)
    u.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(u)
    return u


class UsuarioPasswordBody(BaseModel):
    password: str
    email: Optional[str] = None  # opcional: corregir email del placeholder


@router.post("/usuarios/{usuario_id}/password", response_model=UsuarioOut)
async def set_usuario_password(
    usuario_id: str,
    body: UsuarioPasswordBody,
    db: AsyncSession = Depends(get_session),
    _: Usuario = Depends(require_role("admin")),
):
    """Asigna password real a un usuario (tipico para activar placeholder).

    Solo admin. Si se proporciona email, se actualiza el email tambien (util para
    cambiar el placeholder@vedisa.local por el email real). Activa el usuario.
    """
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="password debe tener al menos 6 caracteres")
    u = (await db.execute(select(Usuario).where(Usuario.id == usuario_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if body.email and body.email != u.email:
        # Verificar que el nuevo email no este en uso
        other = (await db.execute(
            select(Usuario).where(Usuario.email == body.email, Usuario.id != usuario_id)
        )).scalar_one_or_none()
        if other:
            raise HTTPException(status_code=409, detail="Email ya en uso por otro usuario")
        u.email = body.email
    u.hashed_password = hash_password(body.password)
    u.activo = True
    u.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(u)
    return u


class UsuarioCreateBody(BaseModel):
    email: str
    nombre: str
    password: str
    rol: str = "comercial"
    equipo: Optional[str] = None
    iniciales: Optional[str] = None
    color: Optional[str] = None
    cargo: Optional[str] = None
    activo: bool = True


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
async def create_usuario(
    body: UsuarioCreateBody,
    db: AsyncSession = Depends(get_session),
    _: Usuario = Depends(require_role("admin")),
):
    """Crea un nuevo usuario. Solo admin."""
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="password debe tener al menos 6 caracteres")
    if body.equipo and body.equipo not in USUARIO_EQUIPOS:
        raise HTTPException(status_code=422, detail=f"equipo invalido. Valores: {sorted(USUARIO_EQUIPOS)}")
    existing = (await db.execute(select(Usuario).where(Usuario.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email ya registrado")
    u = Usuario(
        id=str(_uuid.uuid4()),
        email=body.email,
        nombre=body.nombre,
        hashed_password=hash_password(body.password),
        rol=body.rol,
        activo=body.activo,
        equipo=body.equipo,
        iniciales=body.iniciales,
        color=body.color,
        cargo=body.cargo,
        created_at=datetime.utcnow(),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u
