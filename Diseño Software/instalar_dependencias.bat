@echo off
echo ========================================================================
echo INSTALADOR AUTOMATICO - Sistema de Control Semáforico
echo ========================================================================
echo.
echo Instalando todas las dependencias necesarias...
echo.

REM Actualizar pip
python -m pip install --upgrade pip

REM Instalar dependencias principales
echo [1/2] Instalando dependencias del sistema...
python -m pip install -r requirements.txt

REM Verificar instalación
echo.
echo [2/2] Verificando instalacion...
python -c "import cv2, numpy, ultralytics, psutil; print('OK - Dependencias basicas instaladas')"

echo.
echo ========================================================================
echo INSTALACION COMPLETADA
echo ========================================================================
echo.
echo Puedes ejecutar el sistema con: python ejecutar.py
echo Nota SUMO: instálalo por separado si usarás TraCI/SUMO-GUI.
echo.
pause
