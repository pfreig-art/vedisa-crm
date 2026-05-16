#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Aplica una actualizacion al backend: stop + git pull + deps + alembic + start.

.DESCRIPTION
    Flujo estandar de despliegue de un release nuevo. Asume que el repo
    esta clonado en $InstallPath y el venv en $VenvPath.

.PARAMETER InstallPath
    Raiz del despliegue (por defecto C:\vedisa\crm).

.PARAMETER VenvPath
    Ruta al virtualenv (por defecto $InstallPath\.venv).

.PARAMETER SkipFrontend
    Si se indica, no rebuilda el frontend.
#>
[CmdletBinding()]
param(
    [string]$InstallPath = "C:\vedisa\crm",
    [string]$VenvPath    = "",
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$ServiceName = "VedisaCRM-Backend"

if ([string]::IsNullOrWhiteSpace($VenvPath)) {
    $VenvPath = Join-Path $InstallPath ".venv"
}

$Python = Join-Path $VenvPath "Scripts\python.exe"
$Pip    = Join-Path $VenvPath "Scripts\pip.exe"
$Backend = Join-Path $InstallPath "backend"
$Frontend = Join-Path $InstallPath "frontend"

Write-Host "[1/6] Deteniendo $ServiceName..." -ForegroundColor Cyan
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne "Stopped") { Stop-Service -Name $ServiceName -Force }

Write-Host "[2/6] git pull..." -ForegroundColor Cyan
Push-Location $InstallPath
try {
    & git pull --ff-only
} finally { Pop-Location }

Write-Host "[3/6] Instalando dependencias Python..." -ForegroundColor Cyan
& $Pip install -r (Join-Path $Backend "requirements.txt")

Write-Host "[4/6] Aplicando migraciones Alembic..." -ForegroundColor Cyan
Push-Location $Backend
try {
    & $Python -m alembic upgrade head
} finally { Pop-Location }

if (-not $SkipFrontend) {
    Write-Host "[5/6] Build frontend..." -ForegroundColor Cyan
    Push-Location $Frontend
    try {
        & npm ci
        & npm run build
    } finally { Pop-Location }
} else {
    Write-Host "[5/6] Frontend omitido (-SkipFrontend)." -ForegroundColor Yellow
}

Write-Host "[6/6] Arrancando $ServiceName..." -ForegroundColor Cyan
Start-Service -Name $ServiceName

Write-Host "Actualizacion completa." -ForegroundColor Green
