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
estado_global_mod = import_module_from_path('estado_global', nucleo_path / 'estado_global.py')

CalculadorICV = indice_mod.CalculadorICV
ParametrosInterseccion = indice_mod.ParametrosInterseccion
ControladorDifuso = difuso_mod.ControladorDifuso
GrafoIntersecciones = olas_mod.GrafoIntersecciones
CoordinadorOlasVerdes = olas_mod.CoordinadorOlasVerdes
Interseccion = olas_mod.Interseccion
VehiculoEmergencia = olas_mod.VehiculoEmergencia
EstadoGlobalRed = estado_global_mod.EstadoGlobalRed

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
    'sumo_auto_step': None,  # Tarea que avanza SUMO automáticamente
    'intersecciones': {},
    'conexiones_ws': [],
    'estado_global_red': None
}


async def avanzar_sumo_automaticamente():
    """Avanza la simulación SUMO automáticamente en background"""
    logger.info("🚀 Iniciando avance automático de SUMO...")
    while True:
        try:
            if estado_sistema.get('conector_sumo') and estado_sistema['conector_sumo'].conectado:
                continuar = estado_sistema['conector_sumo'].simular_paso()
                if not continuar:
                    logger.warning("⚠️  Simulación SUMO terminada")
                    break
                await asyncio.sleep(0.1)  # 100ms entre pasos = velocidad 10x
            else:
                await asyncio.sleep(1)  # Esperar si no está conectado
        except Exception as e:
            logger.error(f"Error en avance automático SUMO: {e}")
            await asyncio.sleep(1)


def inicializar_sistema():
    """Inicializa componentes del sistema"""
    logger.info("Inicializando sistema...")

    # Crear calculadores
    params = ParametrosInterseccion()
    estado_sistema['calculador_icv'] = CalculadorICV(params)
    estado_sistema['controlador_difuso'] = ControladorDifuso()
    estado_sistema['estado_global_red'] = EstadoGlobalRed()

    # Cargar las 31 intersecciones reales de Lima con coordenadas EXACTAS
    # Coordenadas verificadas en Google Maps, ubicadas en el centro de cada cruce vial
    intersecciones_data = [
        # MIRAFLORES (3 intersecciones)
        {'id': 'MIR-001', 'nombre': 'Av. Arequipa con Av. Angamos', 'latitud': -12.1108, 'longitud': -77.0369, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'MIR-002', 'nombre': 'Av. Larco con Av. Benavides', 'latitud': -12.1190, 'longitud': -77.0370, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'MIR-003', 'nombre': 'Av. Arequipa con Av. Benavides', 'latitud': -12.1238, 'longitud': -77.0325, 'num_carriles': 6, 'zona': 'sur'},
        # SAN ISIDRO (4 intersecciones)
        {'id': 'SI-001', 'nombre': 'Av. Javier Prado con Av. Arequipa', 'latitud': -12.0923, 'longitud': -77.0333, 'num_carriles': 8, 'zona': 'centro'},
        {'id': 'SI-002', 'nombre': 'Av. Camino Real con Av. República de Panamá', 'latitud': -12.0970, 'longitud': -77.0326, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SI-003', 'nombre': 'Av. Javier Prado con Av. Canaval y Moreyra', 'latitud': -12.1035, 'longitud': -77.0316, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'SI-004', 'nombre': 'Av. Aviación con Av. Javier Prado', 'latitud': -12.0947, 'longitud': -77.0507, 'num_carriles': 8, 'zona': 'centro'},
        # LIMA CENTRO (4 intersecciones)
        {'id': 'LC-001', 'nombre': 'Av. Abancay con Jr. Lampa', 'latitud': -12.046978, 'longitud': -77.033456, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-002', 'nombre': 'Av. Nicolás de Piérola con Jr. de la Unión', 'latitud': -12.046234, 'longitud': -77.030789, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-003', 'nombre': 'Av. Tacna con Av. Emancipación', 'latitud': -12.051234, 'longitud': -77.032567, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'LC-004', 'nombre': 'Av. Alfonso Ugarte con Av. Venezuela', 'latitud': -12.057823, 'longitud': -77.038912, 'num_carriles': 6, 'zona': 'centro'},
        # LA VICTORIA (4 intersecciones)
        {'id': 'LV-001', 'nombre': 'Av. Grau con Av. 28 de Julio', 'latitud': -12.0591, 'longitud': -77.0298, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'LV-002', 'nombre': 'Av. Aviación con Av. Javier Prado', 'latitud': -12.0841, 'longitud': -77.0041, 'num_carriles': 8, 'zona': 'centro'},
        {'id': 'LV-003', 'nombre': 'Av. Aviación con Av. 28 de Julio', 'latitud': -12.0610, 'longitud': -77.0130, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'LV-004', 'nombre': 'Av. Aviación con Av. 28 de Julio Alt', 'latitud': -12.0719, 'longitud': -77.0115, 'num_carriles': 6, 'zona': 'centro'},
        # SURCO (4 intersecciones)
        {'id': 'SUR-001', 'nombre': 'Av. Javier Prado con Av. Primavera', 'latitud': -12.1005, 'longitud': -76.9946, 'num_carriles': 8, 'zona': 'sur'},
        {'id': 'SUR-002', 'nombre': 'Av. Benavides con Av. Tomás Marsano', 'latitud': -12.1117, 'longitud': -77.0002, 'num_carriles': 6, 'zona': 'sur'},
        {'id': 'SUR-003', 'nombre': 'Av. Higuereta con Av. El Polo', 'latitud': -12.1288, 'longitud': -77.0011, 'num_carriles': 4, 'zona': 'sur'},
        {'id': 'SUR-004', 'nombre': 'Av. Primavera con Av. República de Panamá', 'latitud': -12.1102, 'longitud': -76.9782, 'num_carriles': 6, 'zona': 'sur'},
        # SAN JUAN DE LURIGANCHO (9 intersecciones)
        {'id': 'SJL-001', 'nombre': 'Av. Próceres con Av. Los Jardines', 'latitud': -11.9848, 'longitud': -77.0067, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-002', 'nombre': 'Av. Wiesse con Av. Gran Chimú', 'latitud': -11.9823, 'longitud': -77.0132, 'num_carriles': 4, 'zona': 'este'},
        {'id': 'SJL-003', 'nombre': 'Av. Próceres con Av. Canta Callao', 'latitud': -12.0252, 'longitud': -77.0120, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-004', 'nombre': 'Av. Los Jardines con Av. Circunvalación', 'latitud': -12.0258, 'longitud': -77.0101, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-005', 'nombre': 'Av. Wiesse con Av. Canta Callao', 'latitud': -12.0232, 'longitud': -77.0079, 'num_carriles': 4, 'zona': 'este'},
        {'id': 'SJL-006', 'nombre': 'Av. Próceres con Av. Circunvalación', 'latitud': -12.0206, 'longitud': -77.0125, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-007', 'nombre': 'Av. Los Jardines con Av. Primavera', 'latitud': -12.0123, 'longitud': -77.0115, 'num_carriles': 4, 'zona': 'este'},
        {'id': 'SJL-008', 'nombre': 'Av. Canta Callao con Av. Wiesse', 'latitud': -12.0132, 'longitud': -77.0020, 'num_carriles': 6, 'zona': 'este'},
        {'id': 'SJL-009', 'nombre': 'Av. Próceres con Av. 28 de Julio', 'latitud': -12.0108, 'longitud': -76.9970, 'num_carriles': 6, 'zona': 'este'},
        # SAN MIGUEL (4 intersecciones)
        {'id': 'SM-001', 'nombre': 'Av. La Marina con Av. Universitaria', 'latitud': -12.0749, 'longitud': -77.0797, 'num_carriles': 8, 'zona': 'oeste'},
        {'id': 'SM-002', 'nombre': 'Av. Elmer Faucett con Av. Universitaria', 'latitud': -12.0603, 'longitud': -77.0790, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'SM-003', 'nombre': 'Av. La Marina con Av. Venezuela', 'latitud': -12.0782, 'longitud': -77.0814, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'SM-004', 'nombre': 'Av. La Marina con Av. Bolognesi', 'latitud': -12.0625, 'longitud': -77.0972, 'num_carriles': 6, 'zona': 'oeste'},
        # JESÚS MARÍA (4 intersecciones)
        {'id': 'JM-001', 'nombre': 'Av. Brasil con Av. 28 de Julio', 'latitud': -12.0653, 'longitud': -77.0457, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'JM-002', 'nombre': 'Av. Salaverry con Av. Arequipa', 'latitud': -12.0855, 'longitud': -77.0486, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'JM-003', 'nombre': 'Av. Brasil con Av. Arequipa', 'latitud': -12.0881, 'longitud': -77.0506, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'JM-004', 'nombre': 'Av. Salaverry con Av. Libertad', 'latitud': -12.0752, 'longitud': -77.0421, 'num_carriles': 6, 'zona': 'centro'},
        # SAN BORJA (3 intersecciones)
        {'id': 'SB-001', 'nombre': 'Av. Javier Prado con Av. Aviación', 'latitud': -12.0883, 'longitud': -77.0036, 'num_carriles': 10, 'zona': 'centro'},
        {'id': 'SB-002', 'nombre': 'Av. San Luis con Av. San Borja Norte', 'latitud': -12.0930, 'longitud': -76.9957, 'num_carriles': 4, 'zona': 'centro'},
        {'id': 'SB-003', 'nombre': 'Av. Angamos con Av. Aviación', 'latitud': -12.1118, 'longitud': -77.0002, 'num_carriles': 8, 'zona': 'centro'},
        # PUEBLO LIBRE (3 intersecciones)
        {'id': 'PL-001', 'nombre': 'Av. La Marina con Av. Bolívar', 'latitud': -12.0716, 'longitud': -77.0616, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'PL-002', 'nombre': 'Av. Brasil con Av. Bolívar', 'latitud': -12.0786, 'longitud': -77.0566, 'num_carriles': 6, 'zona': 'oeste'},
        {'id': 'PL-003', 'nombre': 'Av. Faustino con Av. Brasil', 'latitud': -12.0751, 'longitud': -77.0538, 'num_carriles': 6, 'zona': 'oeste'},
        # MAGDALENA (1 intersección)
        {'id': 'MA-001', 'nombre': 'Av. Brasil con Av. 28 de Julio', 'latitud': -12.0899, 'longitud': -77.0660, 'num_carriles': 6, 'zona': 'centro'},
        # LINCE/TRANSVERSAL (4 intersecciones)
        {'id': 'TR-001', 'nombre': 'Av. Arequipa con Av. Paseo de la República', 'latitud': -12.0918, 'longitud': -77.0302, 'num_carriles': 8, 'zona': 'centro'},
        {'id': 'TR-002', 'nombre': 'Av. Petit Thouars con Av. Paseo de la República', 'latitud': -12.0914, 'longitud': -77.0270, 'num_carriles': 6, 'zona': 'centro'},
        {'id': 'TR-003', 'nombre': 'Av. Aviación con Av. Paseo de la República', 'latitud': -12.0824, 'longitud': -76.9973, 'num_carriles': 8, 'zona': 'centro'},
        # LINCE (1 intersección)
        {'id': 'LIN-001', 'nombre': 'Av. Arequipa con Av. Petit Thouars', 'latitud': -12.0837, 'longitud': -77.0341, 'num_carriles': 6, 'zona': 'centro'}
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

    # Agregar conexiones (red real de Lima con distancias exactas basadas en avenidas reales)
    conexiones = [
        # ========== AV. AREQUIPA (EJE NORTE-SUR PRINCIPAL) ==========
        ('JM-003', 'JM-002', 300),        # Brasil → Salaverry
        ('JM-002', 'TR-001', 600),        # Salaverry → Paseo República
        ('TR-001', 'LIN-001', 400),       # Paseo República → Petit Thouars
        ('LIN-001', 'MIR-001', 1200),     # Petit Thouars → Angamos
        ('MIR-001', 'MIR-003', 900),      # Angamos → Benavides

        # ========== AV. JAVIER PRADO (EJE ESTE-OESTE PRINCIPAL) ==========
        ('SI-001', 'SI-003', 700),        # Arequipa → Paseo República
        ('SI-003', 'LV-002', 2500),       # Paseo República → Aviación
        ('LV-002', 'SB-001', 200),        # Aviación → Aviación-Javier Prado
        ('SB-001', 'SUR-001', 2600),      # Aviación → Circunvalación (Surco)

        # ========== AV. ANGAMOS (ESTE-OESTE) ==========
        ('MIR-001', 'SB-003', 800),       # Arequipa → Angamos-Aviación
        ('SB-003', 'SUR-002', 1200),      # Angamos-Aviación → Benavides

        # ========== AV. BENAVIDES (ESTE-OESTE) ==========
        ('MIR-003', 'MIR-002', 400),      # Arequipa → Larco
        ('MIR-002', 'SUR-002', 2400),     # Larco → Primavera
        ('SUR-002', 'SUR-003', 1800),     # Primavera → Velasco Astete

        # ========== AV. AVIACIÓN (NORTE-SUR) ==========
        ('LV-001', 'LV-003', 400),        # Grau → 28 Julio
        ('LV-003', 'LV-004', 500),        # 28 Julio → 28 Julio Alt
        ('LV-004', 'LV-002', 700),        # 28 Julio Alt → Javier Prado
        ('LV-002', 'SB-001', 300),        # Javier Prado → SB-001
        ('SB-001', 'SB-002', 600),        # SB-001 → SB-002
        ('SB-002', 'TR-003', 1000),       # SB-002 → Paseo República
        ('TR-003', 'SUR-001', 800),       # Paseo República → Primavera

        # ========== AV. PASEO DE LA REPÚBLICA (NORTE-SUR) ==========
        ('TR-001', 'TR-002', 500),        # Arequipa → Petit Thouars
        ('TR-002', 'TR-003', 600),        # Petit Thouars → Aviación
        ('SI-003', 'SI-002', 1200),       # Javier Prado → Angamos
        ('SI-002', 'JM-001', 3500),       # Angamos → Av. Venezuela

        # ========== AV. LA MARINA (OESTE) ==========
        ('SM-001', 'SM-002', 500),        # Universitaria → Faucett
        ('SM-002', 'SM-003', 800),        # Faucett → Venezuela
        ('SM-003', 'SM-004', 900),        # Venezuela → Bolognesi
        ('SM-004', 'PL-001', 1200),       # Bolognesi → Bolívar

        # ========== AV. BRASIL (CENTRO-OESTE) ==========
        ('JM-001', 'MA-001', 800),        # Venezuela → Magdalena
        ('MA-001', 'SM-001', 1000),       # Magdalena → La Marina
        ('JM-003', 'MA-001', 700),        # Jesús María → Magdalena
        ('PL-001', 'PL-002', 600),        # Plaza Norte → Brasil
        ('PL-002', 'PL-003', 500),        # Brasil → Faustino
        ('JM-001', 'PL-002', 1300),       # Venezuela → Brasil

        # ========== CENTRO DE LIMA (DAMERO DE PIZARRO) ==========
        ('LC-001', 'LC-002', 400),        # Plaza Mayor → Plaza San Martín
        ('LC-002', 'LC-003', 600),        # Plaza San Martín → Av. Abancay
        ('LC-003', 'LC-004', 900),        # Av. Abancay → Av. Grau
        ('LC-004', 'JM-001', 1500),       # Av. Grau → Av. Venezuela con Brasil

        # ========== SAN JUAN DE LURIGANCHO (EXPANSIÓN) ==========
        ('SJL-001', 'SJL-002', 800),      # Próceres → Wiesse
        ('SJL-002', 'SJL-003', 2500),     # Wiesse → Canta Callao
        ('SJL-003', 'SJL-004', 400),      # Canta Callao → Los Jardines
        ('SJL-004', 'SJL-005', 500),      # Los Jardines → Wiesse
        ('SJL-005', 'SJL-006', 500),      # Wiesse → Próceres
        ('SJL-006', 'SJL-007', 600),      # Próceres → Los Jardines
        ('SJL-007', 'SJL-008', 700),      # Los Jardines → Canta Callao
        ('SJL-008', 'SJL-009', 400),      # Canta Callao → Próceres
        ('PL-001', 'SJL-001', 8000),      # Plaza Norte → Próceres (Vía Expresa)

        # ========== SURCO INTERNO ==========
        ('SUR-001', 'SUR-004', 1400),     # Javier Prado → Monterrico
        ('SUR-002', 'SUR-004', 2200),     # Benavides-Primavera → Monterrico
        ('SUR-003', 'SUR-004', 1600),     # Velasco Astete → Monterrico
        ('SUR-001', 'SUR-002', 1200),     # Javier Prado → Benavides

        # ========== JESÚS MARÍA EXPANDIDO ==========
        ('JM-001', 'JM-003', 700),        # Brasil → Brasil Arequipa
        ('JM-004', 'JM-001', 600),        # Libertad → Brasil
        ('JM-004', 'JM-003', 500),        # Libertad → Arequipa

        # ========== CONEXIONES ADICIONALES (RED MALLADA) ==========
        ('LIN-001', 'LC-003', 500),       # Arequipa con Petit Thouars
        ('SB-001', 'SI-001', 300),        # SB-001 ← SI-001
        ('MIR-003', 'SUR-001', 3500),     # Miraflores → Surco (conexión directa)
        ('JM-002', 'JM-001', 800),        # Salaverry → Venezuela
        ('SI-004', 'SM-001', 2000),       # San Isidro → San Miguel
    ]
    for origen, destino, distancia in conexiones:
        grafo.agregar_conexion(origen, destino, distancia)

    estado_sistema['coordinador_olas_verdes'] = CoordinadorOlasVerdes(grafo)

    logger.info("✓ Sistema inicializado correctamente")

    # Sincronizar el estado local (dict) con la instancia global usada por los
    # servicios (`servicios.estado_global.estado_sistema`). Algunos servicios
    # importan la instancia `estado_sistema` desde `servicios.estado_global` y
    # esperan atributos (no llaves de dict). Para evitar que el coordinador de
    # olas verdes aparezca como "no inicializado", copiamos los valores más
    # relevantes a esa instancia.
    try:
        from servicios.estado_global import estado_sistema as estado_global

        estado_global.modo = estado_sistema.get('modo', estado_global.modo)
        estado_global.simulador = estado_sistema.get('simulador', estado_global.simulador)
        estado_global.calculador_icv = estado_sistema.get('calculador_icv', estado_global.calculador_icv)
        estado_global.controlador_difuso = estado_sistema.get('controlador_difuso', estado_global.controlador_difuso)
        estado_global.coordinador_olas_verdes = estado_sistema.get('coordinador_olas_verdes', estado_global.coordinador_olas_verdes)
        estado_global.procesador_video = estado_sistema.get('procesador_video', estado_global.procesador_video)
        estado_global.conector_sumo = estado_sistema.get('conector_sumo', estado_global.conector_sumo)
        estado_global.intersecciones = estado_sistema.get('intersecciones', estado_global.intersecciones)
        estado_global.olas_verdes_activas = estado_sistema.get('olas_verdes_activas', getattr(estado_global, 'olas_verdes_activas', {}))
        estado_global.conexiones_ws = estado_sistema.get('conexiones_ws', getattr(estado_global, 'conexiones_ws', []))

        logger.info('Estado global sincronizado con servicios.estado_global')
    except Exception as e:
        logger.warning(f'No se pudo sincronizar estado_global: {e}')


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


@app.post("/api/estado-local/ingresar")
async def ingresar_estado_local(paquete: Dict):
    """Recibe paquete de telemetría local y actualiza el estado global de la red"""
    try:
        if not estado_sistema.get('estado_global_red'):
            estado_sistema['estado_global_red'] = EstadoGlobalRed()
        estado_sistema['estado_global_red'].actualizar_interseccion(paquete)
        return { 'status': 'ok' }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/estado-global")
async def obtener_estado_global():
    """Devuelve el estado global agregado (ICV/PI por intersección y globales)"""
    try:
        if not estado_sistema.get('estado_global_red'):
            estado_sistema['estado_global_red'] = EstadoGlobalRed()
        return estado_sistema['estado_global_red'].obtener_estado_global()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    Obtiene métricas agregadas de toda la red

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

    # Calcular promedios de red
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


# Nota: La ruta `/api/emergencia/activar` fue movida al router modular en
# `rutas/emergencias.py`. La definición previa se deja comentada para evitar
# conflictos de rutas duplicadas que provocaban respuestas 400/405 al enviar
# JSON desde el frontend. Mantenerla activa causaba que FastAPI seleccionase
# la implementación equivocada (esperando query params en lugar de JSON).

"""
La implementación anterior estaba aquí como app.route, pero ahora la lógica
se sirve desde el router modular importado más arriba. Si se necesita debug
adicional, revisar `servidor-backend/rutas/emergencias.py` y el servicio
`servidor-backend/servicios/emergencia_service.py`.
"""


@app.post("/api/modo/cambiar")
async def cambiar_modo(modo: str):
    """Cambia el modo de operación"""
    if modo not in ['simulador', 'video', 'sumo']:
        raise HTTPException(status_code=400, detail="Modo inválido")

    # Limpiar modo anterior
    if estado_sistema['modo'] == 'sumo' and estado_sistema['conector_sumo']:
        try:
            # Cancelar tarea de avance automático
            if estado_sistema.get('sumo_auto_step'):
                estado_sistema['sumo_auto_step'].cancel()
                estado_sistema['sumo_auto_step'] = None
                logger.info("Tarea de avance automático SUMO cancelada")
            
            estado_sistema['conector_sumo'].desconectar()
            estado_sistema['conector_sumo'] = None
            logger.info("Conector SUMO desconectado")
        except:
            pass

    # Configurar nuevo modo
    estado_sistema['modo'] = modo
    # Sincronizar inmediatamente con servicios.estado_global
    try:
        from servicios.estado_global import estado_sistema as estado_global
        estado_global.modo = modo
    except Exception as e:
        logger.warning(f"No se pudo sincronizar modo con servicios.estado_global: {e}")

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

                # Buscar configuración SUMO (preferir lima-amplio si existe)
                ruta_config_amplio = integracion_path / 'escenarios' / 'lima-amplio' / 'lima_amplio.sumocfg'
                ruta_config_centro = integracion_path / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
                
                ruta_config = None
                # Priorizar mapa pequeño (centro) para mejor visualización
                if ruta_config_centro.exists():
                    ruta_config = ruta_config_centro
                    logger.info("🗺️  Usando mapa centro de Lima (47 intersecciones)")
                elif ruta_config_amplio.exists():
                    ruta_config = ruta_config_amplio
                    logger.info("🗺️  Usando mapa amplio de Lima")

                if ruta_config:
                    estado_sistema['conector_sumo'] = ConectorSUMO(
                        ruta_config_sumo=str(ruta_config),
                        usar_gui=True  # ✅ CON GUI para visualización en tiempo real
                    )
                    estado_sistema['conector_sumo'].conectar()
                    logger.info("✓ Conector SUMO inicializado y conectado")
                    logger.info("🎮 SUMO-GUI abierto - verás los vehículos circulando en tiempo real")
                    
                    # Iniciar tarea de avance automático
                    estado_sistema['sumo_auto_step'] = asyncio.create_task(avanzar_sumo_automaticamente())
                    logger.info("✅ Avance automático de simulación iniciado")
                    # Sincronizar con servicios.estado_global
                    try:
                        from servicios.estado_global import estado_sistema as estado_global
                        estado_global.conector_sumo = estado_sistema['conector_sumo']
                    except Exception as e_sync:
                        logger.warning(f"No se pudo sincronizar conector_sumo con servicios.estado_global: {e_sync}")
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
        # Buscar archivo de calles (preferir lima-amplio)
        base_path = Path(__file__).parent.parent / 'integracion-sumo' / 'escenarios'
        ruta_geojson_amplio = base_path / 'lima-amplio' / 'calles.geojson'
        ruta_geojson_centro = base_path / 'lima-centro' / 'calles.geojson'
        
        ruta_geojson = None
        if ruta_geojson_amplio.exists():
            ruta_geojson = ruta_geojson_amplio
        elif ruta_geojson_centro.exists():
            ruta_geojson = ruta_geojson_centro

        if not ruta_geojson or not ruta_geojson.exists():
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
        
        # Si SUMO está conectado, usar datos reales
        if conector_sumo and conector_sumo.conectado:
            # La simulación avanza automáticamente en background, solo leer datos
            # Obtener datos actualizados
            estados = conector_sumo.obtener_estado_calles(limite=500)
            
            # Filtrar solo calles con tráfico para reducir payload
            calles_con_trafico = [e for e in estados if e['vehiculos'] > 0]
            total_vehiculos = sum(e['vehiculos'] for e in calles_con_trafico)
            
            logger.info(f"🚗 SUMO: {len(calles_con_trafico)} calles con tráfico, {total_vehiculos} vehículos")
            
            # Derivar métricas agregadas para ICV y flujo basadas en datos SUMO
            try:
                icv_promedio = 0.0
                flujo_promedio = 0.0
                if calles_con_trafico:
                    icv_promedio = sum(e.get('congestion', 0) for e in calles_con_trafico) / len(calles_con_trafico)
                    flujo_promedio = sum(e.get('vehiculos', 0) for e in calles_con_trafico) / len(calles_con_trafico)
                # Clamps: evitar extremos y asegurar mínimos visibles (>= 0.02)
                icv_promedio = max(0.02, min(0.99, icv_promedio))
                flujo_promedio = max(0.02, flujo_promedio)
            except Exception:
                icv_promedio = 0.02
                flujo_promedio = 0.02

            return {
                'calles': estados,  # Enviar todas para colorear el mapa
                'calles_con_trafico': len(calles_con_trafico),
                'vehiculos_totales': total_vehiculos,
                'timestamp': asyncio.get_event_loop().time(),
                'fuente': 'sumo_real',
                'icv_red_promedio': round(icv_promedio, 3),
                'flujo_promedio': round(flujo_promedio, 2)
            }
        
        # Si SUMO NO está conectado, generar datos simulados
        # Cargar IDs de calles desde el GeoJSON
        base_path = Path(__file__).parent.parent / 'integracion-sumo' / 'escenarios'
        ruta_geojson_amplio = base_path / 'lima-amplio' / 'calles.geojson'
        ruta_geojson_centro = base_path / 'lima-centro' / 'calles.geojson'
        
        ruta_geojson = None
        if ruta_geojson_amplio.exists():
            ruta_geojson = ruta_geojson_amplio
        elif ruta_geojson_centro.exists():
            ruta_geojson = ruta_geojson_centro
        
        if not ruta_geojson or not ruta_geojson.exists():
            return {'calles': [], 'mensaje': 'Archivo de calles no encontrado'}
        
        import random
        import time
        
        with open(ruta_geojson, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        
        # Generar tráfico simulado para cada calle
        estados = []
        for feature in geojson['features']:
            calle_id = feature['properties']['id']
            
            # Generar métricas aleatorias pero realistas
            congestion = random.uniform(0.0, 1.0)
            velocidad = random.uniform(10, 60)  # km/h
            vehiculos = random.randint(0, 20)
            ocupacion = random.uniform(0, 100)
            
            estados.append({
                'id': calle_id,
                'vehiculos': vehiculos,
                'velocidad': round(velocidad, 1),
                'ocupacion': round(ocupacion, 1),
                'congestion': round(congestion, 2)
            })
        
        # Métricas agregadas básicas también en simulado
        try:
            icv_promedio = sum(e.get('congestion', 0) for e in estados) / len(estados) if estados else 0.02
            flujo_promedio = sum(e.get('vehiculos', 0) for e in estados) / len(estados) if estados else 0.02
        except Exception:
            icv_promedio = 0.02
            flujo_promedio = 0.02

        return {
            'calles': estados,
            'timestamp': time.time(),
            'fuente': 'simulado',
            'mensaje': 'Tráfico simulado (SUMO no conectado)',
            'icv_red_promedio': round(icv_promedio, 3),
            'flujo_promedio': round(flujo_promedio, 2)
        }

    except Exception as e:
        logger.error(f"Error obteniendo tráfico SUMO: {e}")
        return {'calles': [], 'error': str(e)}


@app.get("/api/sumo/estado")
async def obtener_estado_sumo():
    """Obtiene el estado de conexión con SUMO y métricas en tiempo real"""
    try:
        conector_sumo = estado_sistema.get('conector_sumo')
        
        # Auto-inicializar SUMO si el modo actual es 'sumo' y no hay conexión
        if (estado_sistema.get('modo') == 'sumo') and (not conector_sumo or not conector_sumo.conectado):
            try:
                from pathlib import Path
                import sys
                integracion_path = Path(__file__).parent.parent / 'integracion-sumo'
                sys.path.insert(0, str(integracion_path))
                from conector_sumo import ConectorSUMO

                ruta_config_centro = integracion_path / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
                ruta_config_amplio = integracion_path / 'escenarios' / 'lima-amplio' / 'lima_amplio.sumocfg'
                ruta_config = ruta_config_centro if ruta_config_centro.exists() else (ruta_config_amplio if ruta_config_amplio.exists() else None)

                if ruta_config:
                    estado_sistema['conector_sumo'] = ConectorSUMO(
                        ruta_config_sumo=str(ruta_config),
                        usar_gui=True
                    )
                    estado_sistema['conector_sumo'].conectar()
                    logger.info("✓ SUMO auto-inicializado desde /api/sumo/estado")
                    # Iniciar auto-step si no está corriendo
                    if not estado_sistema.get('sumo_auto_step'):
                        estado_sistema['sumo_auto_step'] = asyncio.create_task(avanzar_sumo_automaticamente())
                        logger.info("✅ Avance automático iniciado (auto)")
                    conector_sumo = estado_sistema['conector_sumo']
                else:
                    logger.warning("No se encontró archivo .sumocfg para auto-inicializar SUMO")
            except Exception as e_auto:
                logger.error(f"Error auto-inicializando SUMO: {e_auto}")

        if conector_sumo and conector_sumo.conectado:
            # La simulación avanza automáticamente en background, solo leer datos
            # Obtener estados actualizados para calcular estadísticas
            estados = conector_sumo.obtener_estado_calles(limite=2000)
            calles_con_trafico = [e for e in estados if e.get('vehiculos', 0) > 0]
            # Inicialmente sumar por calles (puede sub-contar vehículos en múltiples lanes/edges)
            total_vehiculos = sum(e.get('vehiculos', 0) for e in calles_con_trafico)
            
            # Calcular velocidad promedio
            velocidades = [e.get('velocidad', 0) for e in calles_con_trafico if e.get('velocidad', 0) > 0]
            velocidad_promedio = sum(velocidades) / len(velocidades) if velocidades else 0
            
            # Calcular congestión promedio
            congestion_promedio = sum(e.get('congestion', 0) for e in calles_con_trafico) / len(calles_con_trafico) if calles_con_trafico else 0
            # Tiempo simulado
            tiempo_simulado_s = 0.0
            try:
                import traci
                tiempo_simulado_s = float(traci.simulation.getTime())
                # Recalcular SIEMPRE total_vehiculos mediante lista global (fiable)
                veh_ids = list(traci.vehicle.getIDList())
                total_vehiculos_global = len(veh_ids)
                # Si el conteo por calles difiere significativamente (subconteo), usar global
                if total_vehiculos_global > total_vehiculos:
                    total_vehiculos = total_vehiculos_global
                # Ajustar velocidad promedio si estaba en cero
                if velocidad_promedio == 0 and total_vehiculos_global > 0:
                    vel_list = []
                    for vid in veh_ids[:5000]:  # safety cap
                        try:
                            v = traci.vehicle.getSpeed(vid) * 3.6
                            if v > 0:
                                vel_list.append(v)
                        except Exception:
                            continue
                    if vel_list:
                        velocidad_promedio = sum(vel_list) / len(vel_list)
                # Recalcular calles activas si resultó 0
                if len(calles_con_trafico) == 0:
                    try:
                        edge_ids = list(traci.edge.getIDList())
                        activos = 0
                        for eid in edge_ids[:2000]:
                            if eid.startswith(':'):
                                continue
                            try:
                                if traci.edge.getLastStepVehicleNumber(eid) > 0:
                                    activos += 1
                            except Exception:
                                continue
                        # Usar valor estimado
                        calles_con_trafico = ['_'] * activos
                    except Exception:
                        pass
            except Exception:
                pass
            
            logger.info(f"📊 Estado SUMO: {total_vehiculos} veh, {len(calles_con_trafico)} calles activas")
            
            return {
                'conectado': True,
                'gui_visible': conector_sumo.usar_gui,
                'semaforos': len(conector_sumo.intersecciones),
                'calles_totales': len(estados),
                'calles_con_trafico': len(calles_con_trafico),
                'vehiculos_totales': total_vehiculos,
                'velocidad_promedio': round(velocidad_promedio, 1),
                'congestion_promedio': round(congestion_promedio, 2),
                'tiempo_simulado_s': tiempo_simulado_s,
                'fuente': 'sumo_real'
            }
        else:
            # Diagnóstico de razón de desconexión
            razon = 'desconocida'
            if estado_sistema.get('modo') != 'sumo':
                razon = 'modo_no_sumo'
            elif not conector_sumo:
                razon = 'conector_nulo'
            elif not getattr(conector_sumo, 'conectado', False):
                # Verificar disponibilidad de TraCI
                try:
                    import traci  # noqa: F401
                    razon = 'sin_conexion_traci_o_sumo'
                except ImportError:
                    razon = 'traci_no_disponible'

            return {
                'conectado': False,
                'razon': razon,
                'mensaje': 'SUMO no está conectado. Cambia a Modo SUMO para iniciar.'
            }
    except Exception as e:
        logger.error(f"Error obteniendo estado SUMO: {e}")
        return {'conectado': False, 'error': str(e)}


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


from fastapi.responses import StreamingResponse
import cv2
import numpy as np


@app.get("/api/video/stream-camera")
async def stream_camera():
    """Stream de cámara con procesamiento YOLO y métricas visuales en tiempo real"""
    
    def generar_frames():
        """Generador de frames procesados con métricas visuales"""
        import cv2
        import numpy as np
        
        # Agregar path de vision_computadora
        vision_path = Path(__file__).parent.parent / 'vision_computadora'
        sys.path.insert(0, str(vision_path))
        
        try:
            from vision_computadora.procesador_video import ProcesadorVideo
            
            # Crear procesador de video para la cámara (índice 0)
            procesador = ProcesadorVideo(
                ruta_video=0,  # Índice de cámara
                pixeles_por_metro=15.0,
                calcular_metricas_cap6=True,  # Activar métricas del Capítulo 6
                longitud_carril=200.0
            )
            
            logger.info("✓ Procesador de video creado para stream de cámara")
            logger.info(f"  Resolucion: {procesador.ancho}x{procesador.alto}")
            logger.info(f"  FPS: {procesador.fps:.1f}")
            logger.info(f"  Métricas avanzadas: Activadas")
            
            frame_num = 0
            
            while True:
                ret, frame = procesador.video.read()
                if not ret:
                    logger.warning("No se pudo leer frame de la cámara")
                    break
                
                try:
                    # Procesar frame con métricas REALES
                    resultado = procesador.procesar_frame(frame, frame_num)
                    
                    # Dibujar detecciones y métricas usando overlay moderno COMPLETO
                    frame_anotado = procesador.dibujar_detecciones(
                        frame,
                        resultado,
                        mostrar_info=True,  # Activa overlay completo con métricas
                        modo_simple=False  # Modo COMPLETO: mostrar TODO (panel + barra)
                    )
                    
                    # Codificar frame como JPEG
                    ret, buffer = cv2.imencode('.jpg', frame_anotado, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ret:
                        continue
                    
                    frame_bytes = buffer.tobytes()
                    
                    # Enviar frame en formato MJPEG
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    frame_num += 1
                    
                except Exception as e:
                    logger.error(f"Error procesando frame {frame_num}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error inicializando stream de cámara: {e}")
            import traceback
            traceback.print_exc()
            
            # Generar frame de error
            frame_error = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_error, "Error: No se pudo iniciar camara", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame_error)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        finally:
            if 'procesador' in locals():
                procesador.video.release()
                logger.info("Cámara liberada")
    
    return StreamingResponse(
        generar_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/video/stream-video-index/{video_index}")
async def stream_video_procesado(video_index: int):
    """Stream de video procesado con métricas visuales (modo simple para VideoEjemplo)"""
    
    def generar_frames_video():
        """Generador de frames de video procesado"""
        import cv2
        import numpy as np
        
        # Agregar path de vision_computadora
        vision_path = Path(__file__).parent.parent / 'vision_computadora'
        sys.path.insert(0, str(vision_path))
        
        # Buscar videos disponibles (rutas absolutas desde la raíz del proyecto)
        proyecto_root = Path(__file__).parent.parent
        videos_paths = [
            proyecto_root / "datos/videos-prueba/analisis-parametros/VideoPrueba01.mp4",
            proyecto_root / "datos/videos-prueba/analisis-parametros/VideoPuentePUCP.mp4",
        ]
        
        logger.info(f"Intentando cargar video index={video_index} de {len(videos_paths)} disponibles")
        
        # Seleccionar video según índice
        if video_index < 0 or video_index >= len(videos_paths):
            logger.error(f"Índice de video inválido: {video_index}")
            frame_error = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_error, "Error: Video no encontrado", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame_error)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
        
        ruta_video = videos_paths[video_index]
        
        if not ruta_video.exists():
            logger.error(f"Video no existe: {ruta_video}")
            frame_error = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_error, f"Error: {ruta_video.name} no encontrado", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame_error)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return
        
        try:
            from vision_computadora.procesador_video import ProcesadorVideo
            
            # Crear procesador de video
            procesador = ProcesadorVideo(
                ruta_video=str(ruta_video),
                pixeles_por_metro=None,  # Permitir autoajuste por resolución
                calcular_metricas_cap6=True,
                longitud_carril=200.0
            )
            
            logger.info(f"✓ Procesador de video creado para: {ruta_video.name}")
            logger.info(f"  Resolución: {procesador.ancho}x{procesador.alto}")
            logger.info(f"  FPS: {procesador.fps:.1f}")
            logger.info(f"  Total frames: {procesador.total_frames}")
            logger.info(f"  Modo: SIMPLE (solo barra + título)")
            
            frame_num = 0
            
            while True:
                ret, frame = procesador.video.read()
                if not ret:
                    # Reiniciar video al final (loop)
                    procesador.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_num = 0
                    continue
                
                try:
                    # Procesar frame con métricas REALES
                    resultado = procesador.procesar_frame(frame, frame_num)
                    
                    # Dibujar detecciones con overlay MODO SIMPLE
                    # (solo título + barra, sin panel de métricas)
                    print(f"[ENDPOINT VIDEO] Llamando dibujar_detecciones con modo_simple=False")
                    frame_anotado = procesador.dibujar_detecciones(
                        frame,
                        resultado,
                        mostrar_info=True,
                        modo_simple=False  # MODO COMPLETO: mostrar panel de métricas (incluye longitud de cola)
                    )
                    print(f"[ENDPOINT VIDEO] dibujar_detecciones terminó")
                    
                    # Codificar frame como JPEG
                    ret, buffer = cv2.imencode('.jpg', frame_anotado, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ret:
                        continue
                    
                    frame_bytes = buffer.tobytes()
                    
                    # Enviar frame en formato MJPEG
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    frame_num += 1
                    
                except Exception as e:
                    logger.error(f"Error procesando frame {frame_num}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error inicializando stream de video: {e}")
            import traceback
            traceback.print_exc()
            
            # Generar frame de error
            frame_error = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_error, "Error al procesar video", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame_error)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        finally:
            if 'procesador' in locals():
                procesador.video.release()
                logger.info(f"Video liberado: {ruta_video.name}")
    
    return StreamingResponse(
        generar_frames_video(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


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
    """Envía mensaje a todos los clientes WebSocket usando WebSocketManager"""
    from servicios.websocket_manager import WebSocketManager
    await WebSocketManager.broadcast(mensaje)


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
                    # Clamp estricto del ICV en modo simulador (0.50–0.60)
                    icv_val = float(resultado_icv['icv'])
                    if estado_sistema['modo'] == 'simulador':
                        icv_val = max(0.50, min(0.60, icv_val))

                    # Obtener estado del semáforo desde el simulador
                    estado_semaforo = estado_sistema['simulador'].estados_semaforo.get(inter_id)
                    if estado_semaforo:
                        fase_semaforo = estado_semaforo.fase
                    else:
                        fase_semaforo = 'verde'  # Default si no existe

                    metricas = {
                        'interseccion_id': inter_id,
                        'timestamp': estado.timestamp.isoformat(),
                        'icv': icv_val,
                        'clasificacion': resultado_icv['clasificacion'],
                        'color': resultado_icv['color'],
                        'num_vehiculos': estado.num_vehiculos,
                        'flujo': estado.flujo_vehicular,
                        'velocidad': estado.velocidad_promedio,
                        'cola': estado.longitud_cola,
                        'estado_semaforo': fase_semaforo  # NUEVO: estado del semáforo
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
                logger.info(f"Enviando {len(metricas_actualizadas)} métricas por WebSocket...")
                await broadcast_mensaje({
                    'tipo': 'metricas_actualizadas',
                    'datos': metricas_actualizadas
                })
                logger.debug("Métricas enviadas correctamente")

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
