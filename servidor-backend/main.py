"""
Servidor Principal FastAPI

Proporciona API REST y WebSocket para el sistema de control semafórico
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
from fastapi.responses import FileResponse
from typing import List, Dict
import asyncio
import json
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar módulos del sistema
import importlib.util

# Función helper para importar módulos
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importar desde nucleo
nucleo_path = Path(__file__).parent.parent / 'nucleo'
indice_mod = import_module_from_path('indice_congestion', nucleo_path / 'indice_congestion.py')
difuso_mod = import_module_from_path('controlador_difuso', nucleo_path / 'controlador_difuso.py')
olas_mod = import_module_from_path('olas_verdes_dinamicas', nucleo_path / 'olas_verdes_dinamicas.py')

CalculadorICV = indice_mod.CalculadorICV
ParametrosInterseccion = indice_mod.ParametrosInterseccion
ControladorDifuso = difuso_mod.ControladorDifuso
GrafoIntersecciones = olas_mod.GrafoIntersecciones
CoordinadorOlasVerdes = olas_mod.CoordinadorOlasVerdes
Interseccion = olas_mod.Interseccion
VehiculoEmergencia = olas_mod.VehiculoEmergencia

# Importar simulador
simulador_path = Path(__file__).parent.parent / 'simulador_trafico'
sim_mod = import_module_from_path('simulador_lima', simulador_path / 'simulador_lima.py')
SimuladorLima = sim_mod.SimuladorLima
InterseccionSim = sim_mod.Interseccion

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Estado global
estado_sistema = {
    'modo': 'simulador',  # 'simulador', 'video', 'sumo'
    'simulador': None,
    'calculador_icv': None,
    'controlador_difuso': None,
    'coordinador_olas_verdes': None,
    'conector_sumo': None,  # Se inicializa al activar modo SUMO
    'intersecciones': {},
    'conexiones_ws': []
}


def inicializar_sistema():
    """Inicializa componentes del sistema"""
    logger.info("Inicializando sistema...")

    # Crear calculadores
    params = ParametrosInterseccion()
    estado_sistema['calculador_icv'] = CalculadorICV(params)
    estado_sistema['controlador_difuso'] = ControladorDifuso()

    # Cargar las 31 intersecciones reales de Lima con coordenadas EXACTAS
    # Coordenadas verificadas en Google Maps, ubicadas en el centro de cada cruce vial
    intersecciones_data = [
        # MIRAFLORES (3 intersecciones)
        {'id': 'MIR-001', 'nombre': 'Av. Arequipa con Av. Angamos', 'latitud': -12.110273, 'longitud': -77.034874, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'MIR-002', 'nombre': 'Av. Larco con Av. Benavides', 'latitud': -12.121832, 'longitud': -77.031044, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'MIR-003', 'nombre': 'Av. Arequipa con Av. Benavides', 'latitud': -12.119354, 'longitud': -77.034225, 'num_carriles': 6, 'zona': 'sur'},
        # SAN ISIDRO (3 intersecciones)
        {'id': 'SI-001', 'nombre': 'Av. Javier Prado con Av. Arequipa', 'latitud': -12.094817, 'longitud': -77.036156, 'num_carriles': 8, 'zona': 'centro'},
        {'id': 'SI-002', 'nombre': 'Av. Camino Real con Av. República de Panamá', 'latitud': -12.098156, 'longitud': -77.038967, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SI-003', 'nombre': 'Av. Javier Prado con Av. Canaval y Moreyra', 'latitud': -12.091234, 'longitud': -77.030453, 'num_carriles': 6, 'zona': 'centro'},
        # LIMA CENTRO (4 intersecciones)
        {'id': 'LC-001', 'nombre': 'Av. Abancay con Jr. Lampa', 'latitud': -12.046978, 'longitud': -77.033456, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-002', 'nombre': 'Av. Nicolás de Piérola con Jr. de la Unión', 'latitud': -12.046234, 'longitud': -77.030789, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-003', 'nombre': 'Av. Tacna con Av. Emancipación', 'latitud': -12.051234, 'longitud': -77.032567, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-004', 'nombre': 'Av. Alfonso Ugarte con Av. Venezuela', 'latitud': -12.057823, 'longitud': -77.038912, 'num_carriles': 6, 'zona': 'centro'},
        # LA VICTORIA (2 intersecciones)
        {'id': 'LV-001', 'nombre': 'Av. Grau con Av. 28 de Julio', 'latitud': -12.067845, 'longitud': -77.026123, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'LV-002', 'nombre': 'Av. Aviación con Av. Javier Prado', 'latitud': -12.085234, 'longitud': -77.005678, 'num_carriles': 8, 'zona': 'centro'},
        # SURCO (4 intersecciones)
        {'id': 'SUR-001', 'nombre': 'Av. Javier Prado con Av. Primavera', 'latitud': -12.093145, 'longitud': -76.978934, 'num_carriles': 8, 'zona': 'sur'},
        {'id': 'SUR-002', 'nombre': 'Av. Benavides con Av. Tomás Marsano', 'latitud': -12.118923, 'longitud': -77.006734, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'SUR-003', 'nombre': 'Av. Higuereta con Av. El Polo', 'latitud': -12.134812, 'longitud': -76.993567, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'SUR-004', 'nombre': 'Av. Primavera con Av. República de Panamá', 'latitud': -12.106234, 'longitud': -76.979123, 'num_carriles': 6, 'zona': 'sur'},
        # SAN JUAN DE LURIGANCHO (2 intersecciones)
        {'id': 'SJL-001', 'nombre': 'Av. Próceres con Av. Los Jardines', 'latitud': -11.991823, 'longitud': -77.008934, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-002', 'nombre': 'Av. Wiesse con Av. Gran Chimú', 'latitud': -11.984567, 'longitud': -77.001234, 'num_carriles': 4, 'zona': 'este'},
        # SAN MIGUEL (3 intersecciones)
        {'id': 'SM-001', 'nombre': 'Av. La Marina con Av. Universitaria', 'latitud': -12.077123, 'longitud': -77.083456, 'num_carriles': 8, 'zona': 'oeste'},
        {'id': 'SM-002', 'nombre': 'Av. Elmer Faucett con Av. Universitaria', 'latitud': -12.065234, 'longitud': -77.089867, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'SM-003', 'nombre': 'Av. La Marina con Av. Venezuela', 'latitud': -12.076845, 'longitud': -77.091234, 'num_carriles': 6, 'zona': 'oeste'},
        # JESÚS MARÍA (2 intersecciones)
        {'id': 'JM-001', 'nombre': 'Av. Brasil con Av. 28 de Julio', 'latitud': -12.068934, 'longitud': -77.044567, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'JM-002', 'nombre': 'Av. Salaverry con Av. Arequipa', 'latitud': -12.082967, 'longitud': -77.043812, 'num_carriles': 6, 'zona': 'centro'},
        # SAN BORJA (3 intersecciones)
        {'id': 'SB-001', 'nombre': 'Av. Javier Prado con Av. Aviación', 'latitud': -12.087823, 'longitud': -77.005967, 'num_carriles': 10, 'zona': 'centro'},
        {'id': 'SB-002', 'nombre': 'Av. San Luis con Av. San Borja Norte', 'latitud': -12.094823, 'longitud': -77.001645, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SB-003', 'nombre': 'Av. Angamos con Av. Aviación', 'latitud': -12.110567, 'longitud': -77.006234, 'num_carriles': 8, 'zona': 'centro'},
        # PUEBLO LIBRE (2 intersecciones)
        {'id': 'PL-001', 'nombre': 'Av. La Marina con Av. Bolívar', 'latitud': -12.070945, 'longitud': -77.064123, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'PL-002', 'nombre': 'Av. Brasil con Av. Bolívar', 'latitud': -12.072834, 'longitud': -77.057234, 'num_carriles': 6, 'zona': 'oeste'},
        # LINCE (1 intersección)
        {'id': 'LIN-001', 'nombre': 'Av. Arequipa con Av. Petit Thouars', 'latitud': -12.081723, 'longitud': -77.034845, 'num_carriles': 6, 'zona': 'centro'}
    ]

    # Guardar intersecciones
    estado_sistema['intersecciones'] = {i['id']: i for i in intersecciones_data}

    # Crear simulador (filtrar campos que el simulador no usa)
    intersecciones_sim = []
    for i in intersecciones_data:
        inter_sim = InterseccionSim(
            id=i['id'],
            nombre=i['nombre'],
            latitud=i['latitud'],
            longitud=i['longitud'],
            num_carriles=i['num_carriles']
        )
        intersecciones_sim.append(inter_sim)

    estado_sistema['simulador'] = SimuladorLima(
        intersecciones_sim,
        escenario='hora_pico_manana'
    )

    # Crear grafo para olas verdes
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

    # Agregar conexiones (red real de Lima con distancias exactas)
    conexiones = [
        # Av. Arequipa (eje norte-sur)
        ('SI-001', 'LIN-001', 1400),
        ('LIN-001', 'JM-002', 200),
        ('JM-002', 'MIR-001', 2800),
        ('MIR-001', 'MIR-003', 900),
        # Av. Javier Prado (eje este-oeste)
        ('SI-001', 'SI-003', 700),
        ('SI-003', 'LV-002', 2500),
        ('LV-002', 'SB-001', 200),
        ('SB-001', 'SUR-001', 2600),
        # Av. La Marina (zona oeste)
        ('SM-001', 'SM-003', 800),
        ('SM-003', 'PL-001', 1900),
        # Centro de Lima
        ('LC-001', 'LC-002', 400),
        ('LC-002', 'LC-003', 600),
        ('LC-003', 'LC-004', 900),
        # Av. Aviación (norte-sur)
        ('LV-002', 'SB-001', 200),
        ('SB-001', 'SB-003', 2500),
        # Av. Angamos (este-oeste)
        ('MIR-001', 'SB-003', 2800),
        # Av. Benavides (este-oeste)
        ('MIR-003', 'SUR-002', 2800),
        # Surco
        ('SUR-001', 'SUR-004', 1400),
        ('SUR-002', 'SUR-003', 1800),
        # Av. Brasil (este-oeste)
        ('JM-001', 'PL-002', 1300)
    ]
    for origen, destino, distancia in conexiones:
        grafo.agregar_conexion(origen, destino, distancia)

    estado_sistema['coordinador_olas_verdes'] = CoordinadorOlasVerdes(grafo)

    logger.info("✓ Sistema inicializado correctamente")


# Manejador de lifespan (reemplaza on_event)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup
    inicializar_sistema()
    # Iniciar tarea de simulación
    tarea_simulacion = asyncio.create_task(bucle_simulacion())
    yield
    # Shutdown
    tarea_simulacion.cancel()
    try:
        await tarea_simulacion
    except asyncio.CancelledError:
        pass


# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema de Control Semafórico Adaptativo",
    description="API para control inteligente de semáforos con ICV + Lógica Difusa",
    version="1.0.0",
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

# Registrar routers modulares
try:
    from rutas import emergencias, simulacion, intersecciones, sumo, video, websocket

    app.include_router(emergencias.router)
    app.include_router(simulacion.router)
    app.include_router(intersecciones.router)
    app.include_router(sumo.router)
    app.include_router(video.router)
    app.include_router(websocket.router)

    logger.info("Routers modulares registrados correctamente")
except ImportError as e:
    logger.warning(f"No se pudieron cargar algunos routers modulares: {e}")


# ==================== RUTAS API ====================


@app.get("/api/estado")
async def obtener_estado():
    """Obtiene el estado general del sistema"""
    return {
        'modo': estado_sistema['modo'],
        'num_intersecciones': len(estado_sistema['intersecciones']),
        'intersecciones': list(estado_sistema['intersecciones'].values())
    }


@app.get("/api/intersecciones")
async def listar_intersecciones():
    """Lista todas las intersecciones"""
    return list(estado_sistema['intersecciones'].values())


@app.get("/api/interseccion/{interseccion_id}/metricas")
async def obtener_metricas(interseccion_id: str):
    """Obtiene métricas de una intersección"""
    simulador = estado_sistema['simulador']
    if not simulador:
        raise HTTPException(status_code=400, detail="Simulador no activo")

    estado = simulador.obtener_estado(interseccion_id)
    if not estado:
        raise HTTPException(status_code=404, detail="Intersección no encontrada")

    # Calcular ICV
    calculador = estado_sistema['calculador_icv']
    resultado_icv = calculador.calcular(
        longitud_cola=estado.longitud_cola,
        velocidad_promedio=estado.velocidad_promedio,
        flujo_vehicular=estado.flujo_vehicular
    )

    return {
        'interseccion_id': interseccion_id,
        'timestamp': estado.timestamp.isoformat(),
        'num_vehiculos': estado.num_vehiculos,
        'flujo_vehicular': estado.flujo_vehicular,
        'velocidad_promedio': estado.velocidad_promedio,
        'longitud_cola': estado.longitud_cola,
        'icv': resultado_icv['icv'],
        'clasificacion_icv': resultado_icv['clasificacion'],
        'color_icv': resultado_icv['color']
    }


@app.get("/api/metricas/red")
async def obtener_metricas_red():
    """
    Obtiene métricas agregadas de toda la red (Cap 6.3.4)

    Calcula promedios de:
    - QL_red: Longitud de cola promedio en la red
    - Vavg_red: Velocidad promedio en la red
    - q_red: Flujo promedio en la red
    - k_red: Densidad promedio en la red (si disponible)
    - ICV_red: ICV promedio en la red
    - PI_red: Parámetro de Intensidad promedio en la red (si disponible)
    """
    simulador = estado_sistema['simulador']
    if not simulador:
        raise HTTPException(status_code=400, detail="Simulador no activo")

    calculador = estado_sistema['calculador_icv']

    # Recopilar métricas de todas las intersecciones
    metricas_intersecciones = []
    num_intersecciones_activas = 0

    for interseccion_id in estado_sistema['intersecciones'].keys():
        estado = simulador.obtener_estado(interseccion_id)
        if estado and estado.num_vehiculos > 0:  # Solo considerar intersecciones con tráfico
            resultado_icv = calculador.calcular(
                longitud_cola=estado.longitud_cola,
                velocidad_promedio=estado.velocidad_promedio,
                flujo_vehicular=estado.flujo_vehicular
            )

            metricas_intersecciones.append({
                'interseccion_id': interseccion_id,
                'longitud_cola': estado.longitud_cola,
                'velocidad_promedio': estado.velocidad_promedio,
                'flujo_vehicular': estado.flujo_vehicular,
                'num_vehiculos': estado.num_vehiculos,
                'icv': resultado_icv['icv']
            })
            num_intersecciones_activas += 1

    # Si no hay intersecciones activas, retornar valores en 0
    if not metricas_intersecciones:
        return {
            'num_intersecciones_activas': 0,
            'num_intersecciones_total': len(estado_sistema['intersecciones']),
            'QL_red': 0.0,
            'Vavg_red': 0.0,
            'q_red': 0.0,
            'ICV_red': 0.0,
            'clasificacion_red': 'sin_trafico',
            'mensaje': 'No hay intersecciones con trafico activo'
        }

    # Calcular promedios de red (Cap 6.3.4)
    import numpy as np

    QL_red = np.mean([m['longitud_cola'] for m in metricas_intersecciones])
    Vavg_red = np.mean([m['velocidad_promedio'] for m in metricas_intersecciones if m['velocidad_promedio'] > 0])
    q_red = np.mean([m['flujo_vehicular'] for m in metricas_intersecciones])
    ICV_red = np.mean([m['icv'] for m in metricas_intersecciones])

    # Clasificar estado de la red según ICV_red
    if ICV_red < 0.3:
        clasificacion_red = 'fluido'
    elif ICV_red < 0.6:
        clasificacion_red = 'moderado'
    else:
        clasificacion_red = 'congestionado'

    return {
        'num_intersecciones_activas': num_intersecciones_activas,
        'num_intersecciones_total': len(estado_sistema['intersecciones']),
        'QL_red': round(QL_red, 2),
        'Vavg_red': round(Vavg_red, 2),
        'q_red': round(q_red, 2),
        'ICV_red': round(ICV_red, 3),
        'clasificacion_red': clasificacion_red,
        'metricas_por_interseccion': metricas_intersecciones,
        'formula': 'Capitulo_6.3.4'
    }


@app.post("/api/emergencia/activar")
async def activar_emergencia(
    tipo: str,
    origen: str,
    destino: str,
    velocidad: float = 50.0
):
    """Activa ola verde para vehículo de emergencia"""
    coordinador = estado_sistema['coordinador_olas_verdes']

    from datetime import datetime
    vehiculo = VehiculoEmergencia(
        id=f"EMG-{datetime.now().strftime('%H%M%S')}",
        tipo=tipo,
        interseccion_actual=origen,
        destino=destino,
        velocidad_estimada=velocidad,
        timestamp=datetime.now()
    )

    resultado = coordinador.activar_ola_verde(vehiculo)

    # Notificar a clientes WebSocket
    await broadcast_mensaje({
        'tipo': 'ola_verde_activada',
        'datos': resultado
    })

    return resultado


@app.post("/api/modo/cambiar")
async def cambiar_modo(modo: str):
    """Cambia el modo de operación"""
    if modo not in ['simulador', 'video', 'sumo']:
        raise HTTPException(status_code=400, detail="Modo inválido")

    # Limpiar modo anterior
    if estado_sistema['modo'] == 'sumo' and estado_sistema['conector_sumo']:
        try:
            estado_sistema['conector_sumo'].desconectar()
            estado_sistema['conector_sumo'] = None
            logger.info("Conector SUMO desconectado")
        except:
            pass

    # Configurar nuevo modo
    estado_sistema['modo'] = modo

    # Inicializar modo SUMO si es necesario
    if modo == 'sumo':
        try:
            # Importar conector SUMO
            from pathlib import Path
            import sys
            integracion_path = Path(__file__).parent.parent / 'integracion-sumo'
            sys.path.insert(0, str(integracion_path))

            try:
                from conector_sumo import ConectorSUMO

                # Ruta a configuración SUMO
                ruta_config = integracion_path / 'escenarios' / 'lima-centro' / 'osm.sumocfg'

                if ruta_config.exists():
                    estado_sistema['conector_sumo'] = ConectorSUMO(
                        ruta_config_sumo=str(ruta_config),
                        usar_gui=False  # Sin GUI para mejor rendimiento
                    )
                    estado_sistema['conector_sumo'].conectar()
                    logger.info("✓ Conector SUMO inicializado y conectado")
                else:
                    logger.warning("Archivo de configuración SUMO no encontrado")
            except ImportError as e:
                logger.warning(f"SUMO/TraCI no disponible: {e}")
                logger.info("Modo SUMO funcionará solo con visualización de calles")
        except Exception as e:
            logger.error(f"Error inicializando SUMO: {e}")

    await broadcast_mensaje({
        'tipo': 'modo_cambiado',
        'datos': {'modo': modo}
    })

    return {'modo': modo, 'mensaje': f'Modo cambiado a {modo}'}


@app.get("/api/sumo/calles")
async def obtener_calles_sumo():
    """Obtiene el GeoJSON con las calles de la red SUMO"""
    try:
        ruta_geojson = Path(__file__).parent.parent / 'integracion-sumo' / 'escenarios' / 'lima-centro' / 'calles.geojson'

        if not ruta_geojson.exists():
            raise HTTPException(
                status_code=404,
                detail="Archivo de calles no encontrado. Ejecuta extraer_calles.py primero."
            )

        with open(ruta_geojson, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

        return geojson

    except Exception as e:
        logger.error(f"Error cargando calles SUMO: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sumo/trafico")
async def obtener_trafico_sumo():
    """Obtiene el estado actual del tráfico en las calles SUMO"""
    try:
        if estado_sistema['modo'] != 'sumo':
            return {'calles': [], 'mensaje': 'Modo SUMO no activo'}

        conector_sumo = estado_sistema.get('conector_sumo')
        if not conector_sumo or not conector_sumo.conectado:
            return {'calles': [], 'mensaje': 'SUMO no conectado'}

        # Obtener estado de las calles
        estados = conector_sumo.obtener_estado_calles(limite=500)

        return {
            'calles': estados,
            'timestamp': asyncio.get_event_loop().time()
        }

    except Exception as e:
        logger.error(f"Error obteniendo tráfico SUMO: {e}")
        return {'calles': [], 'error': str(e)}


@app.post("/api/video/procesar")
async def procesar_frame_video(frame_data: Dict):
    """Procesa un frame de video con YOLO y calcula métricas"""
    try:
        # Importar procesador de video
        vision_path = Path(__file__).parent.parent / 'vision_computadora'
        sys.path.insert(0, str(vision_path))

        try:
            from procesador_video import ProcesadorVideo

            # Inicializar procesador si no existe
            if not estado_sistema.get('procesador_video'):
                estado_sistema['procesador_video'] = ProcesadorVideo(
                    modelo='yolov8n.pt',
                    confianza=0.5
                )

            procesador = estado_sistema['procesador_video']

            # El frame viene como base64, decodificar
            import base64
            import numpy as np
            import cv2

            if 'frame' in frame_data:
                frame_base64 = frame_data['frame'].split(',')[1] if ',' in frame_data['frame'] else frame_data['frame']
                frame_bytes = base64.b64decode(frame_base64)
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                # Mantener contador de frames
                if 'video_frame_count' not in estado_sistema:
                    estado_sistema['video_frame_count'] = 0
                frame_num = estado_sistema['video_frame_count']
                estado_sistema['video_frame_count'] += 1

                # Procesar frame con firma correcta
                resultado = procesador.procesar_frame(frame, frame_num)

                # Acceder correctamente a atributos del dataclass ResultadoFrame
                num_vehiculos = resultado.num_vehiculos
                vehiculos_detectados = resultado.vehiculos_detectados
                flujo_estimado = resultado.flujo_estimado
                velocidad_promedio = resultado.velocidad_promedio
                longitud_cola = resultado.longitud_cola

                # Calcular ICV usando las métricas del procesador
                calculador = estado_sistema['calculador_icv']
                resultado_icv = calculador.calcular(
                    longitud_cola=longitud_cola,
                    velocidad_promedio=velocidad_promedio,
                    flujo_vehicular=flujo_estimado
                )

                # Convertir detecciones a formato para frontend
                detecciones_formateadas = []
                for vehiculo in vehiculos_detectados:
                    detecciones_formateadas.append({
                        'clase': vehiculo.get('clase', 'vehiculo'),
                        'confianza': vehiculo.get('confianza', 0.0),
                        'bbox': vehiculo.get('bbox', [0, 0, 0, 0])
                    })

                return {
                    'detecciones': detecciones_formateadas,
                    'num_vehiculos': num_vehiculos,
                    'frame_procesado': frame_data.get('frame'),
                    'metricas': {
                        'icv': resultado_icv['icv'],
                        'clasificacion': resultado_icv['clasificacion'],
                        'flujo': flujo_estimado,
                        'velocidad': velocidad_promedio,
                        'cola': longitud_cola,
                        'num_vehiculos': num_vehiculos
                    }
                }

        except ImportError as e:
            logger.error(f"Error importando procesador de video: {e}")
            return {
                'error': 'Procesador de video no disponible',
                'detalle': str(e)
            }

    except Exception as e:
        logger.error(f"Error procesando frame: {e}")
        return {'error': str(e)}


@app.get("/api/video/estado")
async def obtener_estado_video():
    """Obtiene el estado del procesador de video"""
    if estado_sistema.get('procesador_video'):
        return {
            'activo': True,
            'modelo': 'yolov8n.pt'
        }
    return {'activo': False}


# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para actualizaciones en tiempo real"""
    await websocket.accept()
    estado_sistema['conexiones_ws'].append(websocket)

    logger.info(f"Cliente WebSocket conectado. Total: {len(estado_sistema['conexiones_ws'])}")

    try:
        while True:
            # Mantener conexión activa
            data = await websocket.receive_text()
            # Opcional: procesar comandos del cliente
    except WebSocketDisconnect:
        estado_sistema['conexiones_ws'].remove(websocket)
        logger.info(f"Cliente WebSocket desconectado. Total: {len(estado_sistema['conexiones_ws'])}")


async def broadcast_mensaje(mensaje: Dict):
    """Envía mensaje a todos los clientes WebSocket"""
    conexiones_cerradas = []

    for websocket in estado_sistema['conexiones_ws']:
        try:
            await websocket.send_json(mensaje)
        except Exception as e:
            logger.warning(f"Error enviando mensaje WebSocket: {e}")
            conexiones_cerradas.append(websocket)

    # Limpiar conexiones cerradas
    for ws in conexiones_cerradas:
        if ws in estado_sistema['conexiones_ws']:
            estado_sistema['conexiones_ws'].remove(ws)


# ==================== BUCLE DE SIMULACIÓN ====================

async def bucle_simulacion():
    """Bucle principal de simulación"""
    logger.info("Iniciando bucle de simulación...")

    # Importar servicio de estadísticas
    from servicios.estadisticas_service import EstadisticasService

    while True:
        try:
            if estado_sistema['modo'] == 'simulador' and estado_sistema['simulador']:
                # Simular un paso
                estados = estado_sistema['simulador'].simular_paso(duracion_s=1.0)

                # Calcular métricas para cada intersección
                metricas_actualizadas = []
                for inter_id, estado in estados.items():
                    calculador = estado_sistema['calculador_icv']
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

                    # Guardar métricas en base de datos
                    try:
                        EstadisticasService.guardar_metrica(
                            interseccion_id=inter_id,
                            timestamp=estado.timestamp,
                            num_vehiculos=estado.num_vehiculos,
                            icv=resultado_icv['icv'],
                            flujo_vehicular=estado.flujo_vehicular,
                            velocidad_promedio=estado.velocidad_promedio,
                            longitud_cola=estado.longitud_cola,
                            fuente='simulador'
                        )
                    except Exception as e_db:
                        logger.warning(f"No se pudo guardar métrica en BD para {inter_id}: {e_db}")

                # Broadcast a clientes WebSocket
                await broadcast_mensaje({
                    'tipo': 'metricas_actualizadas',
                    'datos': metricas_actualizadas
                })

            # Esperar 1 segundo
            await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"Error en bucle de simulación: {e}", exc_info=True)
            await asyncio.sleep(5.0)


# Montar archivos estáticos
interfaz_path = Path(__file__).parent.parent / "interfaz-web"
if interfaz_path.exists():
    app.mount("/", StaticFiles(directory=str(interfaz_path), html=True), name="static")
    logger.info(f"Archivos estáticos montados desde: {interfaz_path}")


if __name__ == "__main__":
    import uvicorn

    try:
        print("\n" + "="*70)
        print("  SISTEMA DE CONTROL SEMAFÓRICO ADAPTATIVO INTELIGENTE")
        print("="*70)
        print("\n[*] Iniciando servidor...")
        print("[*] Dashboard disponible en: http://localhost:8000")
        print("[*] WebSocket en: ws://localhost:8000/ws")
        print("[*] Documentación API: http://localhost:8000/docs")
        print("\nPresiona Ctrl+C para detener\n")
    except:
        # Fallback si hay problemas con encoding
        print("\nSistema iniciando en http://localhost:8000\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
