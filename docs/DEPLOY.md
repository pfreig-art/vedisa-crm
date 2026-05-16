# Despliegue en Windows Server (intranet, HTTP plano)

Este documento describe el despliegue del CRM Vedisa en un Windows Server con IIS+ARR como reverse proxy y backend FastAPI ejecutado como Windows Service nativo. No se usa HTTPS porque el sistema solo se sirve por la intranet.

## Pre-requisitos

| Componente | Version recomendada |
|---|---|
| Windows Server | 2019 o 2022 |
| Python | 3.12 (x64, "Add to PATH") |
| Node.js | 22 LTS |
| PostgreSQL | 18 (el servicio se llama `postgresql-x64-18`) |
| IIS | Rol Web-Server con `Web-Static-Content`, `Web-Default-Doc`, `Web-Http-Errors`, `Web-Http-Redirect`, `Web-Mgmt-Console` |
| URL Rewrite Module | https://www.iis.net/downloads/microsoft/url-rewrite |
| Application Request Routing (ARR) | https://www.iis.net/downloads/microsoft/application-request-routing |
| Git para Windows | cualquier reciente |

`win-acme` u otro emisor TLS **no es necesario**: la intranet usa HTTP plano.

Instalacion de IIS y roles (PowerShell admin):

```powershell
Install-WindowsFeature -Name Web-Server, Web-Asp-Net45, Web-Mgmt-Console `
    -IncludeManagementTools
```

Tras instalar URL Rewrite + ARR, **reiniciar IIS** (`iisreset`) o reiniciar el servidor.

## Estructura de carpetas

```
C:\vedisa\crm\
  backend\           # codigo FastAPI
    .env             # variables (NO commiteado)
  frontend\
    dist\            # build estatico (lo sirve IIS)
  deploy\windows\    # scripts PowerShell
  .venv\             # virtualenv del backend
  logs\              # stdout/stderr del servicio (opcional)
  backups\           # dumps pg_dump diarios
```

## Despliegue paso a paso

### 1. Clonar repo

```powershell
mkdir C:\vedisa
cd C:\vedisa
git clone https://github.com/<org>/vedisa-crm.git crm
cd crm
```

### 2. Virtualenv + dependencias backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 3. `.env` del backend

```powershell
copy backend\.env.example backend\.env
notepad backend\.env
```

Variables obligatorias en prod:

- `DATABASE_URL=postgresql+asyncpg://vedisa_app:CLAVE@localhost:5432/vedisa_crm`
- `SECRET_KEY=` (generar con `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
- `ENVIRONMENT=production`
- `HOST=127.0.0.1`
- `PORT=8081`

Para los backups diarios, ademas:

- `PG_USER=vedisa_app`
- `PGPASSWORD=CLAVE`

### 4. Crear DB y rol Postgres

Ver [MIGRATION_PROD.md](MIGRATION_PROD.md) para el detalle de creacion del rol `vedisa_app` y sus permisos.

### 5. Migraciones Alembic

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

### 6. Build del frontend

```powershell
cd frontend
npm ci
npm run build
cd ..
```

Esto genera `frontend\dist\` que sera el webroot del sitio IIS.

### 7. Instalar el Windows Service del backend

```powershell
# PowerShell como Administrador
.\deploy\windows\install-service.ps1 -InstallPath "C:\vedisa\crm"
Start-Service VedisaCRM-Backend
```

Verifica que el servicio quedo arriba:

```powershell
Get-Service VedisaCRM-Backend
Invoke-WebRequest http://127.0.0.1:8081/healthz | Select-Object -ExpandProperty Content
```

### 8. Configurar IIS + ARR

```powershell
# PowerShell como Administrador
.\deploy\windows\iis\setup-iis.ps1 -InstallPath "C:\vedisa\crm" -Port 80
```

El script valida que IIS, URL Rewrite y ARR esten instalados, habilita el proxy ARR a nivel maquina, crea el App Pool `VedisaCRM` (No Managed Code), crea el sitio `VedisaCRM` apuntando a `frontend\dist\` y copia `web.config`.

### 9. Backups diarios

```powershell
# PowerShell como Administrador
.\deploy\windows\install-backup-task.ps1 -InstallPath "C:\vedisa\crm"
```

Crea la Scheduled Task `VedisaCRM-Backup` que corre `backup.ps1` a las 03:00 con rotacion de 7 dias.

## Verificacion final

| Check | Comando |
|---|---|
| Backend escucha | `Invoke-WebRequest http://127.0.0.1:8081/healthz` -> 200 |
| IIS reverse-proxy | `Invoke-WebRequest http://localhost/healthz` -> 200 (atravesando ARR) |
| SPA carga | navegar a `http://localhost/` desde Edge/Chrome |
| Login funciona | login con usuario seed, ver consola de IIS sin 502 |
| Logs estructurados | `Get-EventLog -LogName Application -Source VedisaCRM-Backend` o stdout del servicio |
| Backup manual | `.\deploy\windows\backup.ps1 -InstallPath "C:\vedisa\crm"` y revisar `C:\vedisa\crm\backups\` |

## Actualizar a una nueva version

```powershell
.\deploy\windows\update-service.ps1 -InstallPath "C:\vedisa\crm"
```

Hace `Stop-Service` -> `git pull` -> `pip install` -> `alembic upgrade head` -> `npm ci && npm run build` -> `Start-Service`.

## Desinstalar el servicio

```powershell
.\deploy\windows\uninstall-service.ps1
```

## Notas operativas

- **Coexistencia con otro CRM en el mismo server**: el otro CRM escucha en 8000. Vedisa escucha en 8081. ARR no rompe el otro sitio mientras el `web.config` viva en el webroot de cada sitio (configuracion por sitio, no global). El proxy global de ARR debe estar habilitado una sola vez.
- **No bypassar HTTPS**: si en el futuro se publica fuera de la intranet, instalar `win-acme` y anadir un binding 443 con redireccion 80 -> 443.
- **Logs**: structlog escribe por stdout; el SCM redirige a `logs\` si se configura `--log-config` en uvicorn. Por defecto van al journal de Application Events.
