@echo off
echo ========================================
echo    Limpiando puerto 8000...
echo ========================================

REM Matar todos los procesos Python
taskkill /F /IM python.exe /T 2>nul

REM Esperar 2 segundos
timeout /t 2 /nobreak >nul

REM Verificar si el puerto está libre
netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo [!] Puerto 8000 todavia ocupado, forzando liberacion...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        taskkill /F /PID %%a 2>nul
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo ========================================
echo    Iniciando servidor backend...
echo ========================================
echo.

cd servidor-backend
python main.py

pause
