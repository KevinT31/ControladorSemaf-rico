# Sistema de Control Semafórico Adaptativo

Sistema modular que integra ICV, control difuso, procesamiento de video y visualización web. Incluye apertura directa de escenarios SUMO.

## Instalación Rápida (Windows/PowerShell)

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Notas:
- SUMO/TraCI: instálalo por separado desde https://sumo.dlr.de y asegúrate de tener `sumo-gui` en el PATH si usarás la opción 3 del menú.
- Los modelos grandes (`*.pt`) no se versionan; descárgalos según necesidad.

## Inicio rápido

```powershell
# Menú principal
python ejecutar.py

# Servidor backend (FastAPI)
python servidor-backend/main.py
```

## Menú principal (ejecutar.py)

1. Iniciar Dashboard
2. Procesar Video con Análisis Completo
3. Conectar con SUMO (Lima Amplio / Lima Centro / ambos)
4. Comparar Adaptativo vs Tiempo Fijo
5. Ejecutar Pruebas del Sistema
6. Ver Estado de Componentes
7. Ver Documentación del Sistema
8. Exportar Configuración Actual
0. Salir

Notas:
- La opción 3 abre SUMO-GUI con `lima_amplio.sumocfg` y/o la configuración disponible en `lima-centro` (se detecta `lima_centro.sumocfg`, `osm.sumocfg` o cualquier `.sumocfg`).
- El procesamiento de video está unificado al modo completo.

## Estructura del proyecto

```
ejecutar.py                 # Punto de entrada
servidor-backend/           # API FastAPI y servicios
interfaz-web/               # Frontend HTML/JS
vision_computadora/         # Procesamiento de video
nucleo/                     # ICV, control difuso y métricas
integracion-sumo/           # Conectores y escenarios SUMO
datos/                      # Datos de ejemplo (no versionar videos)
```

## Dependencias principales

- Python 3.9+
- FastAPI, Uvicorn
- NumPy, OpenCV
- Psutil
- Ultralytics (opcional según modo de video)

Instalación (orden recomendado):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Consideraciones de despliegue

- Configura `sumo-gui` en el PATH para usar la opción 3.
- No versionar archivos grandes como modelos (`.pt`) ni resultados. Usa Git LFS o descargas separadas.
- Revisa `.gitignore` para excluir `__pycache__`, `node_modules`, resultados y temporales.
