"""Validación del pinout y del import perezoso de GPIO (corre en Windows)."""
import pytest


def test_import_gpio_no_rompe_windows():
    """spec §23: importar el módulo JAMÁS debe fallar sin gpiozero."""
    import nsb.actuation.gpio  # noqa: F401


def test_pinout_del_repo_es_valido():
    from nsb.actuation.gpio import cargar_pinout
    pinout = cargar_pinout("config/nsb/pinout.yaml")
    pines = [p for cols in pinout.values() for p in cols.values()]
    assert len(pines) == 12
    assert len(set(pines)) == 12   # sin duplicados


def test_pinout_duplicado_falla(tmp_path):
    from nsb.actuation.gpio import cargar_pinout
    malo = tmp_path / "p.yaml"
    malo.write_text("""
numbering: BCM
groups:
  north: {red: 17, yellow: 27, green: 22}
  south: {red: 5, yellow: 6, green: 13}
  east: {red: 23, yellow: 24, green: 25}
  west: {red: 16, yellow: 20, green: 17}
""", encoding="utf-8")   # 17 repetido
    with pytest.raises(ValueError, match="duplicado"):
        cargar_pinout(malo)


def test_pinout_incompleto_falla(tmp_path):
    from nsb.actuation.gpio import cargar_pinout
    malo = tmp_path / "p.yaml"
    malo.write_text("""
numbering: BCM
groups:
  north: {red: 17, yellow: 27}
  south: {red: 5, yellow: 6, green: 13}
  east: {red: 23, yellow: 24, green: 25}
  west: {red: 16, yellow: 20, green: 21}
""", encoding="utf-8")
    with pytest.raises(ValueError, match="north.green"):
        cargar_pinout(malo)


def test_gpio_actuator_sin_gpiozero_da_error_claro(tmp_path):
    """Instanciar (no importar) sin gpiozero → RuntimeError explicativo."""
    import importlib.util
    if importlib.util.find_spec("gpiozero") is not None:
        pytest.skip("gpiozero instalado: este test es para plataformas sin él")
    from nsb.actuation.gpio import GPIOActuator
    with pytest.raises(RuntimeError, match="gpiozero no disponible"):
        GPIOActuator("config/nsb/pinout.yaml")


def test_apply_apaga_globalmente_antes_de_encender():
    from nsb.actuation.gpio import GPIOActuator
    from nsb.domain.enums import SignalColor, SignalGroup
    from nsb.safety.gate import TODO_ROJO

    operaciones = []

    class LedFalso:
        def __init__(self, grupo, color):
            self._id = (grupo, color)

        def off(self):
            operaciones.append(("off", *self._id))

        def on(self):
            operaciones.append(("on", *self._id))

    actuator = GPIOActuator.__new__(GPIOActuator)
    actuator._leds = {
        grupo: {color: LedFalso(grupo, color) for color in SignalColor}
        for grupo in SignalGroup
    }
    actuator._estado = dict(TODO_ROJO)
    objetivo = dict(TODO_ROJO)
    objetivo[SignalGroup.NORTE] = SignalColor.VERDE
    objetivo[SignalGroup.SUR] = SignalColor.VERDE

    actuator.apply(objetivo)

    primer_on = next(i for i, op in enumerate(operaciones) if op[0] == "on")
    assert all(op[0] == "off" for op in operaciones[:primer_on])
    assert all(op[0] == "on" for op in operaciones[primer_on:])
