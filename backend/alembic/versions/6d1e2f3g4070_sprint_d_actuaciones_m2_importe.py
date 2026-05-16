"""Sprint D bloque C: anadir m2 e importe a solicitud_actuaciones.

Revision ID: 6d1e2f3g4070
Revises: 5c1d2e3f4060
Create Date: 2026-05-16 18:00:00.000000

Idempotente: detecta si las columnas ya existen (creadas por
SQLModel.metadata.create_all en arranque) y las salta. Mantiene el PK
compuesto (solicitud_id, actuacion_id) — la UNIQUE pedida en el bloque C
ya esta garantizada por ese PK, no se anade un constraint duplicado.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d1e2f3g4070'
down_revision = '5c1d2e3f4060'
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_column(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    try:
        existing = {c["name"] for c in inspector.get_columns(table)}
    except sa.exc.NoSuchTableError:
        return False
    return column in existing


def upgrade() -> None:
    bind = op.get_bind()

    # Si la tabla no existe (caso muy improbable porque Sprint A la creo),
    # salimos sin hacer nada; SQLModel.metadata.create_all la creara con el
    # esquema actualizado.
    if not _has_table(bind, "solicitud_actuaciones"):
        return

    # m2 y importe son los unicos cambios reales del bloque C.
    if not _has_column(bind, "solicitud_actuaciones", "m2"):
        op.add_column(
            "solicitud_actuaciones",
            sa.Column("m2", sa.Float(), nullable=True),
        )
    if not _has_column(bind, "solicitud_actuaciones", "importe"):
        op.add_column(
            "solicitud_actuaciones",
            sa.Column("importe", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "solicitud_actuaciones", "importe"):
        with op.batch_alter_table("solicitud_actuaciones") as batch_op:
            batch_op.drop_column("importe")
    if _has_column(bind, "solicitud_actuaciones", "m2"):
        with op.batch_alter_table("solicitud_actuaciones") as batch_op:
            batch_op.drop_column("m2")
