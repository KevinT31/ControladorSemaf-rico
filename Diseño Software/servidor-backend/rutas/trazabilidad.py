"""
Rutas de Trazabilidad y Demostración de Seguridad
=================================================
    GET /api/interseccion/{id}/explicacion -> cadena completa de decisión
    GET /api/seguridad/demo                 -> demostración de la autoridad de seguridad

La explicación responde al requisito de TRAZABILIDAD: el jurado puede ver de
dónde sale cada decisión (entrada -> ICV -> regla difusa disparada -> ΔT ->
verde final -> corrección de seguridad). Acepta valores por query para hacer
"what-if" en vivo, o usa los datos reales de la intersección si están disponibles.
"""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

_RAIZ = Path(__file__).parent.parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion  # noqa: E402
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6  # noqa: E402
from nucleo.seguridad_semaforica import validador_seguridad, LIMITES  # noqa: E402

router = APIRouter(prefix="/api", tags=["Trazabilidad"])

# Instancias reutilizables (deterministas, sin estado mutable relevante)
_calc = CalculadorICV(ParametrosInterseccion())
_difuso = ControladorDifusoCapitulo6()


def _pi_normalizado(velocidad: float, cola_m: float):
    """
    Parámetro de Intensidad PI (Cap 6.2.4), normalizado a (0,1).
    PI = (Vnorm + δ)/(SCnorm + δ);  PI_norm = PI/(1+PI).
    Flujo libre -> ~0.92 (eficiente); bloqueo -> ~0.08 (ineficiente).
    """
    delta = 0.1
    sc = max(0.0, cola_m / 7.0)          # vehículos detenidos (≈7 m c/u)
    v_norm = min(1.0, max(0.0, velocidad) / 60.0)
    sc_norm = min(1.0, sc / 20.0)
    pi_raw = (v_norm + delta) / (sc_norm + delta)
    return pi_raw / (1.0 + pi_raw), sc


def _limites_dict():
    return {
        "t_verde_min": LIMITES.T_VERDE_MIN, "t_verde_max": LIMITES.T_VERDE_MAX,
        "t_ambar_min": LIMITES.T_AMBAR_MIN, "t_todo_rojo_min": LIMITES.T_TODO_ROJO_MIN,
    }


@router.get("/interseccion/{interseccion_id}/explicacion")
async def explicar_decision(interseccion_id: str,
                            cola: Optional[float] = None,
                            velocidad: Optional[float] = None,
                            flujo: Optional[float] = None,
                            ev: float = 0.0):
    """Devuelve la cadena de decisión trazable para una intersección."""
    fuente = "manual (what-if)"

    # Si no se pasan datos por query, intentar leer el estado real
    if cola is None or velocidad is None or flujo is None:
        try:
            from main import estado_sistema
            sim = estado_sistema.get('simulador')
            est = sim.obtener_estado(interseccion_id) if sim else None
            if est:
                cola = est.longitud_cola if cola is None else cola
                velocidad = est.velocidad_promedio if velocidad is None else velocidad
                flujo = est.flujo_vehicular if flujo is None else flujo
                fuente = "estado real (simulador/SUMO)"
        except Exception:
            pass

    cola = 0.0 if cola is None else float(cola)
    velocidad = 0.0 if velocidad is None else float(velocidad)
    flujo = 0.0 if flujo is None else float(flujo)

    # 1) Índice de Congestión Vehicular (Cap 6.2.3)
    res_icv = _calc.calcular(longitud_cola=cola, velocidad_promedio=velocidad,
                             flujo_vehicular=flujo)
    icv = float(res_icv['icv'])

    # 2) Parámetro de Intensidad (Cap 6.2.4)
    pi, sc = _pi_normalizado(velocidad, cola)

    # 3) Inferencia difusa Mamdani (reglas disparadas con su grado)
    inf = _difuso.calcular_ajuste_verde(icv=icv, pi=pi, ev=ev)
    delta_t = inf['delta_t_porcentaje']

    # 4) Tiempo verde ajustado + capa de seguridad funcional
    t_verde_bruto = _difuso.calcular_tiempo_verde_ajustado(_difuso.T_base_NS, delta_t)
    seg = validador_seguridad.aplicar_con_seguridad(
        {'t_verde_ns': t_verde_bruto, 't_verde_eo': _difuso.T_base_EO,
         't_ambar': _difuso.T_ambar, 't_todo_rojo': _difuso.T_todo_rojo},
        {'icv': icv, 'pi': pi})

    return {
        'interseccion_id': interseccion_id,
        'fuente_datos': fuente,
        'entrada': {
            'cola_m': round(cola, 1), 'velocidad_kmh': round(velocidad, 1),
            'flujo_veh_min': round(flujo, 1), 'stopped_count_aprox': round(sc, 1),
            'emergencia': ev,
        },
        'icv': {'valor': round(icv, 3), 'nivel': res_icv['clasificacion'],
                'color': res_icv.get('color')},
        'pi': round(pi, 3),
        'fuzzificacion': {'icv': inf['grados_icv'], 'pi': inf['grados_pi'],
                          'ev': inf['grados_ev']},
        'reglas_disparadas': inf['reglas_disparadas'],
        'delta_t_porcentaje': round(delta_t, 1),
        'verde_base_s': _difuso.T_base_NS,
        'verde_bruto_s': round(t_verde_bruto, 1),
        'seguridad': seg,
        'verde_final_s': round(seg['tiempos']['t_verde_ns'], 1),
        'limites': _limites_dict(),
    }


@router.get("/seguridad/demo")
async def demo_seguridad():
    """Demostración en vivo de la AUTORIDAD de seguridad funcional."""
    casos = []

    # Caso 1: comando peligroso (verde de 200 s) -> recortado al máximo seguro
    t, corr = validador_seguridad.clamp_tiempos(200, 30, 3, 2)
    casos.append({
        'caso': 'Verde solicitado de 200 s',
        'resultado': f"recortado a {t['t_verde_ns']:.0f} s (máx {LIMITES.T_VERDE_MAX:.0f} s)",
        'seguro': True, 'correcciones': corr,
    })

    # Caso 2: datos inválidos -> modo seguro
    r = validador_seguridad.aplicar_con_seguridad(None, {'icv': float('nan')})
    casos.append({
        'caso': 'Datos de tráfico inválidos (NaN / SUMO caído)',
        'resultado': 'MODO SEGURO: ' + str(r.get('motivo_modo_seguro')),
        'seguro': True, 'tiempos': r.get('tiempos'),
    })

    # Caso 3: amarillo por debajo del mínimo -> forzado al mínimo
    t3, corr3 = validador_seguridad.clamp_tiempos(30, 30, 0, 0)
    casos.append({
        'caso': 'Amarillo y todo-rojo en 0 s',
        'resultado': f"forzados a amarillo {t3['t_ambar']:.0f} s / todo-rojo {t3['t_todo_rojo']:.0f} s",
        'seguro': True, 'correcciones': corr3,
    })

    # Caso 4: no-conflicto de fases
    permitido = validador_seguridad.verificar_fases_no_conflictivas(True, True)
    casos.append({
        'caso': 'Intento de poner NS y EO en verde a la vez',
        'resultado': 'PERMITIDO (¡peligro!)' if permitido else 'BLOQUEADO por seguridad',
        'seguro': (not permitido),
    })

    return {
        'autoridad': 'Capa de seguridad funcional semafórica',
        'descripcion': ('El módulo difuso optimiza la temporización, pero esta capa '
                        'mantiene la autoridad final: nunca permite estados peligrosos.'),
        'limites': _limites_dict(),
        'casos': casos,
    }
