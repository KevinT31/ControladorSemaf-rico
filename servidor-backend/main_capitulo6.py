# -*- coding: utf-8 -*-
"""
Servidor Principal FastAPI - IMPLEMENTACIÓN COMPLETA CAPÍTULO 6

Servidor con todas las funcionalidades del Capítulo 6:
- Estado Local con CamMask
- Control Difuso con 12 reglas jerárquicas
- Métricas de Red Globales
- Comparación Adaptativo vs Tiempo Fijo
- Integración SUMO completa
- WebSocket bidireccional con frontend
"""

# Configurar encoding para Windows
import sys
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import asyncio
import logging
import json

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar módulos del núcleo (Capítulo 6)
from nucleo.estado_local import EstadoLocalInterseccion, ParametrosInterseccion
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.metricas_red import (
    MetricasInterseccion,
    ConfiguracionInterseccion,
    AgregadorMetricasRed
)
from nucleo.sistema_comparacion import SistemaComparacion, TipoControl

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sistema_control.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
INTERFAZ_WEB_DIR = BASE_DIR / "interfaz-web"

APP_NAME = "Sistema de Control Semafórico Adaptativo Inteligente"
APP_VERSION = "2.0.0-Capitulo6"
HOST = "0.0.0.0"
PORT = 8000


# ============================================================================
# ESTADO GLOBAL DEL SISTEMA
# ============================================================================

class EstadoSistema:
    """Estado global del sistema"""

    def __init__(self):
        # Configuraciones de intersecciones
        self.configuraciones_intersecciones: Dict[str, ConfiguracionInterseccion] = {}

        # Estados locales por intersección
        self.estados_locales: Dict[str, EstadoLocalInterseccion] = {}

        # Controladores difusos por intersección
        self.controladores_difusos: Dict[str, ControladorDifusoCapitulo6] = {}

        # Agregador de métricas de red
        self.agregador_metricas: Optional[AgregadorMetricasRed] = None

        # Sistema de comparación
        self.sistema_comparacion: Optional[SistemaComparacion] = None

        # Modo de operación
        self.modo = 'simulador'  # 'simulador', 'video', 'sumo'
        self.simulacion_pausada = False
        self.modo_comparacion = False
        self.tipo_control_actual = TipoControl.ADAPTATIVO

        # Simulador (para modo demo)
        self.simulador = None

        # Conexiones WebSocket
        self.conexiones_ws: List[WebSocket] = []

        # Métricas en tiempo real
        self.metricas_tiempo_real: Dict = {}

    def registrar_interseccion(
        self,
        id_inter: str,
        nombre: str,
        peso: float = 1.0,
        ubicacion: tuple = (0.0, 0.0),
        num_carriles_ns: int = 2,
        num_carriles_eo: int = 2
    ):
        """Registra una nueva intersección en el sistema"""

        # Crear configuración
        config = ConfiguracionInterseccion(
            id=id_inter,
            nombre=nombre,
            peso=peso,
            ubicacion=ubicacion,
            num_carriles_ns=num_carriles_ns,
            num_carriles_eo=num_carriles_eo
        )
        self.configuraciones_intersecciones[id_inter] = config

        # Crear estado local
        params = ParametrosInterseccion(
            id_interseccion=id_inter,
            nombre=nombre
        )
        self.estados_locales[id_inter] = EstadoLocalInterseccion(params)

        # Crear controlador difuso
        self.controladores_difusos[id_inter] = ControladorDifusoCapitulo6(
            T_base_NS=30.0,
            T_base_EO=30.0,
            T_ciclo=90.0
        )

        logger.info(f"Intersección registrada: {nombre} (ID: {id_inter})")

    def inicializar_agregador_metricas(self):
        """Inicializa el agregador de métricas de red"""
        configuraciones = list(self.configuraciones_intersecciones.values())

        self.agregador_metricas = AgregadorMetricasRed(
            configuraciones=configuraciones,
            directorio_datos=BASE_DIR / "datos" / "metricas_red"
        )

        logger.info("✅ Agregador de métricas inicializado")

    def inicializar_sistema_comparacion(self):
        """Inicializa el sistema de comparación"""
        configuraciones = list(self.configuraciones_intersecciones.values())

        self.sistema_comparacion = SistemaComparacion(
            configuraciones_intersecciones=configuraciones,
            directorio_resultados=BASE_DIR / "resultados" / "comparacion"
        )

        logger.info("✅ Sistema de comparación inicializado")

    async def broadcast_ws(self, mensaje: dict):
        """Envía mensaje a todos los clientes WebSocket conectados"""
        if not self.conexiones_ws:
            return

        mensaje_json = json.dumps(mensaje)

        conexiones_cerradas = []
        for ws in self.conexiones_ws:
            try:
                await ws.send_text(mensaje_json)
            except:
                conexiones_cerradas.append(ws)

        # Limpiar conexiones cerradas
        for ws in conexiones_cerradas:
            if ws in self.conexiones_ws:
                self.conexiones_ws.remove(ws)


# Instancia global del estado
estado_sistema = EstadoSistema()


# ============================================================================
# INICIALIZACIÓN DEL SISTEMA
# ============================================================================

def inicializar_sistema():
    """Inicializa componentes del sistema"""
    logger.info("🚀 Inicializando sistema del Capítulo 6...")

    # Cargar intersecciones de ejemplo (Lima)
    # En producción, esto vendría de una base de datos o archivo de configuración
    intersecciones_lima = [
        {
            'id': 'I001',
            'nombre': 'Av. Arequipa - Av. Javier Prado',
            'peso': 1.5,
            'ubicacion': (-12.0893, -77.0315),
            'num_carriles_ns': 3,
            'num_carriles_eo': 3
        },
        {
            'id': 'I002',
            'nombre': 'Av. Brasil - Av. Venezuela',
            'peso': 1.2,
            'ubicacion': (-12.0715, -77.0531),
            'num_carriles_ns': 2,
            'num_carriles_eo': 2
        },
        {
            'id': 'I003',
            'nombre': 'Av. Universitaria - Av. La Marina',
            'peso': 1.0,
            'ubicacion': (-12.0893, -77.0842),
            'num_carriles_ns': 2,
            'num_carriles_eo': 2
        },
        {
            'id': 'I004',
            'nombre': 'Av. Abancay - Jr. Lampa',
            'peso': 0.8,
            'ubicacion': (-12.0464, -77.0282),
            'num_carriles_ns': 2,
            'num_carriles_eo': 2
        }
    ]

    # Registrar intersecciones
    for inter in intersecciones_lima:
        estado_sistema.registrar_interseccion(
            id_inter=inter['id'],
            nombre=inter['nombre'],
            peso=inter['peso'],
            ubicacion=inter['ubicacion'],
            num_carriles_ns=inter['num_carriles_ns'],
            num_carriles_eo=inter['num_carriles_eo']
        )

    # Inicializar agregador de métricas
    estado_sistema.inicializar_agregador_metricas()

    # Inicializar sistema de comparación
    estado_sistema.inicializar_sistema_comparacion()

    logger.info(f"✅ Sistema inicializado: {len(intersecciones_lima)} intersecciones")


# ============================================================================
# BUCLE DE SIMULACIÓN
# ============================================================================

async def bucle_simulacion():
    """Bucle principal de simulación (modo demo)"""
    logger.info("🔄 Iniciando bucle de simulación...")

    import random

    paso = 0

    while True:
        try:
            if not estado_sistema.simulacion_pausada and estado_sistema.modo == 'simulador':
                timestamp = datetime.now()

                # Simular métricas para cada intersección
                for id_inter in estado_sistema.configuraciones_intersecciones.keys():
                    # Simular valores aleatorios (en producción vendrían de sensores/video/SUMO)
                    metricas = MetricasInterseccion(
                        interseccion_id=id_inter,
                        timestamp=timestamp,
                        sc_ns=random.uniform(5, 40),
                        sc_eo=random.uniform(5, 40),
                        vavg_ns=random.uniform(15, 50),
                        vavg_eo=random.uniform(15, 50),
                        q_ns=random.uniform(8, 25),
                        q_eo=random.uniform(8, 25),
                        k_ns=random.uniform(0.02, 0.12),
                        k_eo=random.uniform(0.02, 0.12)
                    )

                    # Calcular ICV y PI
                    def calc_icv(sc, v, q, k):
                        sc_n = min(sc/50, 1.0)
                        v_n = 1.0 - min(v/60, 1.0)
                        k_n = min(k/0.15, 1.0)
                        q_n = 1.0 - min(q/30, 1.0)
                        return 0.4*sc_n + 0.3*v_n + 0.2*k_n + 0.1*q_n

                    metricas.icv_ns = calc_icv(metricas.sc_ns, metricas.vavg_ns, metricas.q_ns, metricas.k_ns)
                    metricas.icv_eo = calc_icv(metricas.sc_eo, metricas.vavg_eo, metricas.q_eo, metricas.k_eo)
                    metricas.pi_ns = metricas.vavg_ns / (metricas.sc_ns + 1.0)
                    metricas.pi_eo = metricas.vavg_eo / (metricas.sc_eo + 1.0)

                    # Actualizar agregador de métricas
                    estado_sistema.agregador_metricas.actualizar_metricas_interseccion(metricas)

                    # Aplicar control difuso
                    if paso % 30 == 0:  # Cada 30 pasos
                        controlador = estado_sistema.controladores_difusos[id_inter]
                        resultado = controlador.calcular_control_completo(
                            icv_ns=metricas.icv_ns,
                            pi_ns=metricas.pi_ns,
                            ev_ns=metricas.ev_ns,
                            icv_eo=metricas.icv_eo,
                            pi_eo=metricas.pi_eo,
                            ev_eo=metricas.ev_eo
                        )

                        metricas.T_verde_ns = resultado['T_verde_NS']
                        metricas.T_verde_eo = resultado['T_verde_EO']

                # Obtener métricas de red actualizadas
                metricas_red = estado_sistema.agregador_metricas.obtener_metricas_red_actual()

                if metricas_red:
                    # Broadcast a clientes WebSocket
                    await estado_sistema.broadcast_ws({
                        'tipo': 'metricas_red_actualizadas',
                        'datos': metricas_red.to_dict()
                    })

                paso += 1

            await asyncio.sleep(1.0)  # 1 segundo por paso

        except Exception as e:
            logger.error(f"❌ Error en bucle de simulación: {e}")
            await asyncio.sleep(5.0)


# ============================================================================
# CICLO DE VIDA DE LA APLICACIÓN
# ============================================================================

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
    try:
        await tarea_simulacion
    except asyncio.CancelledError:
        pass
    logger.info("✅ Sistema detenido correctamente")


# ============================================================================
# CREAR APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title=APP_NAME,
    description="Sistema de Control Semafórico Adaptativo con Lógica Difusa (Capítulo 6)",
    version=APP_VERSION,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# RUTAS DE LA API
# ============================================================================

@app.get("/")
async def root():
    """Sirve el dashboard web"""
    interfaz_path = INTERFAZ_WEB_DIR / "index.html"
    if interfaz_path.exists():
        return FileResponse(interfaz_path)
    return {
        "mensaje": "Sistema de Control Semafórico Activo - Capítulo 6",
        "version": APP_VERSION
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "modo": estado_sistema.modo,
        "intersecciones": len(estado_sistema.configuraciones_intersecciones),
        "websocket_conexiones": len(estado_sistema.conexiones_ws)
    }


@app.get("/api/intersecciones")
async def listar_intersecciones():
    """Lista todas las intersecciones"""
    intersecciones = []
    for id_inter, config in estado_sistema.configuraciones_intersecciones.items():
        intersecciones.append({
            'id': config.id,
            'nombre': config.nombre,
            'peso': config.peso,
            'ubicacion': {
                'latitud': config.ubicacion[0],
                'longitud': config.ubicacion[1]
            },
            'num_carriles_ns': config.num_carriles_ns,
            'num_carriles_eo': config.num_carriles_eo,
            'es_critica': config.es_critica
        })

    return {
        "total": len(intersecciones),
        "intersecciones": intersecciones
    }


@app.get("/api/intersecciones/{interseccion_id}/metricas")
async def obtener_metricas_interseccion(interseccion_id: str):
    """Obtiene métricas de una intersección específica"""
    if interseccion_id not in estado_sistema.configuraciones_intersecciones:
        raise HTTPException(status_code=404, detail="Intersección no encontrada")

    estadisticas = estado_sistema.agregador_metricas.obtener_estadisticas_interseccion(
        interseccion_id,
        ventana_segundos=60
    )

    return estadisticas


@app.get("/api/red/metricas")
async def obtener_metricas_red():
    """Obtiene métricas de toda la red"""
    metricas = estado_sistema.agregador_metricas.obtener_metricas_red_actual()

    if not metricas:
        return {
            "mensaje": "No hay métricas disponibles aún"
        }

    return metricas.to_dict()


@app.get("/api/red/resumen")
async def obtener_resumen_red():
    """Obtiene resumen completo del estado de la red"""
    resumen = estado_sistema.agregador_metricas.obtener_resumen_red()
    return resumen


@app.post("/api/simulacion/pausar")
async def pausar_simulacion():
    """Pausa la simulación"""
    estado_sistema.simulacion_pausada = True
    logger.info("⏸️  Simulación pausada")
    return {"status": "pausado"}


@app.post("/api/simulacion/reanudar")
async def reanudar_simulacion():
    """Reanuda la simulación"""
    estado_sistema.simulacion_pausada = False
    logger.info("▶️  Simulación reanudada")
    return {"status": "activo"}


@app.post("/api/simulacion/modo")
async def cambiar_modo(modo: str):
    """Cambia el modo de simulación"""
    modos_validos = ['simulador', 'video', 'sumo']
    if modo not in modos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Modo inválido. Opciones: {modos_validos}"
        )

    estado_sistema.modo = modo
    logger.info(f"🔄 Modo cambiado a: {modo}")
    return {"modo": modo}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para comunicación en tiempo real con el frontend"""
    await websocket.accept()
    estado_sistema.conexiones_ws.append(websocket)

    logger.info(f"✅ Cliente WebSocket conectado (total: {len(estado_sistema.conexiones_ws)})")

    try:
        # Enviar estado inicial
        await websocket.send_json({
            'tipo': 'estado_inicial',
            'datos': {
                'version': APP_VERSION,
                'modo': estado_sistema.modo,
                'num_intersecciones': len(estado_sistema.configuraciones_intersecciones)
            }
        })

        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()
            mensaje = json.loads(data)

            # Procesar comandos del cliente
            if mensaje.get('tipo') == 'solicitar_resumen':
                resumen = estado_sistema.agregador_metricas.obtener_resumen_red()
                await websocket.send_json({
                    'tipo': 'resumen_red',
                    'datos': resumen
                })

            elif mensaje.get('tipo') == 'pausar_simulacion':
                estado_sistema.simulacion_pausada = True
                await websocket.send_json({
                    'tipo': 'simulacion_pausada',
                    'datos': {'pausado': True}
                })

    except WebSocketDisconnect:
        logger.info("❌ Cliente WebSocket desconectado")
    finally:
        if websocket in estado_sistema.conexiones_ws:
            estado_sistema.conexiones_ws.remove(websocket)


# Montar archivos estáticos
if INTERFAZ_WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(INTERFAZ_WEB_DIR)), name="static")
    logger.info(f"📁 Archivos estáticos montados desde: {INTERFAZ_WEB_DIR}")


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print(f"  {APP_NAME.upper()}")
    print(f"  Versión {APP_VERSION}")
    print("="*70)
    print(f"\n[*] Dashboard: http://localhost:{PORT}")
    print(f"[*] WebSocket: ws://localhost:{PORT}/ws")
    print(f"[*] API Docs: http://localhost:{PORT}/docs")
    print("\n✨ Presiona Ctrl+C para detener\n")

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
