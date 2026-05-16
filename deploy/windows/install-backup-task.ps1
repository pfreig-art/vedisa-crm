#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Registra una Scheduled Task que ejecuta backup.ps1 diario a las 03:00.

.PARAMETER InstallPath
    Raiz del despliegue (por defecto C:\vedisa\crm).

.PARAMETER TaskName
    Nombre de la tarea (por defecto VedisaCRM-Backup).

.PARAMETER Hour, Minute
    Hora de ejecucion (por defecto 03:00).

.PARAMETER RunAsUser
    Cuenta. Por defecto SYSTEM.
#>
[CmdletBinding()]
param(
    [string]$InstallPath = "C:\vedisa\crm",
    [string]$TaskName    = "VedisaCRM-Backup",
    [int]   $Hour        = 3,
    [int]   $Minute      = 0,
    [string]$RunAsUser   = "SYSTEM"
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $InstallPath "deploy\windows\backup.ps1"
if (-not (Test-Path $Script)) { throw "No se encuentra $Script" }

$Action  = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`" -InstallPath `"$InstallPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hour).AddMinutes($Minute))
$Principal = New-ScheduledTaskPrincipal -UserId $RunAsUser -LogonType ServiceAccount -RunLevel Highest
$Settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings `
    -Description "Backup diario de la DB vedisa_crm con rotacion 7 dias" | Out-Null

Write-Host "Scheduled Task '$TaskName' registrada para correr diaria a las $Hour`:$Minute." -ForegroundColor Green
