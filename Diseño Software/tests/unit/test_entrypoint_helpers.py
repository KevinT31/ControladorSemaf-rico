"""Regresiones para los lanzadores locales (fuera del núcleo NSB)."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import reiniciar_simulador
import utilidades_proceso


class _ProcesoFalso:
    def __init__(self, pid, cwd, cmdline, nombre="python.exe"):
        self.pid = pid
        self._cwd = cwd
        self._cmdline = cmdline
        self._nombre = nombre
        self.terminado = False

    def cwd(self):
        return str(self._cwd)

    def cmdline(self):
        return list(self._cmdline)

    def name(self):
        return self._nombre

    def terminate(self):
        self.terminado = True


def test_solo_reconoce_main_del_backend_del_proyecto(tmp_path, monkeypatch):
    backend = tmp_path / "servidor-backend"
    backend.mkdir()
    monkeypatch.setattr(utilidades_proceso, "BACKEND_DIR", backend)

    propio = _ProcesoFalso(10, backend, ["python", "main.py"])
    ajeno = _ProcesoFalso(11, tmp_path, ["python", "main.py"])
    otro_script = _ProcesoFalso(12, backend, ["python", "trabajo.py"])

    assert utilidades_proceso._es_backend_del_proyecto(propio)
    assert not utilidades_proceso._es_backend_del_proyecto(ajeno)
    assert not utilidades_proceso._es_backend_del_proyecto(otro_script)


def test_puerto_ajeno_no_termina_el_proceso(monkeypatch):
    import psutil

    externo = _ProcesoFalso(42, Path.cwd(), ["python", "otro_servidor.py"])
    conexion = SimpleNamespace(laddr=SimpleNamespace(port=8000), pid=42)
    monkeypatch.setattr(psutil, "net_connections", lambda kind: [conexion])
    monkeypatch.setattr(psutil, "Process", lambda pid: externo)
    monkeypatch.setattr(utilidades_proceso, "_puerto_ocupado", lambda puerto: True)

    mensajes = []
    assert not utilidades_proceso.liberar_puerto_backend(informar=mensajes.append)
    assert not externo.terminado
    assert any("otro_servidor.py" in mensaje or "python" in mensaje
               for mensaje in mensajes)


def test_reinicio_se_autentica_y_reintenta(monkeypatch):
    llamadas = []

    def solicitar(base_url, metodo, ruta, *, token=None, cuerpo=None):
        llamadas.append((metodo, ruta, token, cuerpo))
        if ruta == "/api/auth/login":
            return 200, {"access_token": "token-prueba"}
        if token == "token-prueba":
            return 200, {"mensaje": "ok"}
        return 401, {"detail": "No autenticado"}

    monkeypatch.delenv("SEMAFORO_TOKEN", raising=False)
    monkeypatch.setenv("SEMAFORO_PASSWORD", "secreto")
    monkeypatch.setattr(reiniciar_simulador, "_solicitar_json", solicitar)

    assert reiniciar_simulador.reiniciar_simulador(
        "http://localhost:8000", "hora pico", "tecnico"
    )
    assert llamadas[0][1].endswith("escenario=hora+pico")
    assert llamadas[1][1] == "/api/auth/login"
    assert llamadas[1][3] == {"username": "tecnico", "password": "secreto"}
    assert llamadas[2][2] == "token-prueba"


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://localhost/api", "//localhost", "http://"],
)
def test_reinicio_rechaza_esquemas_no_http(url):
    with pytest.raises(ValueError, match="base-url"):
        reiniciar_simulador.reiniciar_simulador(url, "normal", "tecnico")
