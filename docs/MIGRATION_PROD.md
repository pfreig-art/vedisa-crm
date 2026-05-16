# Migracion de dev local a Postgres compartido en Windows Server

Este documento describe como mover los datos del CRM Vedisa desde el entorno de desarrollo (SQLite o Postgres local) al cluster Postgres compartido del Windows Server, conviviendo con otro CRM ya desplegado.

## Modelo de aislamiento

| Recurso | Otro CRM | Vedisa |
|---|---|---|
| Database | (existente) | **`vedisa_crm`** (nueva) |
| Rol de aplicacion | (existente) | **`vedisa_app`** (nuevo) |
| Puerto backend | 8000 | **8081** |
| Webroot IIS | (existente) | `C:\vedisa\crm\frontend\dist` |

El aislamiento es **a nivel de base de datos** dentro del mismo cluster. El rol `vedisa_app` solo tiene grants sobre `vedisa_crm`, y el rol del otro CRM no recibe ningun grant nuevo. Postgres impide cross-database queries salvo via `dblink`/FDW, que no se habilitaran.

## Paso 1 - Dump del entorno actual

### Si dev usa SQLite (`vedisa_dev.db`)

Usa Alembic en el server contra una DB vacia y aliementa con un seed/import en CSV:

```bash
# en dev local
sqlite3 backend/vedisa_dev.db ".dump" > vedisa_dump.sql
# revisar a mano el .sql; SQLite y Postgres difieren en tipos y AUTOINCREMENT
```

Recomendado: usar las migraciones Alembic para crear el esquema en `vedisa_crm` y reseedar con un script Python que lea SQLite y escriba en Postgres.

### Si dev ya usa Postgres

```bash
pg_dump -h <dev-host> -U <dev-user> -d <dev-db> -F c -f vedisa_dev.dump
```

Transferir `vedisa_dev.dump` al server (`C:\vedisa\restore\`).

## Paso 2 - Crear DB y rol en el server

Como `postgres` (superuser) en el server:

```sql
-- Crear rol de aplicacion con password
CREATE ROLE vedisa_app WITH LOGIN PASSWORD '<PASSWORD_FUERTE>';

-- Crear DB de la que vedisa_app es owner
CREATE DATABASE vedisa_crm WITH OWNER = vedisa_app ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'C' TEMPLATE = template0;

-- Bloquear que otros roles toquen la DB
REVOKE ALL ON DATABASE vedisa_crm FROM PUBLIC;
GRANT  CONNECT ON DATABASE vedisa_crm TO vedisa_app;
```

Aislamiento explicito vs el rol del otro CRM (supongamos que se llama `othercrm_app`):

```sql
-- En psql conectado a vedisa_crm
REVOKE ALL ON SCHEMA public FROM othercrm_app;
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM othercrm_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM othercrm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM othercrm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM othercrm_app;
```

Y simetricamente, asegurarse de que `vedisa_app` **no** tiene permisos sobre la DB del otro CRM (no ejecutar ningun `GRANT` a esa DB para `vedisa_app`).

## Paso 3 - Aplicar el esquema con Alembic

En el server, una vez creada `vedisa_crm` y configurado `backend\.env`:

```powershell
cd C:\vedisa\crm\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Esto crea todas las tablas del CRM Vedisa dentro de `vedisa_crm`, propiedad de `vedisa_app`.

## Paso 4 - Restaurar datos

### Desde un dump custom de Postgres

```powershell
pg_restore --no-owner --role=vedisa_app -h localhost -U vedisa_app -d vedisa_crm `
    --data-only --disable-triggers C:\vedisa\restore\vedisa_dev.dump
```

Usar `--data-only` porque el esquema ya esta creado por Alembic. `--no-owner --role=vedisa_app` re-mapea ownership al rol de prod.

### Desde SQL plano (`pg_dump -F p` o conversion desde SQLite)

```powershell
psql -h localhost -U vedisa_app -d vedisa_crm -f C:\vedisa\restore\vedisa_dump.sql
```

## Paso 5 - Copia del repo y build

Ver [DEPLOY.md](DEPLOY.md), seccion "Despliegue paso a paso".

## Paso 6 - Validar coexistencia con el otro CRM

1. **Puertos**: `Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 80, 443, 8000, 8081, 5432` debe mostrar 8000 (otro CRM), 8081 (Vedisa), 80 (IIS), 5432 (Postgres).
2. **Sitios IIS**: `Get-Website` debe listar los dos sitios sin conflicto de binding. Si ambos usan puerto 80, distinguir por host header o subdominio.
3. **ARR**: el proxy ARR es global pero las reglas viven en cada `web.config` del sitio. Cambiar el `web.config` de Vedisa **no** afecta las reglas del otro CRM.
4. **Postgres**: conectarse como `vedisa_app` y verificar que `\l` lista ambas DBs pero `\c othercrm_db` falla con `permission denied`. Conectarse como `othercrm_app` y verificar el mismo aislamiento simetrico con `\c vedisa_crm`.
5. **Backups**: ambos CRMs deben tener su propia Scheduled Task y su propio `BackupDir`. Verificar que `VedisaCRM-Backup` no toca dumps del otro CRM.

## Rollback

Si la migracion va mal:

```sql
DROP DATABASE vedisa_crm;
DROP ROLE vedisa_app;
```

El otro CRM no se ve afectado porque no se modifico ninguno de sus objetos.

## Riesgos conocidos

- **Colision de puertos**: si el otro CRM expande a 8081 en el futuro, Vedisa rompe. Documentar en el inventario de servicios.
- **Backups concurrentes**: si la Scheduled Task del otro CRM corre a las 03:00, el IO simultaneo puede degradar Postgres. Programar Vedisa a las 03:15.
- **ARR global**: si el otro CRM **deshabilita** el proxy global de ARR (`enabled=false`), Vedisa deja de funcionar. Documentar dependencia.
- **shared_buffers / max_connections**: con dos CRMs en el mismo cluster, vigilar saturacion. Limitar `pool_size` del backend Vedisa si hace falta.
