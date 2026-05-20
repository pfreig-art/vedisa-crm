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

---

## Paso 7 - Procedimiento real ejecutado (mayo 2026)

La migracion al server de produccion se cerro la noche del 2026-05-19/20 con desviaciones respecto al plan anterior. Esta seccion documenta lo realmente desplegado.

### 7.1 Arquitectura final

| Recurso | Valor |
|---|---|
| Servidor | Windows Server, dos NIC Ethernet (192.168.1.19 y 192.168.1.40), Tailscale 100.88.8.100 |
| Postgres | 18.3, cluster local, puerto 5432 |
| DB | `vedisa_crm` (UTF8 / LC_COLLATE=C / LC_CTYPE=C) |
| Rol app | `vedisa` (con CREATEDB), password en gestor de secretos del operador |
| Backend | `C:\vedisa\crm\backend\`, NSSM `VedisaCRM`, bind `0.0.0.0:8081` |
| Frontend | `C:\vedisa\crm\frontend\dist\`, NSSM `VedisaCRMFrontend`, vite preview en `0.0.0.0:5173` |
| Coexistencia | NSSM `VedisaERP` en puerto 8000 sigue operativo, sin cambios |
| Acceso | LAN-only para usuarios finales. Remoto solo via Tailscale al servidor + Comet del servidor |
| Node | 24.15.0 (LTS); Node 20.18.1 no era suficiente para Vite 8 |

Decisiones clave respecto al plan:

- **Sin IIS / sin ARR**: el frontend se sirve directamente con Vite preview detras de NSSM, no como sitio IIS. Es una simplificacion deliberada para esta fase; si el negocio pide TLS publico se anade un reverse proxy delante.
- **Rol Postgres**: se uso `vedisa` (no `vedisa_app`) para mantener consistencia con la nomenclatura del ERP existente.
- **LAN-only (opcion C)**: tras evaluar exponer el frontend por Tailscale a usuarios, se decidio que los usuarios finales acceden por LAN. Para teletrabajo se entra al servidor por Tailscale y se usa Comet del servidor.

### 7.2 Variables de entorno backend (`C:\vedisa\crm\backend\.env`)

```ini
DATABASE_URL=postgresql+asyncpg://vedisa:<POSTGRES_PASSWORD>@localhost:5432/vedisa_crm
SECRET_KEY=<generada con secrets.token_urlsafe(64)>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
PORT=8081
ENVIRONMENT=production

LLM_PRIMARY_PROVIDER=openrouter
OPENROUTER_API_KEY=<rotar tras migracion>
OPENROUTER_BASE_URL=https://api.perplexity.ai

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=sistema@vedisa.es
SMTP_PASS=<secreto>
SMTP_FROM=sistema@vedisa.es
SMTP_TLS=true

CORS_ORIGINS=["http://localhost","http://localhost:5173","http://127.0.0.1:5173","http://192.168.1.19:5173","http://192.168.1.40:5173","http://100.88.8.100:5173"]
```

El bloque SMTP se reutiliza del ERP. Si en algun momento el ERP rota la password, este `.env` debe actualizarse a la vez.

### 7.3 Variables de entorno frontend (`C:\vedisa\crm\frontend\.env.production`)

```ini
VITE_API_URL=http://192.168.1.19:8081
```

Nota: la URL queda embebida en el bundle al hacer `npm run build`. Si cambia la IP del servidor o el puerto, hay que rebuildear el frontend.

### 7.4 Servicios NSSM

Backend:

```powershell
nssm install VedisaCRM "C:\vedisa\crm\backend\.venv\Scripts\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8081"
nssm set VedisaCRM AppDirectory "C:\vedisa\crm\backend"
nssm set VedisaCRM AppStdout "C:\vedisa\crm\logs\backend.out.log"
nssm set VedisaCRM AppStderr "C:\vedisa\crm\logs\backend.err.log"
nssm set VedisaCRM Start SERVICE_AUTO_START
Start-Service VedisaCRM
```

Frontend (vite preview sirviendo `dist/`):

```powershell
nssm install VedisaCRMFrontend "C:\Program Files\nodejs\node.exe" "C:\vedisa\crm\frontend\node_modules\vite\bin\vite.js preview --host 0.0.0.0 --port 5173"
nssm set VedisaCRMFrontend AppDirectory "C:\vedisa\crm\frontend"
nssm set VedisaCRMFrontend AppStdout "C:\vedisa\crm\logs\frontend.out.log"
nssm set VedisaCRMFrontend AppStderr "C:\vedisa\crm\logs\frontend.err.log"
nssm set VedisaCRMFrontend Start SERVICE_AUTO_START
Start-Service VedisaCRMFrontend
```

### 7.5 Firewall

Dos reglas inbound Domain+Private:

```powershell
New-NetFirewallRule -DisplayName "VEDISA CRM 8081" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8081 -Profile Domain,Private
New-NetFirewallRule -DisplayName "VEDISA CRM 5173" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5173 -Profile Domain,Private
```

### 7.6 Usuarios iniciales

- `admin@vedisa.com` - rol `admin`. Password inicial entregada al operador fuera de banda; se debe rotar tras la primera sesion.
- `corregidor@vedisa.es` - rol `admin`, cargo CEO (Juan Manuel Corregidor). Creado con script PowerShell + bcrypt. INSERT con `ON CONFLICT (email) DO UPDATE` para idempotencia. La password inicial se entrega fuera de banda y se debe rotar tras el primer login.
- 5 placeholders de comerciales con hash `!disabled:...` para que aparezcan en los selectores sin permitir login hasta que se les ponga password real.

El endpoint de login es form-data, no JSON:

```powershell
$form = @{ username = "corregidor@vedisa.es"; password = "<PASSWORD>" }
Invoke-RestMethod -Uri "http://127.0.0.1:8081/auth/login" -Method Post -Body $form
```

### 7.7 Operaciones rutinarias

**Reiniciar backend o frontend tras un deploy:**

```powershell
cd C:\vedisa\crm
git pull
# backend
.\backend\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
Restart-Service VedisaCRM
# frontend (solo si cambia codigo del bundle)
cd frontend
npm install
npm run build
Restart-Service VedisaCRMFrontend
```

**Logs en vivo:**

```powershell
Get-Content C:\vedisa\crm\logs\backend.out.log -Wait -Tail 50
Get-Content C:\vedisa\crm\logs\backend.err.log -Wait -Tail 50
```

**Verificar servicios:**

```powershell
Get-Service VedisaCRM, VedisaCRMFrontend, VedisaERP, postgresql-x64-18
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8000,8081,5173,5432
```

**Acceso de usuarios:**

- LAN: `http://192.168.1.19:5173` (o `192.168.1.40:5173`).
- Remoto: conectar a Tailscale, entrar al servidor (`100.88.8.100`), abrir Comet local del servidor y navegar al CRM por loopback o LAN.

### 7.8 Backup diario

Ver apartado dedicado en `docs/DEPLOY.md` y la Scheduled Task `VedisaCRM-Backup` (Paso 8 abajo).

## Paso 8 - Backup automatico diario

### 8.1 Script `C:\vedisa\scripts\backup_crm.ps1`

```powershell
# Backup diario de vedisa_crm con retencion de 14 dias
$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$dir = "C:\vedisa\backups\db\crm"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir "vedisa_crm_$ts.dump"
$log = Join-Path $dir "backup.log"

# Lee la password Postgres del rol vedisa desde una variable de
# entorno de maquina configurada con setx (no comitear nunca en claro).
$env:PGPASSWORD = [Environment]::GetEnvironmentVariable("VEDISA_CRM_PGPASSWORD", "Machine")
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
    -U vedisa -h localhost -d vedisa_crm -F c -f $out 2>> $log
$env:PGPASSWORD = $null

if ($LASTEXITCODE -ne 0) {
    Add-Content $log "[$(Get-Date -Format o)] FAIL exit=$LASTEXITCODE"
    exit $LASTEXITCODE
}

$size = (Get-Item $out).Length
Add-Content $log "[$(Get-Date -Format o)] OK $out size=$size"

# Retencion 14 dias
Get-ChildItem $dir -Filter "vedisa_crm_*.dump" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
    Remove-Item -Force
```

### 8.2 Registrar Scheduled Task `VedisaCRM-Backup` a las 03:15

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\vedisa\scripts\backup_crm.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 03:15
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "VedisaCRM-Backup" `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
```

03:15 deliberadamente desfasado del ERP (que corre a 03:00) para no saturar Postgres.

### 8.3 Restore desde un dump

```powershell
$env:PGPASSWORD = [Environment]::GetEnvironmentVariable("VEDISA_CRM_PGPASSWORD", "Machine")
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" `
    -U vedisa -h localhost -d vedisa_crm `
    --clean --if-exists --no-owner --role=vedisa `
    "C:\vedisa\backups\db\crm\vedisa_crm_<TS>.dump"
$env:PGPASSWORD = $null
```

Antes de un restore destructivo, parar el backend para que no haya conexiones activas: `Stop-Service VedisaCRM`. Re-arrancar al terminar: `Start-Service VedisaCRM`.

## Apendice - Secretos a rotar tras migracion

Durante la migracion algunos secretos quedaron escritos en historial de PowerShell, logs de despliegue y conversaciones. Rotar lo antes posible:

- `OPENROUTER_API_KEY` en `backend\.env` (revocar la actual en el panel del proveedor y emitir una nueva).
- Password del usuario CEO (`corregidor@vedisa.es`): forzar cambio en el primer login.
- Password del usuario admin (`admin@vedisa.com`): rotar tras handover.
- Password Postgres del rol `vedisa` si se sospecha exposicion: `ALTER ROLE vedisa WITH PASSWORD '<NUEVA>';` y actualizar `backend\.env` + variable de entorno `VEDISA_CRM_PGPASSWORD` usada por el backup.

## Apendice - Incidencias post-migracion resueltas (2026-05-19/20)

Validacion visual via Comet del servidor detecto 8 incidencias, todas resueltas en la misma noche:

1. Drawer IA arrancaba sin contexto operativo - fix en `frontend/src/stores/aiStore.ts` (preservar context cuando `openDrawer` se llama sin payload).
2. Settings mostraba OpenAI como provider activo en vez de OpenRouter - fix en `backend/app/services/llm_router.py::available_providers` (devolver `is_default`/`is_fallback`/`model`) + `frontend/src/pages/Settings.tsx` (map dinamico).
3. Donut "Mix actuaciones" salia vacio en dashboard - era data real (0 lineas en `solicitud_actuaciones`); se mejoro el empty state con instrucciones al usuario.
4. Listado mostraba 11 solicitudes y kanban solo 10 - una solicitud tenia estado `Ganada` (no es estado valido del modelo); `UPDATE solicitudes SET estado='Adjudicada' WHERE estado='Ganada'`.
5. Footer mostraba `v0.2.0 - Sprint C` desactualizado - bump a `v0.3.0 - Sprint E` en `App.tsx`.
6. Sidebar mostraba "Contactos" apuntando a `/contacts` - renombrado a "Solicitudes" con ruta `/solicitudes` y redirect de `/contacts`.
7. Columna Comercial del kanban mostraba UUID en vez de nombre - fix en `PipelineBoard.tsx` resolviendo via `useUsuariosMap` y propagando `usuariosMap` a `Column` y `SolicitudCard`.
8. Primer login tardaba 7-8s (cold start del worker uvicorn + bcrypt) - warmup en `main.py::lifespan` que hace un `hash_password` + `verify_password` al arrancar, dejando los siguientes logins en ~250ms.
