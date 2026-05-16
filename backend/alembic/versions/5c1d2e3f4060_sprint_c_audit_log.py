"""Sprint C: tabla audit_log para auditoria de cambios en solicitudes.

Revision ID: 5c1d2e3f4060
Revises: 4b1c2d3e4f50
Create Date: 2026-05-16 14:30:00.000000

Idempotente: detecta si la tabla ya existe (creada por SQLModel.metadata.create_all
en el initial schema) y la salta. Esto reproduce el patron del initial migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c1d2e3f4060'
down_revision = '4b1c2d3e4f50'
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_index(bind, table: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    try:
        existing = {ix["name"] for ix in inspector.get_indexes(table)}
    except sa.exc.NoSuchTableError:
        return False
    return index_name in existing


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("solicitud_id", sa.String(), nullable=False),
            sa.Column("usuario_id", sa.String(), nullable=True),
            sa.Column("accion", sa.String(), nullable=False),
            sa.Column("campo", sa.String(), nullable=True),
            sa.Column("valor_anterior", sa.String(), nullable=True),
            sa.Column("valor_nuevo", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["solicitud_id"], ["solicitudes.id"]),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index(bind, "audit_log", "ix_audit_log_solicitud_id"):
        op.create_index(
            "ix_audit_log_solicitud_id", "audit_log", ["solicitud_id"], unique=False
        )
    if not _has_index(bind, "audit_log", "ix_audit_log_created_at"):
        op.create_index(
            "ix_audit_log_created_at", "audit_log", ["created_at"], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "audit_log", "ix_audit_log_created_at"):
        op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    if _has_index(bind, "audit_log", "ix_audit_log_solicitud_id"):
        op.drop_index("ix_audit_log_solicitud_id", table_name="audit_log")
    if _has_table(bind, "audit_log"):
        op.drop_table("audit_log")
