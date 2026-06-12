"""
Servidor Principal FastAPI - REFACTORIZADO

Servidor simplificado con arquitectura MVC limpia
"""

# Configurar encoding para Windows
import sys
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar configuración
from config import settings

# Importar rutas
from rutas import (
    intersecciones_router,
    emergencias_router,
    simulacion_router,
    video_router,
    sumo_router,
    websocket_router
)

# Importar servicios
from servicios import estado_sistema
from servicios.websocket_manager import WebSocketManager

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def inicializar_sistema():
    """Inicializa componentes del sistema"""
    logger.info("🚀 Inicializando sistema...")

    # Importar módulos del núcleo
    import importlib.util

    def import_module_from_path(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    nucleo_path = settings.BASE_DIR / 'nucleo'

    # Importar módulos del núcleo
    indice_mod = import_module_from_path('indice_congestion', nucleo_path / 'indice_congestion.py')
    difuso_mod = import_module_from_path('controlador_difuso', nucleo_path / 'controlador_difuso.py')
    olas_mod = import_module_from_path('olas_verdes_dinamicas', nucleo_path / 'olas_verdes_dinamicas.py')

    # Crear calculadores
    ParametrosInterseccion = indice_mod.ParametrosInterseccion
    params = ParametrosInterseccion()

    estado_sistema.calculador_icv = indice_mod.CalculadorICV(params)
    estado_sistema.controlador_difuso = difuso_mod.ControladorDifuso()

    # Cargar intersecciones de Lima (las 31 intersecciones reales)
    from datos_intersecciones import obtener_intersecciones_lima
    intersecciones_data = obtener_intersecciones_lima()

    estado_sistema.intersecciones = {i['id']: i for i in intersecciones_data}

    # Inicializar simulador
    simulador_path = settings.BASE_DIR / 'simulador_trafico'
    sim_mod = import_module_from_path('simulador_lima', simulador_path / 'simulador_lima.py')

    InterseccionSim = sim_mod.Interseccion
    intersecciones_sim = [
        InterseccionSim(
            id=i['id'],
            nombre=i['nombre'],
            latitud=i['latitud'],
            longitud=i['longitud'],
            num_carriles=i['num_carriles']
        )
        for i in intersecciones_data
    ]

    estado_sistema.simulador = sim_mod.SimuladorLima(
        intersecciones_sim,
        escenario='hora_pico_manana'
    )

    # Crear grafo para olas verdes
    Interseccion = olas_mod.Interseccion
    GrafoIntersecciones = olas_mod.GrafoIntersecciones
    CoordinadorOlasVerdes = olas_mod.CoordinadorOlasVerdes

    grafo = GrafoIntersecciones()
    for data in intersecciones_data:
        inter = Interseccion(
            id=data['id'],
            nombre=data['nombre'],
            latitud=data['latitud'],
            longitud=data['longitud'],
            vecinos=[],
            distancia_vecinos={}
        )
        grafo.agregar_interseccion(inter)

    # Agregar conexiones (las mismas del main.py original)
    from datos_intersecciones import obtener_conexiones_lima
    conexiones = obtener_conexiones_lima()
    for origen, destino, distancia in conexiones:
        grafo.agregar_conexion(origen, destino, distancia)

    estado_sistema.coordinador_olas_verdes = CoordinadorOlasVerdes(grafo)

    logger.info("✅ Sistema inicializado correctamente")
    logger.info(f"📍 {len(intersecciones_data)} intersecciones cargadas")


async def bucle_simulacion():
    """Bucle principal de simulación"""
    logger.info("🔄 Iniciando bucle de simulación...")

    while True:
        try:
            if not estado_sistema.simulacion_pausada and estado_sistema.modo == 'simulador' and estado_sistema.simulador:
                # Simular un paso
                estados = estado_sistema.simulador.simular_paso(duracion_s=1.0)

                # Calcular métricas
                metricas_actualizadas = []
                for inter_id, estado in estados.items():
                    calculador = estado_sistema.calculador_icv
                    resultado_icv = calculador.calcular(
                        longitud_cola=estado.longitud_cola,
                        velocidad_promedio=estado.velocidad_promedio,
                        flujo_vehicular=estado.flujo_vehicular
                    )

                    metricas = {
                        'interseccion_id': inter_id,
                        'timestamp': estado.timestamp.isoformat(),
                        'icv': resultado_icv['icv'],
                        'clasificacion': resultado_icv['clasificacion'],
                        'color': resultado_icv['color'],
                        'num_vehiculos': estado.num_vehiculos,
                        'flujo': estado.flujo_vehicular,
                        'velocidad': estado.velocidad_promedio,
                        'cola': estado.longitud_cola
                    }
                    metricas_actualizadas.append(metricas)

                # Broadcast a clientes WebSocket
                await WebSocketManager.broadcast({
                    'tipo': 'metricas_actualizadas',
                    'datos': metricas_actualizadas
                })

            await asyncio.sleep(settings.SIMULACION_INTERVALO)

        except Exception as e:
            logger.error(f"❌ Error en bucle de simulación: {e}")
            await asyncio.sleep(5.0)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Manejador de ciclo de vida de la aplicación"""
    # Startup
    inicializar_sistema()
    tarea_simulacion = asyncio.create_task(bucle_simulacion())

    yield

    # Shutdown
    logger.info("🛑 Deteniendo sistema...")
    tarea_simulacion.cancel()
    WebSocketManager.limpiar_todas()
    try:
        await tarea_simulacion
    except asyncio.CancelledError:
        pass
    logger.info("✅ Sistema detenido correctamente")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registrar routers
app.include_router(intersecciones_router)
app.include_router(emergencias_router)
app.include_router(simulacion_router)
app.include_router(video_router)
app.include_router(sumo_router)
app.include_router(websocket_router)


# Ruta raíz
@app.get("/")
async def root():
    """Sirve el dashboard web"""
    interfaz_path = settings.INTERFAZ_WEB_DIR / "index.html"
    if interfaz_path.exists():
        return FileResponse(interfaz_path)
    return {"mensaje": "Sistema de Control Semafórico Activo", "version": settings.APP_VERSION}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from modelos.respuestas import HealthCheckResponse

    servicios_estado = {
        "simulador": "ok" if estado_sistema.simulador else "no_inicializado",
        "video": "ok" if estado_sistema.procesador_video else "no_activo",
        "sumo": "ok" if estado_sistema.conector_sumo and getattr(estado_sistema.conector_sumo, 'conectado', False) else "no_conectado",
        "websocket": f"{WebSocketManager.total_conexiones()} conexiones"
    }

    return HealthCheckResponse(
        status="ok",
        version=settings.APP_VERSION,
        servicios=servicios_estado
    )


# Montar archivos estáticos
if settings.INTERFAZ_WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.INTERFAZ_WEB_DIR)), name="static")
    logger.info(f"📁 Archivos estáticos montados desde: {settings.INTERFAZ_WEB_DIR}")


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print(f"  {settings.APP_NAME.upper()}")
    print("="*70)
    print(f"\n[*] Versión: {settings.APP_VERSION}")
    print(f"[*] Dashboard: http://localhost:{settings.PORT}")
    print(f"[*] WebSocket: ws://localhost:{settings.PORT}/ws")
    print(f"[*] Documentación API: http://localhost:{settings.PORT}/docs")
    print("\n✨ Presiona Ctrl+C para detener\n")

    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower())
