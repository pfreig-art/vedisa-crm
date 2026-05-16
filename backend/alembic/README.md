# Alembic — Vedisa CRM

Gestión de migraciones del backend. La revisión inicial `3a78a4893db7` refleja el esquema actual que ya está desplegado en producción (Postgres) y en los entornos locales (SQLite).

## Comandos habituales

Ejecútalos desde `backend/` con el `.env` cargado.

```bash
# Ver historial y estado
alembic current
alembic history

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Crear una nueva migración a partir de cambios en los modelos
alembic revision --autogenerate -m "descripcion"

# Bajar una revisión
alembic downgrade -1
```

## Casos de uso

### BBDD existente con esquema ya creado (producción actual)

La BBDD ya tiene `alembic_version` con `3a78a4893db7` apuntado, así que `alembic upgrade head` no hará nada. No es necesaria ninguna acción extra.

### BBDD existente SIN `alembic_version` (entornos antiguos)

Marca la revisión como aplicada sin tocar el esquema:

```bash
alembic stamp 3a78a4893db7
```

### BBDD nueva (entorno limpio o SQLite local)

```bash
alembic upgrade head
```

Crea las tres tablas (`usuarios`, `solicitudes`, `ai_audit_log`) a partir de `SQLModel.metadata`.

## Notas de implementación

- `env.py` lee la URL desde `app.core.config.settings.DATABASE_URL` y convierte automáticamente `postgresql+asyncpg://` y `sqlite+aiosqlite://` a sus variantes síncronas para que Alembic pueda ejecutar las migraciones.
- Para SQLite se activa `render_as_batch` (necesario para alterar tablas).
- La aplicación ya no usa `SQLModel.metadata.create_all()` al arrancar: el esquema lo gestiona Alembic. Para entornos de desarrollo con SQLite, ejecutar `alembic upgrade head` antes de levantar el backend.
