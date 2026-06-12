# Script para crear mapa amplio de Lima - Paso a Paso
# Ejecutar cada sección cuando se te indique

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  CREACIÓN DE MAPA AMPLIO DE LIMA - PRESENTACIÓN" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$limaAmplioDir = "C:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2\integracion-sumo\escenarios\lima-amplio"

# ====================================================================
# PASO 1: DESCARGAR MAPA (si no existe)
# ====================================================================
function Paso1-DescargarMapa {
    Write-Host "`n[PASO 1/5] Descargando mapa de OpenStreetMap..." -ForegroundColor Yellow
    
    Set-Location $limaAmplioDir
    
    if (Test-Path "lima_amplio.osm") {
        $size = (Get-Item "lima_amplio.osm").Length / 1MB
        Write-Host "  Archivo ya existe: lima_amplio.osm ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
        return $true
    }
    
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri "https://overpass-api.de/api/map?bbox=-77.0700,-12.1200,-77.0100,-12.0400" `
                          -OutFile "lima_amplio.osm" `
                          -TimeoutSec 180
        
        $size = (Get-Item "lima_amplio.osm").Length / 1MB
        Write-Host "  Descarga completada: $([math]::Round($size, 2)) MB" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  Error en descarga automatica" -ForegroundColor Red
        Write-Host "  Descarga manual desde: https://www.openstreetmap.org/export" -ForegroundColor Yellow
        return $false
    }
}

# ====================================================================
# PASO 2: CONVERTIR A RED SUMO
# ====================================================================
function Paso2-ConvertirRed {
    Write-Host "`n[PASO 2/5] Convirtiendo OSM a red SUMO..." -ForegroundColor Yellow
    
    Set-Location $limaAmplioDir
    
    if (-not (Test-Path "lima_amplio.osm")) {
        Write-Host "  ERROR: Archivo lima_amplio.osm no encontrado" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  Ejecutando netconvert..." -ForegroundColor Cyan
    Write-Host "  (Esto puede tomar 2-3 minutos)" -ForegroundColor Gray
    
    $cmd = @(
        "netconvert",
        "--osm-files", "lima_amplio.osm",
        "--output-file", "lima_amplio.net.xml",
        "--geometry.remove",
        "--ramps.guess",
        "--junctions.join",
        "--tls.guess-signals",
        "--tls.default-type", "actuated",
        "--remove-edges.isolated",
        "--keep-edges.by-vclass", "passenger",
        "--remove-edges.by-type", "highway.footway,highway.path,highway.cycleway",
        "--verbose"
    )
    
    & $cmd[0] $cmd[1..($cmd.Length-1)] 2>&1 | Out-Host
    
    if ($LASTEXITCODE -eq 0 -and (Test-Path "lima_amplio.net.xml")) {
        $size = (Get-Item "lima_amplio.net.xml").Length / 1MB
        Write-Host "  Red SUMO creada: $([math]::Round($size, 2)) MB" -ForegroundColor Green
        
        # Contar semáforos
        $content = Get-Content "lima_amplio.net.xml" -Raw
        $tlCount = ([regex]::Matches($content, '<tlLogic')).Count
        Write-Host "  Semaforos detectados: $tlCount" -ForegroundColor Green
        
        return $true
    } else {
        Write-Host "  ERROR: Conversion fallida" -ForegroundColor Red
        return $false
    }
}

# ====================================================================
# PASO 3: GENERAR TRAFICO
# ====================================================================
function Paso3-GenerarTrafico {
    Write-Host "`n[PASO 3/5] Generando trafico vehicular..." -ForegroundColor Yellow
    
    Set-Location $limaAmplioDir
    
    if (-not (Test-Path "lima_amplio.net.xml")) {
        Write-Host "  ERROR: Red SUMO no encontrada" -ForegroundColor Red
        return $false
    }
    
    # Configurar SUMO_HOME
    if (-not $env:SUMO_HOME) {
        $env:SUMO_HOME = "C:\Program Files\Eclipse\Sumo"
    }
    
    $randomTripsScript = Join-Path $env:SUMO_HOME "tools\randomTrips.py"
    
    if (-not (Test-Path $randomTripsScript)) {
        Write-Host "  ERROR: randomTrips.py no encontrado en SUMO_HOME" -ForegroundColor Red
        Write-Host "  Ruta buscada: $randomTripsScript" -ForegroundColor Gray
        return $false
    }
    
    Write-Host "  Generando 1500 vehiculos..." -ForegroundColor Cyan
    Write-Host "  (Esto puede tomar 1-2 minutos)" -ForegroundColor Gray
    
    python $randomTripsScript `
        -n lima_amplio.net.xml `
        -o lima_amplio.rou.xml `
        -e 3600 `
        -p 2.4 `
        --fringe-factor 5 `
        --trip-attributes 'departLane="best" departSpeed="max"' 2>&1 | Out-Host
    
    if ($LASTEXITCODE -eq 0 -and (Test-Path "lima_amplio.rou.xml")) {
        Write-Host "  Trafico generado exitosamente" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ERROR: Generacion de trafico fallida" -ForegroundColor Red
        return $false
    }
}

# ====================================================================
# PASO 4: PROBAR SIMULACION
# ====================================================================
function Paso4-ProbarSimulacion {
    Write-Host "`n[PASO 4/5] Probando simulacion SUMO..." -ForegroundColor Yellow
    
    Set-Location $limaAmplioDir
    
    if (-not (Test-Path "lima_amplio.sumocfg")) {
        Write-Host "  ERROR: Archivo de configuracion no encontrado" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  Abriendo SUMO-GUI..." -ForegroundColor Cyan
    Write-Host "  Presiona Play en SUMO para ver la simulacion" -ForegroundColor Yellow
    
    Start-Process "sumo-gui" -ArgumentList "-c", "lima_amplio.sumocfg"
    
    Write-Host "  SUMO-GUI iniciado" -ForegroundColor Green
    return $true
}

# ====================================================================
# PASO 5: EXTRAER CALLES PARA WEB
# ====================================================================
function Paso5-ExtraerCalles {
    Write-Host "`n[PASO 5/5] Extrayendo calles para visualizacion web..." -ForegroundColor Yellow
    
    $integrationDir = "C:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2\integracion-sumo"
    Set-Location $integrationDir
    
    # Crear script temporal para extraer calles
    $tempScript = @"
import sys
from pathlib import Path
sys.path.insert(0, str(Path('$integrationDir')))

from extraer_calles import extraer_calles_sumo, guardar_geojson

print('Extrayendo calles del mapa amplio...')
ruta_net = Path('$limaAmplioDir') / 'lima_amplio.net.xml'

if not ruta_net.exists():
    print(f'ERROR: {ruta_net} no encontrado')
    sys.exit(1)

geojson = extraer_calles_sumo(str(ruta_net))
ruta_salida = Path('$limaAmplioDir') / 'calles.geojson'
guardar_geojson(geojson, str(ruta_salida))

print(f'Calles extraidas: {len(geojson["features"])}')
print(f'Archivo: {ruta_salida}')
"@
    
    $tempScript | Out-File -FilePath "temp_extraer_amplio.py" -Encoding UTF8
    
    python temp_extraer_amplio.py
    
    Remove-Item "temp_extraer_amplio.py" -ErrorAction SilentlyContinue
    
    if (Test-Path "$limaAmplioDir\calles.geojson") {
        Write-Host "  Calles extraidas exitosamente" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ERROR: No se pudo extraer calles" -ForegroundColor Red
        return $false
    }
}

# ====================================================================
# EJECUTAR TODOS LOS PASOS
# ====================================================================
function Ejecutar-TodosLosPasos {
    Write-Host "`n" + "="*70 -ForegroundColor Cyan
    Write-Host "  INICIANDO CREACION COMPLETA DEL MAPA" -ForegroundColor Cyan
    Write-Host "="*70 + "`n" -ForegroundColor Cyan
    
    $pasos = @(
        @{ Nombre = "Descargar mapa"; Funcion = ${function:Paso1-DescargarMapa} },
        @{ Nombre = "Convertir a red SUMO"; Funcion = ${function:Paso2-ConvertirRed} },
        @{ Nombre = "Generar trafico"; Funcion = ${function:Paso3-GenerarTrafico} },
        @{ Nombre = "Probar simulacion"; Funcion = ${function:Paso4-ProbarSimulacion} },
        @{ Nombre = "Extraer calles"; Funcion = ${function:Paso5-ExtraerCalles} }
    )
    
    $exitosos = 0
    foreach ($paso in $pasos) {
        if (& $paso.Funcion) {
            $exitosos++
        } else {
            Write-Host "`nPaso fallido: $($paso.Nombre)" -ForegroundColor Red
            Write-Host "Proceso detenido." -ForegroundColor Yellow
            break
        }
    }
    
    Write-Host "`n" + "="*70 -ForegroundColor Cyan
    if ($exitosos -eq $pasos.Length) {
        Write-Host "  PROCESO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
        Write-Host "="*70 + "`n" -ForegroundColor Cyan
        
        Write-Host "Archivos generados:" -ForegroundColor Yellow
        Get-ChildItem $limaAmplioDir -Filter "lima_amplio.*" | ForEach-Object {
            $size = if ($_.Length -gt 1MB) { "$([math]::Round($_.Length / 1MB, 2)) MB" } else { "$([math]::Round($_.Length / 1KB, 2)) KB" }
            Write-Host "  $($_.Name) - $size" -ForegroundColor Cyan
        }
        
        Write-Host "`nProximos pasos:" -ForegroundColor Yellow
        Write-Host "  1. Reiniciar el servidor: python iniciar_servidor.py"
        Write-Host "  2. Cambiar a modo SUMO en el navegador"
        Write-Host "  3. Ver el mapa amplio de Lima automaticamente"
        
    } else {
        Write-Host "  PROCESO INCOMPLETO ($exitosos/$($pasos.Length) pasos)" -ForegroundColor Yellow
        Write-Host "="*70 + "`n" -ForegroundColor Cyan
    }
}

# ====================================================================
# MENU PRINCIPAL
# ====================================================================
Write-Host "Opciones disponibles:" -ForegroundColor Yellow
Write-Host "  1. Ejecutar todos los pasos automaticamente"
Write-Host "  2. Ejecutar paso por paso"
Write-Host ""

$opcion = Read-Host "Selecciona una opcion (1 o 2)"

if ($opcion -eq "1") {
    Ejecutar-TodosLosPasos
} else {
    Write-Host "`nEjecuta manualmente cada funcion:" -ForegroundColor Yellow
    Write-Host "  Paso1-DescargarMapa"
    Write-Host "  Paso2-ConvertirRed"
    Write-Host "  Paso3-GenerarTrafico"
    Write-Host "  Paso4-ProbarSimulacion"
    Write-Host "  Paso5-ExtraerCalles"
}

Write-Host "`nPresiona Enter para salir..."
Read-Host
