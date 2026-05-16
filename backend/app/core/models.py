"""SQLModel ORM models for Vedisa CRM."""
from datetime import datetime, date
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------

class Usuario(SQLModel, table=True):
    """Tabla de usuarios / agentes del CRM."""

    __tablename__ = "usuarios"

    id: str = Field(default_factory=_uuid, primary_key=True)
    email: str = Field(unique=True, index=True)
    nombre: str
    hashed_password: str
    rol: str = Field(default="comercial")  # admin | comercial | tecnico
    activo: bool = Field(default=True)

    # --- Sprint A: metadatos de equipo / UI ---
    equipo: Optional[str] = Field(default=None, index=True)
    # comercial | estudios | direccion | administracion
    iniciales: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None)   # hex, ej. #6366f1
    cargo: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# ---------------------------------------------------------------------------
# Solicitud
# ---------------------------------------------------------------------------

class Solicitud(SQLModel, table=True):
    """Solicitud / oportunidad comercial del pipeline."""

    __tablename__ = "solicitudes"

    id: str = Field(default_factory=_uuid, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre_corto: str
    poblacion: Optional[str] = Field(default=None)

    # --- Estado pipeline ---
    estado: str = Field(default="En Estudio", index=True)
    kanban_column: str = Field(default="En Estudio")
    color_estado: str = Field(default="#6366f1")
    prioridad: str = Field(default="media")  # alta | media | baja

    # --- Asignacion (Sprint A: FK -> usuarios) ---
    # Mantenemos las columnas con el mismo nombre, ahora apuntan a usuarios.id
    comercial: Optional[str] = Field(default=None, foreign_key="usuarios.id", index=True)
    tecnico_estudios: Optional[str] = Field(default=None, foreign_key="usuarios.id", index=True)

    # --- Direccion / ubicacion ---
    tipo_via: Optional[str] = Field(default=None)
    numero: Optional[str] = Field(default=None)
    cp: Optional[str] = Field(default=None, index=True)

    # --- Fechas ---
    fecha_solicitud: Optional[date] = Field(default=None)
    fecha_limite: Optional[date] = Field(default=None)
    fecha_reunion: Optional[date] = Field(default=None)
    fecha_visita: Optional[date] = Field(default=None)
    fecha_enviado: Optional[date] = Field(default=None)
    fecha_cierre_cliente: Optional[date] = Field(default=None)

    # --- Financiero ---
    oferta: Optional[float] = Field(default=None)
    presupuesto: Optional[str] = Field(default=None)  # legacy, conservado
    cobertura_pct: Optional[float] = Field(default=None)
    coste: Optional[float] = Field(default=None)
    coeficiente: Optional[float] = Field(default=None)
    margen_pct: Optional[float] = Field(default=None)

    # --- Detalle tecnico ---
    estudio_direccion: Optional[str] = Field(default=None)
    contactos: Optional[str] = Field(default=None)   # JSON legacy
    actuaciones: Optional[str] = Field(default=None) # JSON legacy
    descripcion: Optional[str] = Field(default=None)
    observaciones: Optional[str] = Field(default=None)

    # --- Metricas calculadas ---
    aging_dias: Optional[int] = Field(default=None)

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# ---------------------------------------------------------------------------
# Sprint A: Contactos por solicitud (tabla hija)
# ---------------------------------------------------------------------------

class SolicitudContacto(SQLModel, table=True):
    """Contacto asociado a una solicitud (admin, tecnico de obra, propiedad, etc.)."""

    __tablename__ = "solicitud_contactos"

    id: str = Field(default_factory=_uuid, primary_key=True)
    solicitud_id: str = Field(foreign_key="solicitudes.id", index=True)
    tipo: str = Field(index=True)
    # administracion | tecnico_obra | ensena_obra | presidente | propiedad | otro
    nombre: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    notas: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# ---------------------------------------------------------------------------
# Sprint A: Catalogo de actuaciones + tabla N-N
# ---------------------------------------------------------------------------

class Actuacion(SQLModel, table=True):
    """Catalogo maestro de tipos de actuacion."""

    __tablename__ = "actuaciones"

    id: str = Field(primary_key=True)  # slug, ej. "fachada"
    nombre: str
    orden: int = Field(default=0)
    activo: bool = Field(default=True)


class SolicitudActuacion(SQLModel, table=True):
    """Relacion N-N entre solicitudes y actuaciones."""

    __tablename__ = "solicitud_actuaciones"

    solicitud_id: str = Field(foreign_key="solicitudes.id", primary_key=True)
    actuacion_id: str = Field(foreign_key="actuaciones.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AIAuditLog
# ---------------------------------------------------------------------------
class AIAuditLog(SQLModel, table=True):
    """Registro de auditoria de llamadas al LLM."""
    __tablename__ = "ai_audit_log"

    id: str = Field(default_factory=_uuid, primary_key=True)
    # Identificacion de la llamada
    endpoint: str = Field(index=True)          # analyze | chat | test
    solicitud_id: Optional[str] = Field(default=None, index=True)
    usuario_id: Optional[str] = Field(default=None, index=True)
    # Proveedor / modelo
    provider: str = Field(index=True)
    model: str
    # Metricas
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    latency_ms: int = Field(default=0)
    # Resultado
    success: bool = Field(default=True)
    error_msg: Optional[str] = Field(default=None)
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
