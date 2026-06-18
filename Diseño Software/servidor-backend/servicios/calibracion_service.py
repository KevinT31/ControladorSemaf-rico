"""
Calibración de la simulación SUMO contra el tráfico REAL de HERE.

Idea: HERE es la referencia real. Se toma la congestión media real (promedio de
jamFactor normalizado a 0–1) como OBJETIVO y se ajusta la DEMANDA de SUMO en vivo
con `traci.simulation.setScale` mediante un control proporcional, hasta que la
congestión simulada (ICV_red) se acerque a la real.

- HERE se consulta con TTL (no en cada paso) para cuidar la cuota.
- El ajuste de escala se aplica con un intervalo mínimo para que cada cambio
  tenga tiempo de surtir efecto.
"""
import time
import logging

from .trafico_real_service import obtener_trafico_real

logger = logging.getLogger(__name__)

TTL_HERE = 180.0          # refrescar objetivo HERE cada 3 min (cuota)
INTERVALO_CAL = 6.0       # segundos mínimos entre ajustes de escala
GANANCIA = 1.2            # ganancia del control proporcional
# Tope de escala moderado: en una red enorme (metro) subir mucho la demanda
# genera miles de vehículos y ralentiza la simulación en vivo. Se prioriza
# fluidez; la calibración acerca la congestión sin saturar.
ESCALA_MIN, ESCALA_MAX = 0.2, 3.0

VEL_LIBRE_MS = 13.89      # ~50 km/h (velocidad libre de referencia)

_target = {'ts': 0.0, 'valor': None, 'jam_avg': None}
_estado = {'escala': 1.0, 'ts_cal': 0.0, 'ultimo': None}


def _congestion_sumo(traci):
    """Congestión de red basada en VELOCIDAD (0–1): 1 - v_media/v_libre.

    A diferencia del promedio de congestión por calle (que se diluye al añadir
    vehículos), esta métrica SUBE con el volumen y es comparable al jamFactor de
    HERE (ambas reflejan caída de velocidad). Devuelve (congestion, n_vehiculos).
    """
    try:
        veh = traci.vehicle.getIDList()
        n = len(veh)
        if n == 0:
            return 0.0, 0
        suma = 0.0
        for v in veh:
            suma += traci.vehicle.getSpeed(v)
        v_media = suma / n
        cong = max(0.0, min(1.0, 1.0 - v_media / VEL_LIBRE_MS))
        return cong, n
    except Exception:
        return 0.0, 0


def obtener_objetivo_here():
    """Congestión real media (0–1) desde HERE, con caché por TTL."""
    ahora = time.time()
    if _target['valor'] is not None and (ahora - _target['ts'] < TTL_HERE):
        return _target['valor']
    data = obtener_trafico_real()
    if not data.get('disponible'):
        return _target['valor']  # mantener lo anterior si HERE falla
    jams = [s['jam'] for s in data.get('segmentos', []) if isinstance(s.get('jam'), (int, float))]
    if not jams:
        return _target['valor']
    jam_avg = sum(jams) / len(jams)
    valor = max(0.0, min(1.0, jam_avg / 10.0))   # jamFactor 0..10 -> 0..1
    _target.update({'ts': ahora, 'valor': valor, 'jam_avg': jam_avg})
    logger.info(f"Calibración: objetivo HERE={valor:.3f} (jamFactor medio {jam_avg:.2f})")
    return valor


def calibrar(traci) -> dict:
    """Ajusta la escala de demanda de SUMO hacia el objetivo HERE.

    Mide la congestión simulada por velocidad (sube con el volumen) y ajusta
    `setScale` con control proporcional para acercarla a la congestión real.
    """
    ahora = time.time()
    cong_sumo, n_veh = _congestion_sumo(traci)
    objetivo = obtener_objetivo_here()
    comp = {
        'icv_sumo': round(cong_sumo, 3),
        'vehiculos': n_veh,
        'objetivo_here': round(objetivo, 3) if objetivo is not None else None,
        'jam_avg_here': round(_target['jam_avg'], 2) if _target['jam_avg'] is not None else None,
        'escala': round(_estado['escala'], 2),
        'calibrado': objetivo is not None,
    }

    if objetivo is not None and (ahora - _estado['ts_cal'] >= INTERVALO_CAL):
        error = objetivo - cong_sumo
        escala = _estado['escala'] + GANANCIA * error
        escala = max(ESCALA_MIN, min(ESCALA_MAX, escala))
        _estado['escala'] = escala
        _estado['ts_cal'] = ahora
        try:
            traci.simulation.setScale(escala)
        except Exception as e:
            logger.warning(f"setScale falló: {e}")
        comp['escala'] = round(escala, 2)

    if objetivo is not None:
        den = max(objetivo, cong_sumo, 0.05)
        comp['coincidencia'] = round(max(0.0, 1.0 - abs(objetivo - cong_sumo) / den) * 100.0)
    else:
        comp['coincidencia'] = None

    _estado['ultimo'] = comp
    return comp


def ultima_comparacion() -> dict:
    """Última comparación calculada (para /api/comparacion)."""
    if _estado['ultimo'] is not None:
        return _estado['ultimo']
    return {'icv_sumo': None, 'objetivo_here': None, 'escala': _estado['escala'],
            'calibrado': False, 'coincidencia': None}
