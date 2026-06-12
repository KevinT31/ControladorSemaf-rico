@echo off
REM Script para reiniciar el simulador de forma sencilla
echo.
echo ========================================
echo  REINICIADOR DE SIMULADOR
echo ========================================
echo.
echo Enviando solicitud de reinicio al servidor...
echo Asegúrate de que el servidor esté corriendo en http://localhost:8000
echo.

python reiniciar_simulador.py

echo.
echo Si ves "✅ Simulador reiniciado correctamente" arriba, entonces:
echo   - El backend ahora tiene las 47 intersecciones cargadas
echo   - Actualiza la página web (F5) para ver todos los marcadores brillar
echo.
pause
