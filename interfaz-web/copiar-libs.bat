@echo off
echo Copiando librerias desde node_modules a libs...

REM Crear directorios
mkdir libs\leaflet\images 2>nul
mkdir libs\chart 2>nul
mkdir libs\particles 2>nul
mkdir libs\fontawesome 2>nul

REM Copiar Leaflet
xcopy /Y node_modules\leaflet\dist\leaflet.js libs\leaflet\
xcopy /Y node_modules\leaflet\dist\leaflet.css libs\leaflet\
xcopy /Y /I node_modules\leaflet\dist\images\* libs\leaflet\images\

REM Copiar Chart.js
xcopy /Y node_modules\chart.js\dist\chart.umd.js libs\chart\

REM Copiar Particles.js
xcopy /Y node_modules\particles.js\particles.js libs\particles\particles.min.js*

echo.
echo Librerias copiadas exitosamente!
echo.
pause
