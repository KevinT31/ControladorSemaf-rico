@echo off
setlocal
cd /d "%~dp0"
REM Script para procesar videos con visualización en tiempo real
REM Ejecutar con: procesar_video.bat

echo ===============================================
echo  PROCESADOR DE VIDEO CON VISUALIZACION
echo ===============================================
echo.

python vision_computadora/procesar_video_con_visualizacion.py
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
