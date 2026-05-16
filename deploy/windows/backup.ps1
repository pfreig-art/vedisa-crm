#Requires -Version 5.1
<#
.SYNOPSIS
    Backup diario de la base de datos vedisa_crm con pg_dump.

.DESCRIPTION
    - Ejecuta pg_dump en formato custom (-F c) sobre la DB vedisa_crm.
    - Guarda en $BackupDir con timestamp.
    - Rota archivos: borra dumps con mtime > $RetentionDays dias.
    - Loggea cada ejecucion a $BackupDir\backup.log.

    La password se lee de $env:PGPASSWORD. Si no esta seteada, intenta
    leerla del .env del backend.

.PARAMETER InstallPath
    Raiz del despliegue, para localizar el .env (por defecto C:\vedisa\crm).

.PARAMETER BackupDir
    Directorio destino (por defecto $InstallPath\backups).

.PARAMETER PgUser
    Usuario Postgres (por defecto vedisa_app o $env:PG_USER).

.PARAMETER PgHost
    Host Postgres (por defecto localhost).

.PARAMETER Database
    Nombre de la DB (por defecto vedisa_crm).

.PARAMETER RetentionDays
    Dias a conservar (por defecto 7).
#>
[CmdletBinding()]
param(
    [string]$InstallPath   = "C:\vedisa\crm",
    [string]$BackupDir     = "",
    [string]$PgUser        = "",
    [string]$PgHost        = "localhost",
    [string]$Database      = "vedisa_crm",
    [int]   $RetentionDays = 7,
    [string]$PgDumpExe     = "pg_dump"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $BackupDir = Join-Path $InstallPath "backups"
}
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$LogFile = Join-Path $BackupDir "backup.log"

function Write-Log([string]$Message, [string]$Level = "INFO") {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts [$Level] $Message" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

# Cargar password/user del .env si no hay variables de entorno.
$envFile = Join-Path $InstallPath "backend\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $idx = $line.IndexOf("=")
            $k = $line.Substring(0, $idx).Trim()
            $v = $line.Substring($idx + 1).Trim()
            if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
                $v = $v.Substring(1, $v.Length - 2)
            }
            if ($k -eq "PG_USER"    -and [string]::IsNullOrWhiteSpace($PgUser))           { $PgUser = $v }
            if ($k -eq "PGPASSWORD" -and [string]::IsNullOrWhiteSpace($env:PGPASSWORD))   { $env:PGPASSWORD = $v }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PgUser))         { $PgUser = if ($env:PG_USER) { $env:PG_USER } else { "vedisa_app" } }
if ([string]::IsNullOrWhiteSpace($env:PGPASSWORD)) {
    Write-Log "PGPASSWORD vacio; pg_dump fallara si requiere autenticacion." "WARN"
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$OutFile   = Join-Path $BackupDir "vedisa_${Timestamp}.dump"

Write-Log "Iniciando backup -> $OutFile (host=$PgHost db=$Database user=$PgUser)"

try {
    & $PgDumpExe -h $PgHost -U $PgUser -d $Database -F c -f $OutFile
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump retorno codigo $LASTEXITCODE"
    }
    $size = (Get-Item $OutFile).Length
    Write-Log "Backup OK ($([math]::Round($size/1MB,2)) MB)"
} catch {
    Write-Log "FALLO backup: $_" "ERROR"
    throw
}

# Rotacion: borrar dumps con mtime > RetentionDays.
$cutoff = (Get-Date).AddDays(-$RetentionDays)
$deleted = 0
Get-ChildItem -Path $BackupDir -Filter "vedisa_*.dump" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object {
        Remove-Item $_.FullName -Force
        $deleted++
        Write-Log "Borrado por rotacion: $($_.Name)"
    }

Write-Log "Backup terminado. Archivos borrados por rotacion: $deleted."
