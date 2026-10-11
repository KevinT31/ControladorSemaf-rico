@echo off
setlocal
cd /d "%~dp0"
echo ========================================================================
echo INSTALADOR AUTOMATICO - Sistema de Control Semáforico
echo ========================================================================
echo.
echo Instalando todas las dependencias necesarias...
echo.

REM Actualizar pip
python -m pip install --upgrade pip
if errorlevel 1 goto :error

REM Instalar dependencias principales
echo [1/2] Instalando dependencias del sistema...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

REM Verificar instalación
echo.
echo [2/2] Verificando instalacion...
python -c "import cv2, numpy, ultralytics, psutil; print('OK - Dependencias basicas instaladas')"
if errorlevel 1 goto :error

echo.
echo ========================================================================
echo INSTALACION COMPLETADA
echo ========================================================================
echo.
echo Puedes ejecutar el sistema con: python ejecutar.py
echo Nota SUMO: instálalo por separado si usarás TraCI/SUMO-GUI.
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] La instalacion no se completo. Revisa el mensaje anterior.
pause
exit /b 1
