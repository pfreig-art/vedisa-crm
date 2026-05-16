#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Instala (idempotente) el Windows Service nativo VedisaCRM-Backend.

.DESCRIPTION
    Registra un servicio nativo que ejecuta PowerShell con el wrapper
    start-backend.ps1, el cual carga el .env y lanza uvicorn.

    Idempotente: si el servicio ya existe se reconfigura (sc.exe config)
    en lugar de duplicarse.

.PARAMETER InstallPath
    Raiz del despliegue (por defecto C:\vedisa\crm).

.PARAMETER VenvPath
    Ruta al virtualenv (por defecto $InstallPath\.venv).

.PARAMETER ServiceUser
    Cuenta bajo la que corre el servicio. Por defecto LocalSystem.
    Recomendado en prod: una cuenta de servicio dedicada con permisos sobre
    el directorio del repo y conexion a Postgres.

.PARAMETER PostgresService
    Nombre del servicio de Postgres del que dependera el backend
    (por defecto postgresql-x64-18). Ajustar a la version instalada.
#>
[CmdletBinding()]
param(
    [string]$InstallPath     = "C:\vedisa\crm",
    [string]$VenvPath        = "",
    [string]$ServiceUser     = "LocalSystem",
    [string]$ServicePassword = "",
    [string]$PostgresService = "postgresql-x64-18"
)

$ErrorActionPreference = "Stop"

$ServiceName  = "VedisaCRM-Backend"
$DisplayName  = "Vedisa CRM Backend"
$Description  = "API FastAPI del CRM Vedisa (uvicorn, puerto 8081)"

if ([string]::IsNullOrWhiteSpace($VenvPath)) {
    $VenvPath = Join-Path $InstallPath ".venv"
}

$Wrapper = Join-Path $InstallPath "deploy\windows\start-backend.ps1"

if (-not (Test-Path $Wrapper)) {
    throw "No se encuentra el wrapper en $Wrapper. Copia el repo a $InstallPath antes de instalar el servicio."
}

# PowerShell.exe en modo no interactivo, oculto, ejecutando el wrapper.
$PowerShellExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$BinPath = "`"$PowerShellExe`" -NoProfile -ExecutionPolicy Bypass -File `"$Wrapper`" -InstallPath `"$InstallPath`" -VenvPath `"$VenvPath`""

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Servicio $ServiceName ya existe; reconfigurando..." -ForegroundColor Yellow
    if ($existing.Status -ne "Stopped") {
        Stop-Service -Name $ServiceName -Force
    }
    & sc.exe config $ServiceName binPath= $BinPath start= auto depend= $PostgresService | Out-Null
    & sc.exe description $ServiceName $Description | Out-Null
} else {
    Write-Host "Creando servicio $ServiceName..." -ForegroundColor Green
    $args = @(
        "create", $ServiceName,
        "binPath=", $BinPath,
        "DisplayName=", $DisplayName,
        "start=", "auto",
        "depend=", $PostgresService
    )
    if ($ServiceUser -ne "LocalSystem" -and -not [string]::IsNullOrWhiteSpace($ServicePassword)) {
        $args += @("obj=", $ServiceUser, "password=", $ServicePassword)
    } else {
        $args += @("obj=", "LocalSystem")
    }
    & sc.exe @args | Out-Null
    & sc.exe description $ServiceName $Description | Out-Null
}

# Recovery: reinicio automatico ante fallos (60s, 60s, 120s).
& sc.exe failure $ServiceName reset= 86400 actions= restart/60000/restart/60000/restart/120000 | Out-Null

Write-Host "Listo. Iniciar con: Start-Service $ServiceName" -ForegroundColor Cyan
