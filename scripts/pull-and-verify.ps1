<#
.SYNOPSIS
    Pull, instala dependencias y verifica el backend Vedisa CRM en Windows.

.DESCRIPTION
    Pasos:
      1. git fetch + checkout + pull de la rama indicada.
      2. Activa (o crea) el venv en backend\.venv.
      3. pip install -r backend\requirements.txt.
      4. alembic current y alembic upgrade head (idempotente).
      5. Health-check del backend si está corriendo en 127.0.0.1:8000.

    Es seguro re-ejecutarlo: no toca datos, Alembic ya está en 3a78a4893db7
    en producción y upgrade head es no-op.

.PARAMETER RepoPath
    Ruta al repositorio. Por defecto C:\vedisa\crm.

.PARAMETER Branch
    Rama a traer. Por defecto fix/e2e-may16.

.PARAMETER BackendUrl
    URL base del backend para el health-check. Por defecto http://127.0.0.1:8000.

.PARAMETER SkipPipInstall
    Salta el pip install (útil si las dependencias no cambiaron).

.PARAMETER SkipAlembic
    Salta los pasos de Alembic.

.EXAMPLE
    .\scripts\pull-and-verify.ps1

.EXAMPLE
    .\scripts\pull-and-verify.ps1 -Branch main -SkipPipInstall
#>

[CmdletBinding()]
param(
    [string]$RepoPath    = 'C:\vedisa\crm',
    [string]$Branch      = 'fix/e2e-may16',
    [string]$BackendUrl  = 'http://127.0.0.1:8000',
    [switch]$SkipPipInstall,
    [switch]$SkipAlembic
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

function Write-Step {
    param([string]$Msg)
    Write-Host ''
    Write-Host "==> $Msg" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Msg)
    Write-Host "    OK   $Msg" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "    WARN $Msg" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Msg)
    Write-Host "    FAIL $Msg" -ForegroundColor Red
}

function Invoke-Native {
    <#
        Ejecuta un comando externo y propaga $LASTEXITCODE como excepción.
        Usar SIEMPRE para invocar git, pip, alembic, etc.
    #>
    param(
        [Parameter(Mandatory)] [string]   $File,
        [Parameter(Mandatory)] [string[]] $Args,
        [string] $WorkingDirectory
    )
    if ($WorkingDirectory) {
        Push-Location $WorkingDirectory
    }
    try {
        & $File @Args
        if ($LASTEXITCODE -ne 0) {
            throw "$File $($Args -join ' ') terminó con código $LASTEXITCODE"
        }
    }
    finally {
        if ($WorkingDirectory) {
            Pop-Location
        }
    }
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encuentra '$Name' en el PATH. Instálalo y vuelve a ejecutar."
    }
}

# ----------------------------------------------------------------------------
# 0. Pre-requisitos
# ----------------------------------------------------------------------------

Write-Step 'Comprobando pre-requisitos'

Assert-Command -Name 'git'
Assert-Command -Name 'python'

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "RepoPath no existe: $RepoPath"
}
$backendPath = Join-Path $RepoPath 'backend'
if (-not (Test-Path -LiteralPath $backendPath)) {
    throw "No se encuentra la carpeta backend en $backendPath"
}

Write-Ok "Repo: $RepoPath"
Write-Ok "Branch destino: $Branch"

# ----------------------------------------------------------------------------
# 1. Git
# ----------------------------------------------------------------------------

Write-Step "git fetch + checkout + pull ($Branch)"

# Aviso si hay cambios sin commitear; no abortamos pero el pull podría fallar.
$dirty = & git -C $RepoPath status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw 'git status falló; ¿es realmente un repo git?'
}
if ($dirty) {
    Write-Warn 'El árbol de trabajo tiene cambios sin commitear:'
    $dirty | ForEach-Object { Write-Host "        $_" -ForegroundColor DarkGray }
    Write-Warn 'Si el pull se queja, considera "git stash" antes de re-ejecutar.'
}

Invoke-Native -File 'git' -Args @('-C', $RepoPath, 'fetch', 'origin')
Write-Ok 'fetch ok'

# Asegura que la rama remota existe
$remoteRef = "refs/remotes/origin/$Branch"
& git -C $RepoPath show-ref --verify --quiet $remoteRef
if ($LASTEXITCODE -ne 0) {
    throw "La rama remota '$Branch' no existe en origin. ¿Has empujado la PR?"
}

# Checkout (crea tracking si la rama local no existe)
& git -C $RepoPath rev-parse --verify --quiet $Branch | Out-Null
if ($LASTEXITCODE -eq 0) {
    Invoke-Native -File 'git' -Args @('-C', $RepoPath, 'checkout', $Branch)
} else {
    Invoke-Native -File 'git' -Args @('-C', $RepoPath, 'checkout', '-b', $Branch, "origin/$Branch")
}
Write-Ok "checkout $Branch ok"

Invoke-Native -File 'git' -Args @('-C', $RepoPath, 'pull', '--ff-only', 'origin', $Branch)
$head = (& git -C $RepoPath rev-parse --short HEAD).Trim()
Write-Ok "pull ok (HEAD = $head)"

# ----------------------------------------------------------------------------
# 2. Virtualenv
# ----------------------------------------------------------------------------

Write-Step 'Preparando virtualenv backend\.venv'

$venvPath    = Join-Path $backendPath '.venv'
$activatePs1 = Join-Path $venvPath 'Scripts\Activate.ps1'

if (-not (Test-Path -LiteralPath $activatePs1)) {
    Write-Warn 'No existe .venv; creando uno nuevo con python -m venv .venv'
    Invoke-Native -File 'python' -Args @('-m', 'venv', '.venv') -WorkingDirectory $backendPath
}

. $activatePs1
Write-Ok "venv activo: $env:VIRTUAL_ENV"

# Sanity-check del intérprete activo
$pyVer = (& python --version) 2>&1
Write-Ok "Python: $pyVer"

# ----------------------------------------------------------------------------
# 3. Dependencias
# ----------------------------------------------------------------------------

if ($SkipPipInstall) {
    Write-Step 'pip install — SALTADO (-SkipPipInstall)'
} else {
    Write-Step 'pip install -r backend\requirements.txt'
    Invoke-Native -File 'python' -Args @('-m', 'pip', 'install', '--upgrade', 'pip') -WorkingDirectory $backendPath
    Invoke-Native -File 'python' -Args @('-m', 'pip', 'install', '-r', 'requirements.txt') -WorkingDirectory $backendPath
    Write-Ok 'dependencias instaladas'
}

# ----------------------------------------------------------------------------
# 4. Alembic
# ----------------------------------------------------------------------------

if ($SkipAlembic) {
    Write-Step 'Alembic — SALTADO (-SkipAlembic)'
} else {
    Write-Step 'alembic current'
    Invoke-Native -File 'alembic' -Args @('current') -WorkingDirectory $backendPath

    Write-Step 'alembic upgrade head (idempotente)'
    Invoke-Native -File 'alembic' -Args @('upgrade', 'head') -WorkingDirectory $backendPath

    Write-Step 'alembic current (post-upgrade)'
    Invoke-Native -File 'alembic' -Args @('current') -WorkingDirectory $backendPath
    Write-Ok 'esquema sincronizado'
}

# ----------------------------------------------------------------------------
# 5. Health-check del backend (si está corriendo)
# ----------------------------------------------------------------------------

Write-Step "Health-check $BackendUrl/health"

try {
    $resp = Invoke-RestMethod -Uri "$BackendUrl/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    $json = $resp | ConvertTo-Json -Compress
    Write-Ok "backend responde: $json"

    try {
        $providers = Invoke-RestMethod -Uri "$BackendUrl/ai/providers" -Method Get -TimeoutSec 5 -ErrorAction Stop
        $available = ($providers | Where-Object { $_.available }) | ForEach-Object { $_.name }
        if ($available) {
            Write-Ok ("providers disponibles: " + ($available -join ', '))
        } else {
            Write-Warn 'no hay providers disponibles'
        }
    } catch {
        Write-Warn "no se pudo consultar /ai/providers: $($_.Exception.Message)"
    }
}
catch {
    Write-Warn "backend no responde en $BackendUrl/health"
    Write-Warn 'Si el backend NO está arrancado es normal. Para levantarlo:'
    Write-Host  '        cd backend' -ForegroundColor DarkGray
    Write-Host  '        uvicorn main:app --reload --host 127.0.0.1 --port 8000' -ForegroundColor DarkGray
}

# ----------------------------------------------------------------------------
# Resumen
# ----------------------------------------------------------------------------

Write-Step 'Resumen'
Write-Ok "Rama: $Branch ($head)"
if (-not $SkipPipInstall) { Write-Ok 'Dependencias instaladas' }
if (-not $SkipAlembic)    { Write-Ok 'Alembic en head' }
Write-Host ''
Write-Host 'Listo. Si el backend estaba corriendo, reinícialo (Ctrl+C + uvicorn) para aplicar el nuevo código.' -ForegroundColor Green
