#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Detiene y elimina el Windows Service VedisaCRM-Backend.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ServiceName = "VedisaCRM-Backend"

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "El servicio $ServiceName no existe. Nada que hacer." -ForegroundColor Yellow
    return
}

if ($svc.Status -ne "Stopped") {
    Write-Host "Deteniendo $ServiceName..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force
}

& sc.exe delete $ServiceName | Out-Null
Write-Host "Servicio $ServiceName eliminado." -ForegroundColor Green
