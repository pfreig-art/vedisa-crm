"""initial schema (usuarios, solicitudes, ai_audit_log)

Esta revisión refleja el estado actual de las BBDD ya desplegadas. En
producción la BBDD ya contiene estas tablas y `alembic_version` apunta a
`3a78a4893db7`, por lo que upgrade no debe hacer nada. Para BBDD nuevas
(SQLite local, entornos en blanco), upgrade crea las tablas a partir de los
modelos SQLModel para que el esquema se mantenga en un único sitio.

Revision ID: 3a78a4893db7
Revises:
Create Date: 2026-05-15 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlmodel import SQLModel

# Importa los modelos para registrarlos en SQLModel.metadata.
from app.core import models  # noqa: F401


# Identificadores Alembic
revision: str = "3a78a4893db7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    SQLModel.metadata.drop_all(bind=bind)
