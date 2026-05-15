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

    # --- Asignacion ---
    comercial: Optional[str] = Field(default=None, index=True)
    tecnico_estudios: Optional[str] = Field(default=None)

    # --- Fechas ---
    fecha_solicitud: Optional[date] = Field(default=None)
    fecha_limite: Optional[date] = Field(default=None)

    # --- Financiero ---
    oferta: Optional[float] = Field(default=None)
    presupuesto: Optional[str] = Field(default=None)

    # --- Detalle tecnico ---
    estudio_direccion: Optional[str] = Field(default=None)
    contactos: Optional[str] = Field(default=None)   # JSON serializado
    actuaciones: Optional[str] = Field(default=None)
    observaciones: Optional[str] = Field(default=None)

    # --- Metricas calculadas ---
    aging_dias: Optional[int] = Field(default=None)

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
