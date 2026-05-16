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
from app.core.models import (
    Solicitud,
    Usuario,
    SolicitudContacto,
    Actuacion,
    SolicitudActuacion,
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
):
    """Crea una nueva solicitud."""
    now = datetime.utcnow()
    # Auto-generar codigo si no se proporciona
    codigo = body.codigo or f"SOL-{now.year}-{str(uuid.uuid4())[:4].upper()}"
    data = body.model_dump(exclude_unset=True)
    data.pop("codigo", None)
    s = Solicitud(
        id=str(uuid.uuid4()),
        codigo=codigo,
        aging_dias=0,
        created_at=now,
        **data,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s

@router.put("/solicitudes/{solicitud_id}")
async def update_solicitud(
    solicitud_id: str,
    body: SolicitudUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Actualiza cualquier campo de una solicitud."""
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    s.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(s)
    return s

@router.delete("/solicitudes/{solicitud_id}", status_code=204)
async def delete_solicitud(
    solicitud_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Elimina una solicitud."""
    result = await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
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


@router.get("/solicitudes/{solicitud_id}/actuaciones", response_model=List[ActuacionOut])
async def list_solicitud_actuaciones(solicitud_id: str, db: AsyncSession = Depends(get_session)):
    """Actuaciones asignadas a una solicitud."""
    q = (
        select(Actuacion)
        .join(SolicitudActuacion, SolicitudActuacion.actuacion_id == Actuacion.id)
        .where(SolicitudActuacion.solicitud_id == solicitud_id)
        .order_by(Actuacion.orden)
    )
    result = await db.execute(q)
    return result.scalars().all()


class ActuacionAssignBody(BaseModel):
    actuacion_ids: List[str]


@router.put("/solicitudes/{solicitud_id}/actuaciones")
async def set_solicitud_actuaciones(
    solicitud_id: str,
    body: ActuacionAssignBody,
    db: AsyncSession = Depends(get_session),
):
    """Reemplaza el set completo de actuaciones de una solicitud."""
    sol = (await db.execute(select(Solicitud).where(Solicitud.id == solicitud_id))).scalar_one_or_none()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Validar que todos los ids existen en el catalogo
    if body.actuacion_ids:
        existentes = await db.execute(
            select(Actuacion.id).where(Actuacion.id.in_(body.actuacion_ids))
        )
        existentes_set = {row[0] for row in existentes.all()}
        invalidas = set(body.actuacion_ids) - existentes_set
        if invalidas:
            raise HTTPException(status_code=422, detail=f"Actuaciones no validas: {sorted(invalidas)}")

    # Borrar las existentes
    actuales = await db.execute(
        select(SolicitudActuacion).where(SolicitudActuacion.solicitud_id == solicitud_id)
    )
    for sa_row in actuales.scalars().all():
        await db.delete(sa_row)
    await db.flush()

    # Insertar las nuevas
    for aid in body.actuacion_ids:
        db.add(SolicitudActuacion(
            solicitud_id=solicitud_id,
            actuacion_id=aid,
            created_at=datetime.utcnow(),
        ))
    await db.commit()
    return {"solicitud_id": solicitud_id, "actuaciones": body.actuacion_ids}


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
):
    """Actualiza metadatos (equipo, iniciales, color, cargo, activo). No toca password."""
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
