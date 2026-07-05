"""Tests de hardware GPIO (marker hardware): SOLO corren en una Raspberry Pi
física con gpiozero instalado. En cualquier otra plataforma se saltan con
razón visible — jamás se marcan PASS sin ejecutarse (spec §7.11, §50).
"""
import platform

import pytest

pytestmark = pytest.mark.hardware


def _en_pi() -> bool:
    if platform.machine() not in ("aarch64", "armv7l", "armv6l"):
        return False
    try:
        import gpiozero  # noqa: F401
        return True
    except ImportError:
        return False


requiere_pi = pytest.mark.skipif(
    not _en_pi(),
    reason="REQUIRES HARDWARE: Raspberry Pi física con gpiozero "
           "(validación GPIO pendiente de hardware)")


@requiere_pi
def test_gpio_actuator_ciclo_basico():
    from nsb.actuation.gpio import GPIOActuator
    from nsb.domain.enums import SignalColor, SignalGroup
    from nsb.safety.gate import TODO_ROJO

    act = GPIOActuator("config/nsb/pinout.yaml")
    try:
        assert act.state() == TODO_ROJO
        verde_ns = dict(TODO_ROJO)
        verde_ns[SignalGroup.NORTE] = SignalColor.VERDE
        verde_ns[SignalGroup.SUR] = SignalColor.VERDE
        act.apply(verde_ns)
        assert act.state() == verde_ns
    finally:
        act.shutdown()
    assert act.state() == TODO_ROJO


@requiere_pi
def test_gpio_12_salidas_unicas():
    from nsb.actuation.gpio import cargar_pinout
    pinout = cargar_pinout("config/nsb/pinout.yaml")
    pines = [p for cols in pinout.values() for p in cols.values()]
    assert len(pines) == 12
    assert len(set(pines)) == 12
