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

## Configuración de seguridad local

```powershell
Copy-Item .env.example .env
```

El archivo `.env` está excluido de Git y no debe versionarse. Variables:

- `SECRET_KEY`: clave de firma JWT (mínimo 32 caracteres). Si se omite, el
  backend usa una clave efímera aleatoria; defínela para que las sesiones
  sobrevivan reinicios o varios workers. Los valores `REPLACE_…` se rechazan.
- `DEMO_OPERADOR_PASSWORD`, `DEMO_TECNICO_PASSWORD`, `DEMO_ADMIN_PASSWORD`
  (también se aceptan `DEMO_OPERATOR_PASSWORD` y `DEMO_TECHNICIAN_PASSWORD`):
  contraseñas de los usuarios demo (12–256 caracteres). Deben definirse las
  tres o ninguna. Si no se definen, el primer arranque genera claves aleatorias
  en `.demo_credentials.json`, archivo local ignorado por Git que debe
  mantenerse privado.

## Inicio rápido

```powershell
# Menú principal
python ejecutar.py

# Servidor backend (FastAPI)
python servidor-backend/main.py
```

## Reproducibilidad de la campaña SUMO

La red, la demanda, las semillas y los scripts de la campaña que compara el
controlador difuso con el plan fijo, el control actuado, Webster y Max-Pressure
están versionados. Las órdenes para repetirla, analizarla y calibrar el
controlador difuso están en
[`integracion-sumo/REPRODUCIBILIDAD.md`](integracion-sumo/REPRODUCIBILIDAD.md).

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

- Python 3.10+
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
- El backend escucha en `127.0.0.1` por defecto. Expóngalo a la red solo con un
  proxy TLS y una lista explícita de orígenes CORS.
- No versionar archivos grandes como modelos (`.pt`) ni resultados. Usa Git LFS o descargas separadas.
- Revisa `.gitignore` para excluir `__pycache__`, `node_modules`, resultados y temporales.
