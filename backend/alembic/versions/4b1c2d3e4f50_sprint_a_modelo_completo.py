"""sprint A: modelo de datos completo (mockup)

Cambios (100% aditivos sobre 3a78a4893db7, no destructivos):

- usuarios: anade equipo, iniciales, color, cargo
- solicitudes: anade tipo_via, numero, cp, fecha_reunion, fecha_visita,
  fecha_enviado, fecha_cierre_cliente, descripcion, cobertura_pct, coste,
  coeficiente, margen_pct
- solicitudes: migra comercial / tecnico_estudios de texto libre a FK ->
  usuarios.id. Los valores existentes (nombres) se promocionan: por cada
  nombre distinto se crea (si no existe) un usuario placeholder activo=False
  con email auto-generado y password no usable. Las columnas pasan a contener
  el uuid del usuario correspondiente.
- nuevas tablas: solicitud_contactos, actuaciones, solicitud_actuaciones
- seed: catalogo de 15 actuaciones del mockup

Revision ID: 4b1c2d3e4f50
Revises: 3a78a4893db7
Create Date: 2026-05-16 13:30:00

"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# Identificadores Alembic
revision: str = "4b1c2d3e4f50"
down_revision: Union[str, None] = "3a78a4893db7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Catalogo de actuaciones del mockup
ACTUACIONES = [
    ("accesibilidad", "Accesibilidad", 10),
    ("cubierta", "Cubierta", 20),
    ("estructura", "Estructura", 30),
    ("fachada", "Fachada", 40),
    ("impermeabilizacion", "Impermeabilizacion", 50),
    ("instalaciones", "Instalaciones", 60),
    ("obra_nueva", "Obra nueva", 70),
    ("otras_conservacion", "Otras conservacion", 80),
    ("obras_derivadas_iee", "Obras derivadas IEE", 90),
    ("patios", "Patios", 100),
    ("reforma", "Reforma", 110),
    ("saneamiento_pluviales", "Saneamiento pluviales", 120),
    ("sate", "SATE", 130),
    ("varios", "Varios", 140),
    ("zbcc", "ZBCC", 150),
]


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _slugify(value: str) -> str:
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9]+", ".", v)
    v = v.strip(".")
    return v or "user"


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = _is_sqlite()

    inspector = sa.inspect(bind)

    # ------------------------------------------------------------------
    # 1) usuarios: nuevas columnas
    # ------------------------------------------------------------------
    usuarios_cols = {c["name"] for c in inspector.get_columns("usuarios")}
    with op.batch_alter_table("usuarios") as batch:
        if "equipo" not in usuarios_cols:
            batch.add_column(sa.Column("equipo", sa.String(), nullable=True))
        if "iniciales" not in usuarios_cols:
            batch.add_column(sa.Column("iniciales", sa.String(), nullable=True))
        if "color" not in usuarios_cols:
            batch.add_column(sa.Column("color", sa.String(), nullable=True))
        if "cargo" not in usuarios_cols:
            batch.add_column(sa.Column("cargo", sa.String(), nullable=True))

    # Indice sobre equipo (solo si no existe)
    existing_ix_usuarios = {ix["name"] for ix in inspector.get_indexes("usuarios")}
    if "ix_usuarios_equipo" not in existing_ix_usuarios:
        op.create_index("ix_usuarios_equipo", "usuarios", ["equipo"])

    # ------------------------------------------------------------------
    # 2) solicitudes: nuevas columnas (sin tocar las existentes salvo FK al final)
    # ------------------------------------------------------------------
    sol_cols = {c["name"] for c in inspector.get_columns("solicitudes")}
    new_solicitud_cols = [
        ("tipo_via", sa.String()),
        ("numero", sa.String()),
        ("cp", sa.String()),
        ("fecha_reunion", sa.Date()),
        ("fecha_visita", sa.Date()),
        ("fecha_enviado", sa.Date()),
        ("fecha_cierre_cliente", sa.Date()),
        ("descripcion", sa.Text()),
        ("cobertura_pct", sa.Float()),
        ("coste", sa.Float()),
        ("coeficiente", sa.Float()),
        ("margen_pct", sa.Float()),
    ]
    with op.batch_alter_table("solicitudes") as batch:
        for name, type_ in new_solicitud_cols:
            if name not in sol_cols:
                batch.add_column(sa.Column(name, type_, nullable=True))

    existing_ix_sol = {ix["name"] for ix in inspector.get_indexes("solicitudes")}
    if "ix_solicitudes_cp" not in existing_ix_sol:
        op.create_index("ix_solicitudes_cp", "solicitudes", ["cp"])

    # ------------------------------------------------------------------
    # 3) Promocion comercial/tecnico_estudios -> FK a usuarios.id
    # ------------------------------------------------------------------
    # Estrategia:
    #  a) Recoger valores distintos no-uuid en solicitudes.comercial y .tecnico_estudios
    #  b) Para cada valor: si ya existe usuario por nombre, reusar; si no, crear
    #     usuario placeholder (activo=False, password no usable, email autogenerado).
    #  c) Reemplazar el valor textual por el uuid en solicitudes.
    #  d) En PostgreSQL anadir FK constraints. En SQLite (dev) las FK quedan
    #     declaradas a nivel de modelo pero no se imponen en columnas existentes;
    #     batch_alter_table las recreara cuando aplique.

    uuid_re = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )

    def _is_uuid(s):
        return bool(s and uuid_re.match(s))

    # Recopilar valores distintos
    res = bind.execute(sa.text(
        "SELECT DISTINCT comercial FROM solicitudes "
        "WHERE comercial IS NOT NULL AND comercial <> ''"
    )).fetchall()
    res2 = bind.execute(sa.text(
        "SELECT DISTINCT tecnico_estudios FROM solicitudes "
        "WHERE tecnico_estudios IS NOT NULL AND tecnico_estudios <> ''"
    )).fetchall()

    nombres = {r[0] for r in res} | {r[0] for r in res2}
    nombres = {n for n in nombres if n and not _is_uuid(n)}

    # Mapa nombre -> usuario_id
    name_to_id: dict[str, str] = {}

    # Password placeholder NO usable (hash basura, no es bcrypt -> nunca matchea)
    placeholder_hash = "!disabled!" + hashlib.sha256(b"placeholder").hexdigest()

    for nombre in nombres:
        # Buscar usuario existente por nombre exacto
        row = bind.execute(
            sa.text("SELECT id FROM usuarios WHERE nombre = :n LIMIT 1"),
            {"n": nombre},
        ).fetchone()
        if row:
            name_to_id[nombre] = row[0]
            continue
        # Crear placeholder
        new_id = str(uuid.uuid4())
        slug = _slugify(nombre)
        email = f"{slug}@placeholder.vedisa.local"
        # Evitar colisiones de email
        suffix = 0
        while bind.execute(
            sa.text("SELECT 1 FROM usuarios WHERE email = :e"),
            {"e": email},
        ).fetchone():
            suffix += 1
            email = f"{slug}.{suffix}@placeholder.vedisa.local"

        # Iniciales (primeras letras de cada palabra, max 3)
        partes = [p for p in re.split(r"\s+", nombre) if p]
        iniciales = "".join(p[0].upper() for p in partes[:3]) or nombre[:2].upper()

        bind.execute(
            sa.text(
                "INSERT INTO usuarios "
                "(id, email, nombre, hashed_password, rol, activo, "
                "iniciales, created_at) "
                "VALUES (:id, :email, :nombre, :pwd, :rol, :activo, "
                ":iniciales, :ts)"
            ),
            {
                "id": new_id,
                "email": email,
                "nombre": nombre,
                "pwd": placeholder_hash,
                "rol": "comercial",
                "activo": False,
                "iniciales": iniciales,
                "ts": datetime.utcnow(),
            },
        )
        name_to_id[nombre] = new_id

    # Aplicar reemplazos en solicitudes
    for nombre, uid in name_to_id.items():
        bind.execute(
            sa.text(
                "UPDATE solicitudes SET comercial = :uid "
                "WHERE comercial = :n"
            ),
            {"uid": uid, "n": nombre},
        )
        bind.execute(
            sa.text(
                "UPDATE solicitudes SET tecnico_estudios = :uid "
                "WHERE tecnico_estudios = :n"
            ),
            {"uid": uid, "n": nombre},
        )

    # FK constraints (solo en backends que las soportan en ALTER)
    if not is_sqlite:
        existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("solicitudes")}
        if "fk_solicitudes_comercial_usuarios" not in existing_fks:
            op.create_foreign_key(
                "fk_solicitudes_comercial_usuarios",
                "solicitudes", "usuarios",
                ["comercial"], ["id"],
                ondelete="SET NULL",
            )
        if "fk_solicitudes_tecnico_estudios_usuarios" not in existing_fks:
            op.create_foreign_key(
                "fk_solicitudes_tecnico_estudios_usuarios",
                "solicitudes", "usuarios",
                ["tecnico_estudios"], ["id"],
                ondelete="SET NULL",
            )

    # ------------------------------------------------------------------
    # 4) Tabla solicitud_contactos
    # ------------------------------------------------------------------
    if not inspector.has_table("solicitud_contactos"):
        op.create_table(
            "solicitud_contactos",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("solicitud_id", sa.String(), sa.ForeignKey("solicitudes.id"), nullable=False),
            sa.Column("tipo", sa.String(), nullable=False),
            sa.Column("nombre", sa.String(), nullable=True),
            sa.Column("telefono", sa.String(), nullable=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_solicitud_contactos_solicitud_id", "solicitud_contactos", ["solicitud_id"])
        op.create_index("ix_solicitud_contactos_tipo", "solicitud_contactos", ["tipo"])

    # ------------------------------------------------------------------
    # 5) Tabla actuaciones (catalogo) + seed
    # ------------------------------------------------------------------
    if not inspector.has_table("actuaciones"):
        op.create_table(
            "actuaciones",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("nombre", sa.String(), nullable=False),
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    # Seed idempotente
    for slug, nombre, orden in ACTUACIONES:
        exists = bind.execute(
            sa.text("SELECT 1 FROM actuaciones WHERE id = :id"),
            {"id": slug},
        ).fetchone()
        if not exists:
            bind.execute(
                sa.text(
                    "INSERT INTO actuaciones (id, nombre, orden, activo) "
                    "VALUES (:id, :nombre, :orden, :activo)"
                ),
                {"id": slug, "nombre": nombre, "orden": orden, "activo": True},
            )

    # ------------------------------------------------------------------
    # 6) Tabla solicitud_actuaciones (N-N)
    # ------------------------------------------------------------------
    if not inspector.has_table("solicitud_actuaciones"):
        op.create_table(
            "solicitud_actuaciones",
            sa.Column("solicitud_id", sa.String(), sa.ForeignKey("solicitudes.id"), primary_key=True),
            sa.Column("actuacion_id", sa.String(), sa.ForeignKey("actuaciones.id"), primary_key=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    """Bajada no destructiva: drop solo las tablas/columnas nuevas.

    No revierte la promocion de comercial/tecnico_estudios a uuid (los datos
    originales con nombres ya no existen). Esto es intencional: el downgrade
    deja las columnas existentes intactas para no perder datos.
    """
    bind = op.get_bind()
    is_sqlite = _is_sqlite()
    inspector = sa.inspect(bind)

    # Drop tablas nuevas en orden inverso
    if inspector.has_table("solicitud_actuaciones"):
        op.drop_table("solicitud_actuaciones")
    if inspector.has_table("actuaciones"):
        op.drop_table("actuaciones")
    if inspector.has_table("solicitud_contactos"):
        op.drop_table("solicitud_contactos")

    # Drop FKs si existen (solo no-sqlite)
    if not is_sqlite:
        existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("solicitudes")}
        if "fk_solicitudes_comercial_usuarios" in existing_fks:
            op.drop_constraint(
                "fk_solicitudes_comercial_usuarios", "solicitudes", type_="foreignkey"
            )
        if "fk_solicitudes_tecnico_estudios_usuarios" in existing_fks:
            op.drop_constraint(
                "fk_solicitudes_tecnico_estudios_usuarios", "solicitudes", type_="foreignkey"
            )

    # Drop indices nuevos
    existing_ix_sol = {ix["name"] for ix in inspector.get_indexes("solicitudes")}
    if "ix_solicitudes_cp" in existing_ix_sol:
        op.drop_index("ix_solicitudes_cp", table_name="solicitudes")

    existing_ix_usu = {ix["name"] for ix in inspector.get_indexes("usuarios")}
    if "ix_usuarios_equipo" in existing_ix_usu:
        op.drop_index("ix_usuarios_equipo", table_name="usuarios")

    # Drop columnas anadidas
    drop_solicitud_cols = [
        "tipo_via", "numero", "cp",
        "fecha_reunion", "fecha_visita", "fecha_enviado", "fecha_cierre_cliente",
        "descripcion",
        "cobertura_pct", "coste", "coeficiente", "margen_pct",
    ]
    sol_cols = {c["name"] for c in inspector.get_columns("solicitudes")}
    with op.batch_alter_table("solicitudes") as batch:
        for col in drop_solicitud_cols:
            if col in sol_cols:
                batch.drop_column(col)

    drop_usuario_cols = ["equipo", "iniciales", "color", "cargo"]
    usuarios_cols = {c["name"] for c in inspector.get_columns("usuarios")}
    with op.batch_alter_table("usuarios") as batch:
        for col in drop_usuario_cols:
            if col in usuarios_cols:
                batch.drop_column(col)
