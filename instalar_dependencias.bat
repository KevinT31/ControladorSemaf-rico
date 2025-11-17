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
echo [1/3] Instalando dependencias del sistema...
python -m pip install -r requirements.txt

REM Instalar boxmot para ByteTrack (puede fallar, no es crítico)
echo.
echo [2/3] Instalando ByteTrack (tracker preferido)...
python -m pip install boxmot>=10.0.0
if %errorlevel% neq 0 (
    echo AVISO: ByteTrack no se pudo instalar. Se usara DeepSORT como fallback.
    echo Esto NO afecta el funcionamiento del sistema.
)

REM Verificar instalación
echo.
echo [3/3] Verificando instalacion...
python -c "import cv2; import numpy; import ultralytics; print('OK - Dependencias basicas instaladas')"

echo.
echo ========================================================================
echo INSTALACION COMPLETADA
echo ========================================================================
echo.
echo Puedes ejecutar el sistema con: python ejecutar.py
echo O ejecutar las pruebas con: python probar_capitulo6.py
echo.
pause
