"""Actuador GPIO para Raspberry Pi (spec §23-24).

IMPORT PEREZOSO OBLIGATORIO: gpiozero/lgpio se importan DENTRO de
``__init__``, nunca a nivel de módulo — importar este archivo en Windows no
debe fallar (spec §23: "PROHIBIDO un import global Pi-only que rompa
Windows"). En Pi OS Bookworm (kernel ≥ 6.6) RPi.GPIO está roto: se usa
gpiozero con la pin factory lgpio.

VALIDACIÓN FÍSICA PENDIENTE DE HARDWARE: este backend está implementado y
testeado en su lógica (mapeo, apagado seguro), pero no ha sido ejecutado
sobre una Raspberry Pi real. Ver docs/nsb_v2_1/gpio_wiring.md ANTES de
conectar nada.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import yaml

from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.gate import TODO_ROJO

logger = logging.getLogger(__name__)

_GRUPO_YAML = {SignalGroup.NORTE: "north", SignalGroup.SUR: "south",
               SignalGroup.ESTE: "east", SignalGroup.OESTE: "west"}
_COLOR_YAML = {SignalColor.ROJO: "red", SignalColor.AMBAR: "yellow",
               SignalColor.VERDE: "green"}


def cargar_pinout(path: str | Path) -> Dict[SignalGroup, Dict[SignalColor, int]]:
    """Lee y valida pinout.yaml: 12 pines BCM únicos."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data.get("numbering", "BCM") != "BCM":
        raise ValueError("pinout.yaml: solo se soporta numeración BCM")
    grupos = data.get("groups", {})
    pinout: Dict[SignalGroup, Dict[SignalColor, int]] = {}
    vistos: Dict[int, str] = {}
    for grupo, clave in _GRUPO_YAML.items():
        if clave not in grupos:
            raise ValueError(f"pinout.yaml: falta el grupo {clave!r}")
        pinout[grupo] = {}
        for color, ckey in _COLOR_YAML.items():
            if ckey not in grupos[clave]:
                raise ValueError(f"pinout.yaml: falta {clave}.{ckey}")
            pin = int(grupos[clave][ckey])
            donde = f"{clave}.{ckey}"
            if pin in vistos:
                raise ValueError(
                    f"pinout.yaml: pin BCM {pin} duplicado "
                    f"({vistos[pin]} y {donde})")
            vistos[pin] = donde
            pinout[grupo][color] = pin
    return pinout


class GPIOActuator:
    """12 LEDs (4 grupos × 3 colores) vía gpiozero."""

    def __init__(self, pinout_path: str | Path,
                 active_high: bool | None = None):
        # Import perezoso: SOLO aquí (spec §23)
        try:
            from gpiozero import LED  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError(
                "gpiozero no disponible: GPIOActuator solo funciona en la "
                "Raspberry Pi (instalar con requirements-nsb-pi.txt). "
                "En Windows usar actuator.type=simulated.") from e

        with open(pinout_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if active_high is None:
            active_high = bool(data.get("active_high", True))

        pinout = cargar_pinout(pinout_path)
        self._leds: Dict[SignalGroup, Dict[SignalColor, object]] = {}
        for grupo, colores in pinout.items():
            self._leds[grupo] = {
                color: LED(pin, active_high=active_high, initial_value=False)
                for color, pin in colores.items()}
        self._estado: Dict[SignalGroup, SignalColor] = dict(TODO_ROJO)
        self.apply(dict(TODO_ROJO))
        logger.info("GPIOActuator inicializado (12 salidas BCM, "
                    "active_high=%s)", active_high)

    def apply(self, groups: Dict[SignalGroup, SignalColor]) -> None:
        # Orden seguro: primero APAGAR lo que no corresponde, luego encender.
        for grupo, leds in self._leds.items():
            objetivo = groups[grupo]
            for color, led in leds.items():
                if color is not objetivo:
                    led.off()
            leds[objetivo].on()
        self._estado = dict(groups)

    def state(self) -> Dict[SignalGroup, SignalColor]:
        return dict(self._estado)

    def shutdown(self) -> None:
        """Apagado ordenado: todo-rojo y liberar pines."""
        try:
            self.apply(dict(TODO_ROJO))
        finally:
            for leds in self._leds.values():
                for led in leds.values():
                    try:
                        led.close()
                    except Exception:
                        pass
        logger.info("GPIOActuator: apagado ordenado (todo-rojo + release)")
