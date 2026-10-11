@echo off
setlocal
cd /d "%~dp0"
python iniciar_servidor.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo [ERROR] El servidor termino con codigo %RC%.
pause
exit /b %RC%
