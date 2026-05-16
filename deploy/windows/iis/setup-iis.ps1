#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Configura IIS para servir el frontend de Vedisa CRM y hacer reverse proxy
    al backend uvicorn (puerto 8081) via URL Rewrite + ARR.

.DESCRIPTION
    - Verifica que IIS, URL Rewrite y ARR esten instalados.
    - Habilita el proxy de ARR.
    - Crea Application Pool "VedisaCRM" en modo "No Managed Code".
    - Crea sitio "VedisaCRM" apuntando a $InstallPath\frontend\dist.
    - Copia el web.config a esa ruta (preservando uno existente con backup).

    No instala IIS ni los modulos: requieren reinicio y se documentan en DEPLOY.md.

.PARAMETER InstallPath
    Raiz del despliegue (por defecto C:\vedisa\crm).

.PARAMETER SiteName
    Nombre del sitio IIS.

.PARAMETER Port
    Puerto del binding HTTP (por defecto 80).

.PARAMETER HostHeader
    Host header opcional. Vacio para usar el binding por defecto.
#>
[CmdletBinding()]
param(
    [string]$InstallPath = "C:\vedisa\crm",
    [string]$SiteName    = "VedisaCRM",
    [int]   $Port        = 80,
    [string]$HostHeader  = ""
)

$ErrorActionPreference = "Stop"

$WebRoot       = Join-Path $InstallPath "frontend\dist"
$WebConfigSrc  = Join-Path $InstallPath "deploy\windows\iis\web.config"
$AppPoolName   = "VedisaCRM"

Write-Host "[1/6] Verificando prerequisitos IIS..." -ForegroundColor Cyan
Import-Module WebAdministration -ErrorAction Stop

$features = Get-WindowsFeature -Name Web-Server, Web-WebServer, Web-Common-Http -ErrorAction SilentlyContinue
if ($null -eq $features -or -not ($features | Where-Object Installed)) {
    throw "IIS no esta instalado. Instala el rol Web-Server (Install-WindowsFeature Web-Server -IncludeManagementTools) y reinicia."
}

$rewriteInstalled = Get-WebGlobalModule -Name "RewriteModule" -ErrorAction SilentlyContinue
if (-not $rewriteInstalled) {
    throw "URL Rewrite no esta instalado. Descarga: https://www.iis.net/downloads/microsoft/url-rewrite"
}

$arrInstalled = Get-WebGlobalModule -Name "ApplicationRequestRouting" -ErrorAction SilentlyContinue
if (-not $arrInstalled) {
    throw "Application Request Routing (ARR) no esta instalado. Descarga: https://www.iis.net/downloads/microsoft/application-request-routing"
}

Write-Host "[2/6] Habilitando proxy ARR..." -ForegroundColor Cyan
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" `
    -Filter "system.webServer/proxy" -Name "enabled" -Value "True"

Write-Host "[3/6] Creando Application Pool $AppPoolName..." -ForegroundColor Cyan
if (-not (Test-Path "IIS:\AppPools\$AppPoolName")) {
    New-WebAppPool -Name $AppPoolName | Out-Null
}
Set-ItemProperty "IIS:\AppPools\$AppPoolName" -Name "managedRuntimeVersion" -Value ""
Set-ItemProperty "IIS:\AppPools\$AppPoolName" -Name "startMode" -Value "AlwaysRunning"

Write-Host "[4/6] Verificando webroot $WebRoot..." -ForegroundColor Cyan
if (-not (Test-Path $WebRoot)) {
    throw "No existe $WebRoot. Ejecuta 'npm run build' en frontend\ antes de configurar IIS."
}

Write-Host "[5/6] Copiando web.config al webroot..." -ForegroundColor Cyan
if (-not (Test-Path $WebConfigSrc)) { throw "No se encuentra $WebConfigSrc" }
$WebConfigDst = Join-Path $WebRoot "web.config"
if (Test-Path $WebConfigDst) {
    $backup = "$WebConfigDst.bak.$(Get-Date -Format yyyyMMddHHmmss)"
    Copy-Item $WebConfigDst $backup
    Write-Host "  backup previo en $backup" -ForegroundColor DarkGray
}
Copy-Item -Force $WebConfigSrc $WebConfigDst

Write-Host "[6/6] Creando/actualizando sitio $SiteName..." -ForegroundColor Cyan
if (Test-Path "IIS:\Sites\$SiteName") {
    Set-ItemProperty "IIS:\Sites\$SiteName" -Name "physicalPath"          -Value $WebRoot
    Set-ItemProperty "IIS:\Sites\$SiteName" -Name "applicationPool"       -Value $AppPoolName
} else {
    $bindingInfo = if ([string]::IsNullOrWhiteSpace($HostHeader)) { "*:${Port}:" } else { "*:${Port}:$HostHeader" }
    New-Website -Name $SiteName -PhysicalPath $WebRoot -ApplicationPool $AppPoolName `
        -Port $Port -HostHeader $HostHeader -Force | Out-Null
}

Start-WebAppPool -Name $AppPoolName -ErrorAction SilentlyContinue
Start-Website  -Name $SiteName    -ErrorAction SilentlyContinue

Write-Host "Listo. Sitio sirviendo desde $WebRoot en puerto $Port." -ForegroundColor Green
Write-Host "Verifica: curl http://localhost/healthz" -ForegroundColor Cyan
