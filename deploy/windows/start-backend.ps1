#Requires -Version 5.1
<#
.SYNOPSIS
    Wrapper de arranque del backend de Vedisa CRM como Windows Service.

.DESCRIPTION
    Lee el archivo .env de $InstallPath\backend\.env, exporta cada KEY=VALUE
    al entorno del proceso y arranca uvicorn apuntando a app.main:app.

    Este wrapper existe porque los Windows Services nativos (sc.exe) no leen
    archivos .env. La unica fuente de verdad para variables sensibles
    (DATABASE_URL, SECRET_KEY) es el .env del directorio backend.

.PARAMETER InstallPath
    Raiz del despliegue (por defecto C:\vedisa\crm).

.PARAMETER VenvPath
    Ruta al virtualenv (por defecto $InstallPath\.venv).
#>
[CmdletBinding()]
param(
    [string]$InstallPath = "C:\vedisa\crm",
    [string]$VenvPath    = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VenvPath)) {
    $VenvPath = Join-Path $InstallPath ".venv"
}

$BackendPath = Join-Path $InstallPath "backend"
$EnvFile     = Join-Path $BackendPath ".env"
$Python      = Join-Path $VenvPath "Scripts\python.exe"
$LogDir      = Join-Path $InstallPath "logs"

if (-not (Test-Path $Python))      { throw "No se encontro Python en $Python" }
if (-not (Test-Path $BackendPath)) { throw "No se encontro backend en $BackendPath" }
if (-not (Test-Path $LogDir))      { New-Item -ItemType Directory -Path $LogDir | Out-Null }

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $idx   = $line.IndexOf("=")
            $key   = $line.Substring(0, $idx).Trim()
            $value = $line.Substring($idx + 1).Trim()
            # Quitar comillas envolventes si las hay.
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Warning "No existe $EnvFile. Se usaran los defaults del codigo."
}

$bindHost = [Environment]::GetEnvironmentVariable("HOST")
if ([string]::IsNullOrWhiteSpace($bindHost)) { $bindHost = "127.0.0.1" }
$bindPort = [Environment]::GetEnvironmentVariable("PORT")
if ([string]::IsNullOrWhiteSpace($bindPort)) { $bindPort = "8081" }

Set-Location $BackendPath

# Exec uvicorn en primer plano: el Service Control Manager lo supervisa.
& $Python -m uvicorn main:app --host $bindHost --port $bindPort --workers 1
