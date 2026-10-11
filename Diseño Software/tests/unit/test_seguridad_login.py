"""Pruebas del limitador de login y de las credenciales locales de demo."""

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "servidor-backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from seguridad import usuarios  # noqa: E402
from seguridad.limitador_login import LimitadorLogin  # noqa: E402


def test_limitador_bloquea_y_expira_con_reloj_controlado():
    limitador = LimitadorLogin(
        max_intentos=2,
        ventana_segundos=5,
        bloqueo_segundos=10,
    )

    assert limitador.registrar_fallo(["ip:local"], ahora=0) == 0
    assert limitador.registrar_fallo(["ip:local"], ahora=1) == 10
    assert limitador.reintento_en(["ip:local"], ahora=6) == 5
    assert limitador.reintento_en(["ip:local"], ahora=11) == 0
    assert limitador.registrar_fallo(["ip:local"], ahora=12) == 0


def test_limitador_limpia_claves_y_acota_memoria():
    limitador = LimitadorLogin(5, 60, 30, max_claves=2)
    limitador.registrar_fallo(["usuario:a"], ahora=0)
    limitador.registrar_fallo(["usuario:b"], ahora=1)
    limitador.registrar_fallo(["usuario:c"], ahora=2)

    assert len(limitador._estados) == 2
    assert "usuario:a" not in limitador._estados
    limitador.limpiar(["usuario:b", "usuario:c"])
    assert not limitador._estados


def test_credenciales_de_entorno_deben_estar_completas(monkeypatch):
    variables = (
        "DEMO_OPERADOR_PASSWORD",
        "DEMO_TECNICO_PASSWORD",
        "DEMO_ADMIN_PASSWORD",
    )
    for variable in variables:
        monkeypatch.delenv(variable, raising=False)

    assert usuarios._leer_passwords_entorno() is None
    monkeypatch.setenv(variables[0], "clave-local-operador-2026")
    with pytest.raises(ValueError, match="faltan"):
        usuarios._leer_passwords_entorno()


def test_genera_credenciales_aleatorias_persistentes(tmp_path, monkeypatch):
    for variable in (
        "DEMO_OPERADOR_PASSWORD",
        "DEMO_TECNICO_PASSWORD",
        "DEMO_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(variable, raising=False)

    archivo = tmp_path / "credenciales.json"
    monkeypatch.setattr(usuarios, "_CREDENTIALS_FILE", archivo)
    monkeypatch.setattr(usuarios, "_USUARIOS_CACHE", None)

    cuentas = usuarios.obtener_usuarios_demo()
    guardadas = json.loads(archivo.read_text(encoding="utf-8"))

    assert {cuenta["username"] for cuenta in cuentas} == set(usuarios.ROLES_VALIDOS)
    assert set(guardadas) == set(usuarios.ROLES_VALIDOS)
    assert len(set(guardadas.values())) == len(usuarios.ROLES_VALIDOS)
    assert all(len(password) >= 12 for password in guardadas.values())
