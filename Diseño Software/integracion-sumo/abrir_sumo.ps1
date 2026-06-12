# Script PowerShell para abrir SUMO-GUI

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  INICIANDO SUMO-GUI - MAPA LIMA CENTRO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$limaPath = Join-Path $scriptPath "escenarios\lima-centro"

if (-not (Test-Path $limaPath)) {
    Write-Host "ERROR: No se encuentra el directorio lima-centro" -ForegroundColor Red
    pause
    exit 1
}

Set-Location $limaPath

Write-Host "Ubicación: $limaPath" -ForegroundColor Green
Write-Host "Configuración: osm.sumocfg" -ForegroundColor Green
Write-Host ""
Write-Host "Abriendo SUMO-GUI..." -ForegroundColor Yellow
Write-Host ""

try {
    sumo-gui -c osm.sumocfg
    
    Write-Host ""
    Write-Host "SUMO-GUI cerrado correctamente" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "  ERROR: SUMO-GUI no se pudo iniciar" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles causas:" -ForegroundColor Yellow
    Write-Host "  1. SUMO no está instalado"
    Write-Host "  2. SUMO no está en el PATH"
    Write-Host "  3. Archivos de configuración faltantes"
    Write-Host ""
    Write-Host "Solución:" -ForegroundColor Yellow
    Write-Host "  - Descargar SUMO: https://sumo.dlr.de/docs/Downloads.php"
    Write-Host "  - Agregar al PATH: C:\Program Files\Eclipse\Sumo\bin"
    Write-Host ""
}

pause
