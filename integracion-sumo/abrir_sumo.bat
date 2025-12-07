@echo off
REM Script para abrir SUMO-GUI con el mapa de Lima Centro

echo ======================================================================
echo   INICIANDO SUMO-GUI - MAPA LIMA CENTRO
echo ======================================================================
echo.

cd /d "%~dp0escenarios\lima-centro"

echo Abriendo SUMO-GUI...
echo.
echo Ubicacion: escenarios\lima-centro
echo Configuracion: osm.sumocfg
echo.

sumo-gui -c osm.sumocfg

if errorlevel 1 (
    echo.
    echo ======================================================================
    echo   ERROR: SUMO-GUI no se pudo iniciar
    echo ======================================================================
    echo.
    echo Posibles causas:
    echo   1. SUMO no esta instalado
    echo   2. SUMO no esta en el PATH
    echo   3. Archivos de configuracion faltantes
    echo.
    echo Solucion:
    echo   - Descargar SUMO: https://sumo.dlr.de/docs/Downloads.php
    echo   - Agregar al PATH: C:\Program Files\Eclipse\Sumo\bin
    echo.
    pause
) else (
    echo.
    echo SUMO-GUI cerrado correctamente
    echo.
)

pause
