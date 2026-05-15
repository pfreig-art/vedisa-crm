"""CRM API - Solicitudes, Pipeline, Dashboard con datos seed."""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import math

router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────
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
    fecha_solicitud: Optional[str] = None
    fecha_limite: Optional[str] = None
    aging_dias: Optional[int] = None
    oferta: Optional[float] = None

class SolicitudFront(SolicitudItem):
    estudio_direccion: Optional[str] = None
    presupuesto: dict = {}
    contactos: list[ContactoRef] = []
    actuaciones: list[str] = []
    observaciones: Optional[str] = None

class PipelineColumn(BaseModel):
    estado: str
    label: str
    color: str
    count: int
    total_oferta: float
    items: list[SolicitudItem]

class PaginatedSolicitudes(BaseModel):
    items: list[SolicitudItem]
    total: int
    page: int
    size: int
    pages: int

class EstadoTransition(BaseModel):
    nuevo_estado: str
    motivo: Optional[str] = None

# ── Seed data ──────────────────────────────────────────────
ESTADO_META = {
    "Pte. Aprobacion": {"color": "#94a3b8", "label": "Pte. Aprobacion"},
    "Aprobado":        {"color": "#22c55e", "label": "Aprobado"},
    "Pte. Visita":     {"color": "#f59e0b", "label": "Pte. Visita"},
    "En Estudio":      {"color": "#3b82f6", "label": "En Estudio"},
    "Enviada":         {"color": "#8b5cf6", "label": "Enviada"},
    "Pte. Cierre":     {"color": "#f97316", "label": "Pte. Cierre"},
    "Adjudicada":      {"color": "#10b981", "label": "Adjudicada"},
    "Rechazado":       {"color": "#ef4444", "label": "Rechazado"},
    "Descartada":      {"color": "#6b7280", "label": "Descartada"},
}

_NOW = datetime.now()

def _d(days_ago: int) -> str:
    return (_NOW - timedelta(days=days_ago)).strftime("%Y-%m-%d")

SEED: list[dict] = [
    {"id":"1","codigo":"SOL-2026-001","nombre_corto":"Nave industrial Pol. Son Castelló","poblacion":"Palma","estado":"En Estudio","prioridad":"alta","comercial":"Marc Ferrer","tecnico_estudios":"Pau Llull","fecha_solicitud":_d(45),"fecha_limite":_d(5),"aging_dias":45,"oferta":128000.0,"estudio_direccion":"Pol. Son Castelló, Nave 14, Palma","contactos":[{"nombre":"Joan Miralles","rol":"Promotor","telefono":"971 123 456","email":"joan@miralles.com"}],"actuaciones":["Visita tecnica realizada","Mediciones completadas","Esperando aprobacion presupuesto"]},
    {"id":"2","codigo":"SOL-2026-002","nombre_corto":"Reforma oficinas C/ Blanquerna","poblacion":"Palma","estado":"Enviada","prioridad":"media","comercial":"Sara Vidal","tecnico_estudios":"Pau Llull","fecha_solicitud":_d(30),"fecha_limite":_d(10),"aging_dias":30,"oferta":45000.0,"estudio_direccion":"C/ Blanquerna 22, Palma","contactos":[{"nombre":"Ana Gomez","rol":"Arquitecta","telefono":"971 234 567","email":"ana@gomez.es"}],"actuaciones":["Propuesta enviada","Revisando condiciones"]},
    {"id":"3","codigo":"SOL-2026-003","nombre_corto":"Hotel boutique Soller","poblacion":"Soller","estado":"Adjudicada","prioridad":"alta","comercial":"Marc Ferrer","tecnico_estudios":"Marta Pons","fecha_solicitud":_d(60),"fecha_limite":_d(-5),"aging_dias":60,"oferta":320000.0,"estudio_direccion":"C/ Gran Via 8, Soller","contactos":[{"nombre":"Peter Schmidt","rol":"Propietario","telefono":"+34 971 345 678","email":"peter@hotelsoller.com"}],"actuaciones":["Contrato firmado","Inicio obras previsto 01/06/2026"]},
    {"id":"4","codigo":"SOL-2026-004","nombre_corto":"Vivienda unifamiliar Llucmajor","poblacion":"Llucmajor","estado":"Pte. Visita","prioridad":"baja","comercial":"Sara Vidal","tecnico_estudios":None,"fecha_solicitud":_d(10),"fecha_limite":_d(20),"aging_dias":10,"oferta":None,"estudio_direccion":"Urbanitzacio Bellavista, Llucmajor","contactos":[{"nombre":"Familia Torres","rol":"Cliente","telefono":"666 111 222","email":"torres@gmail.com"}],"actuaciones":["Primera llamada realizada","Visita pendiente de confirmar"]},
    {"id":"5","codigo":"SOL-2026-005","nombre_corto":"Centro comercial Inca fase 2","poblacion":"Inca","estado":"Pte. Aprobacion","prioridad":"alta","comercial":"Marc Ferrer","tecnico_estudios":"Pau Llull","fecha_solicitud":_d(5),"fecha_limite":_d(30),"aging_dias":5,"oferta":580000.0,"estudio_direccion":"Pol. Industrial Inca, Sector 3","contactos":[{"nombre":"GestCom SL","rol":"Promotora","telefono":"971 456 789","email":"obras@gestcom.es"}],"actuaciones":["Solicitud recibida","En revision inicial"]},
    {"id":"6","codigo":"SOL-2026-006","nombre_corto":"Rehabilitacion edificio Sineu","poblacion":"Sineu","estado":"Rechazado","prioridad":"media","comercial":"Sara Vidal","tecnico_estudios":"Marta Pons","fecha_solicitud":_d(90),"fecha_limite":_d(60),"aging_dias":90,"oferta":95000.0,"estudio_direccion":"Placa Major 3, Sineu","contactos":[{"nombre":"Ajuntament Sineu","rol":"Administracion","telefono":"971 520 001","email":"obres@sineu.cat"}],"actuaciones":["Oferta presentada","Rechazada por presupuesto"]},
    {"id":"7","codigo":"SOL-2026-007","nombre_corto":"Piscina y zona exterior Calvia","poblacion":"Calvia","estado":"Aprobado","prioridad":"media","comercial":"Marc Ferrer","tecnico_estudios":None,"fecha_solicitud":_d(15),"fecha_limite":_d(15),"aging_dias":15,"oferta":28000.0,"estudio_direccion":"Urb. Sol de Calvia, Chalet 45","contactos":[{"nombre":"Richard Brown","rol":"Propietario","telefono":"+44 7700 900123","email":"richard@brown.uk"}],"actuaciones":["Visita realizada","Presupuesto aprobado verbalmente"]},
    {"id":"8","codigo":"SOL-2026-008","nombre_corto":"Ampliacion fabrica Manacor","poblacion":"Manacor","estado":"Pte. Cierre","prioridad":"alta","comercial":"Sara Vidal","tecnico_estudios":"Pau Llull","fecha_solicitud":_d(50),"fecha_limite":_d(2),"aging_dias":50,"oferta":215000.0,"estudio_direccion":"Pol. Industrial Manacor, Nave 33","contactos":[{"nombre":"Perlas Orquidea SA","rol":"Cliente","telefono":"971 550 200","email":"compras@orquidea.es"}],"actuaciones":["Negociacion final","Contrato en revision legal"]},
    {"id":"9","codigo":"SOL-2026-009","nombre_corto":"Apartamentos turisticos Alcudia","poblacion":"Alcudia","estado":"En Estudio","prioridad":"alta","comercial":"Marc Ferrer","tecnico_estudios":"Marta Pons","fecha_solicitud":_d(20),"fecha_limite":_d(10),"aging_dias":20,"oferta":175000.0,"estudio_direccion":"Passeig Maritim 78, Alcudia","contactos":[{"nombre":"Inversiones Playa SL","rol":"Promotora","telefono":"971 891 234","email":"info@invplaya.es"}],"actuaciones":["Estudio de viabilidad en curso","Reuniones con arquitecto"]},
    {"id":"10","codigo":"SOL-2026-010","nombre_corto":"Local comercial Mahon","poblacion":"Mahon","estado":"Descartada","prioridad":"baja","comercial":"Sara Vidal","tecnico_estudios":None,"fecha_solicitud":_d(120),"fecha_limite":_d(90),"aging_dias":120,"oferta":12000.0,"estudio_direccion":"C/ Hannover 15, Mahon","contactos":[{"nombre":"Comercial Baleares","rol":"Cliente","telefono":"971 362 111","email":"info@cbaleares.com"}],"actuaciones":["Descartada por cliente"]},
    {"id":"11","codigo":"SOL-2026-011","nombre_corto":"Pabellon deportivo Felanitx","poblacion":"Felanitx","estado":"Enviada","prioridad":"media","comercial":"Marc Ferrer","tecnico_estudios":"Pau Llull","fecha_solicitud":_d(35),"fecha_limite":_d(8),"aging_dias":35,"oferta":95000.0,"estudio_direccion":"C/ Esports s/n, Felanitx","contactos":[{"nombre":"Consell Insular Mallorca","rol":"Administracion","telefono":"971 173 600","email":"obres@conselldemallorca.net"}],"actuaciones":["Oferta enviada","Esperando decision"]},
    {"id":"12","codigo":"SOL-2026-012","nombre_corto":"Restaurante Sa Pobla reforma","poblacion":"Sa Pobla","estado":"Adjudicada","prioridad":"media","comercial":"Sara Vidal","tecnico_estudios":"Marta Pons","fecha_solicitud":_d(40),"fecha_limite":_d(-2),"aging_dias":40,"oferta":67000.0,"estudio_direccion":"Placa Major 12, Sa Pobla","contactos":[{"nombre":"Antoni Crespí","rol":"Propietario","telefono":"671 234 567","email":"toni@restaurantcrespi.com"}],"actuaciones":["Contrato firmado","Materiales pedidos"]},
]

# ── Helpers ──────────────────────────────────────────────
def _to_item(d: dict) -> SolicitudItem:
    return SolicitudItem(
        id=d["id"], codigo=d["codigo"], nombre_corto=d["nombre_corto"],
        poblacion=d.get("poblacion"), estado=d["estado"],
        kanban_column=d["estado"],
        color_estado=ESTADO_META.get(d["estado"], {}).get("color", "#94a3b8"),
        prioridad=d["prioridad"], comercial=d.get("comercial"),
        tecnico_estudios=d.get("tecnico_estudios"),
        fecha_solicitud=d.get("fecha_solicitud"),
        fecha_limite=d.get("fecha_limite"),
        aging_dias=d.get("aging_dias"),
        oferta=d.get("oferta"),
    )

def _to_front(d: dict) -> SolicitudFront:
    item = _to_item(d)
    return SolicitudFront(
        **item.model_dump(),
        estudio_direccion=d.get("estudio_direccion"),
        presupuesto={"oferta": d.get("oferta", 0)},
        contactos=[ContactoRef(**c) for c in d.get("contactos", [])],
        actuaciones=d.get("actuaciones", []),
        observaciones=d.get("observaciones"),
    )

def _filter(items, search, estado, comercial, prioridad):
    out = items
    if search:
        q = search.lower()
        out = [i for i in out if q in i["nombre_corto"].lower()
               or q in i["codigo"].lower()
               or q in (i.get("poblacion") or "").lower()]
    if estado:
        out = [i for i in out if i["estado"] == estado]
    if comercial:
        out = [i for i in out if i.get("comercial") == comercial]
    if prioridad:
        out = [i for i in out if i["prioridad"] == prioridad]
    return out

# ── Endpoints ─────────────────────────────────────────────
@router.get("/solicitudes", response_model=PaginatedSolicitudes)
async def list_solicitudes(
    estado: Optional[str] = Query(None),
    comercial: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    filtered = _filter(SEED, search, estado, comercial, prioridad)
    total = len(filtered)
    pages = max(1, math.ceil(total / size))
    start = (page - 1) * size
    chunk = filtered[start: start + size]
    return PaginatedSolicitudes(
        items=[_to_item(d) for d in chunk],
        total=total, page=page, size=size, pages=pages,
    )

@router.get("/solicitudes/{solicitud_id}", response_model=SolicitudFront)
async def get_solicitud(solicitud_id: str):
    match = next((d for d in SEED if d["id"] == solicitud_id), None)
    if not match:
        raise HTTPException(404, f"Solicitud {solicitud_id} no encontrada")
    return _to_front(match)

@router.get("/solicitudes/{solicitud_id}/context")
async def get_solicitud_context(solicitud_id: str):
    match = next((d for d in SEED if d["id"] == solicitud_id), None)
    if not match:
        raise HTTPException(404, f"Solicitud {solicitud_id} no encontrada")
    return {
        "solicitud_id": solicitud_id,
        "codigo": match["codigo"],
        "nombre": match["nombre_corto"],
        "estado": match["estado"],
        "prioridad": match["prioridad"],
        "comercial": match.get("comercial"),
        "tecnico_estudios": match.get("tecnico_estudios"),
        "poblacion": match.get("poblacion"),
        "oferta": match.get("oferta"),
        "aging_dias": match.get("aging_dias"),
        "contactos": match.get("contactos", []),
        "actuaciones": match.get("actuaciones", []),
        "fechas": {
            "solicitud": match.get("fecha_solicitud"),
            "limite": match.get("fecha_limite"),
        },
    }

@router.patch("/solicitudes/{solicitud_id}/estado")
async def update_estado(solicitud_id: str, transition: EstadoTransition):
    match = next((d for d in SEED if d["id"] == solicitud_id), None)
    if not match:
        raise HTTPException(404, f"Solicitud {solicitud_id} no encontrada")
    match["estado"] = transition.nuevo_estado
    match["kanban_column"] = transition.nuevo_estado
    return {"solicitud_id": solicitud_id, "nuevo_estado": transition.nuevo_estado, "ok": True}

@router.get("/pipeline", response_model=list[PipelineColumn])
async def get_pipeline(
    comercial: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
):
    filtered = _filter(SEED, None, None, comercial, prioridad)
    columns = []
    for estado, meta in ESTADO_META.items():
        items = [d for d in filtered if d["estado"] == estado]
        columns.append(PipelineColumn(
            estado=estado, label=meta["label"], color=meta["color"],
            count=len(items),
            total_oferta=sum(d.get("oferta") or 0 for d in items),
            items=[_to_item(d) for d in items],
        ))
    return columns

@router.get("/dashboard")
async def get_dashboard():
    total = len(SEED)
    en_estudio = sum(1 for d in SEED if d["estado"] == "En Estudio")
    ofertadas = sum(1 for d in SEED if d["estado"] in ("Enviada", "Pte. Cierre"))
    ganadas = sum(1 for d in SEED if d["estado"] == "Adjudicada")
    perdidas = sum(1 for d in SEED if d["estado"] in ("Rechazado", "Descartada"))
    aging_vals = [d["aging_dias"] for d in SEED if d.get("aging_dias")]
    aging_prom = round(sum(aging_vals) / len(aging_vals), 1) if aging_vals else 0
    ofertas = [d["oferta"] for d in SEED if d.get("oferta")]
    oferta_total = sum(ofertas)
    adjudicadas_oferta = sum(d.get("oferta") or 0 for d in SEED if d["estado"] == "Adjudicada")
    rechazadas_oferta = sum(d.get("oferta") or 0 for d in SEED if d["estado"] in ("Rechazado", "Descartada"))
    tasa = round((adjudicadas_oferta / (adjudicadas_oferta + rechazadas_oferta)) * 100, 1) if (adjudicadas_oferta + rechazadas_oferta) > 0 else 0
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
            {"estado": e, "count": sum(1 for d in SEED if d["estado"] == e),
             "total_oferta": sum(d.get("oferta") or 0 for d in SEED if d["estado"] == e),
             "color": m["color"]}
            for e, m in ESTADO_META.items()
        ],
        "comerciales": [
            {"nombre": c, "total": sum(1 for d in SEED if d.get("comercial") == c),
             "adjudicadas": sum(1 for d in SEED if d.get("comercial") == c and d["estado"] == "Adjudicada"),
             "oferta": sum(d.get("oferta") or 0 for d in SEED if d.get("comercial") == c)}
            for c in set(d.get("comercial") for d in SEED if d.get("comercial"))
        ],
    }
