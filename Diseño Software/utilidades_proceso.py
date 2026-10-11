"""Utilidades seguras para arrancar el backend local."""

from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "servidor-backend"


def _puerto_ocupado(puerto: int) -> bool:
    """Indica si hay un listener TCP local en el puerto dado."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", puerto)) == 0


def _es_backend_del_proyecto(proceso: object) -> bool:
    """Reconoce únicamente el ``main.py`` de este proyecto.

    No basta con que el proceso se llame ``python``: terminar cualquier Python
    de la máquina puede destruir trabajo no relacionado.
    """
    try:
        cmdline = [str(arg) for arg in proceso.cmdline()]
        cwd = Path(proceso.cwd()).resolve()
    except Exception:
        return False

    backend = BACKEND_DIR.resolve()
    if cwd != backend:
        return False

    return any(Path(arg).name.lower() == "main.py" for arg in cmdline[1:])


def liberar_puerto_backend(
    puerto: int = 8000,
    informar: Callable[[str], None] = print,
) -> bool:
    """Libera el puerto solo si lo ocupa una instancia previa del backend.

    Devuelve ``False`` cuando el puerto pertenece a otro programa o no puede
    inspeccionarse con seguridad. El llamador debe abortar el arranque en ese
    caso, en lugar de matar procesos ajenos.
    """
    informar(f"\n🔍 Verificando puerto {puerto}...")
    try:
        import psutil
    except ImportError:
        if _puerto_ocupado(puerto):
            informar(
                "   [ERROR] El puerto está ocupado y psutil no está instalado; "
                "no es seguro terminar el proceso automáticamente."
            )
            return False
        informar(f"   [OK] Puerto {puerto} libre")
        return True

    procesos = {}
    try:
        conexiones = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError) as exc:
        informar(f"   [ERROR] No se pudo inspeccionar el puerto: {exc}")
        return not _puerto_ocupado(puerto)

    for conexion in conexiones:
        direccion = conexion.laddr
        if not direccion or getattr(direccion, "port", None) != puerto:
            continue
        if conexion.pid is not None:
            procesos[conexion.pid] = None

    if not procesos:
        if _puerto_ocupado(puerto):
            informar(
                f"   [ERROR] El puerto {puerto} está ocupado, pero no se pudo "
                "identificar al proceso propietario."
            )
            return False
        informar(f"   [OK] Puerto {puerto} libre")
        return True

    propios = []
    externos = []
    for pid in procesos:
        try:
            proceso = psutil.Process(pid)
            (propios if _es_backend_del_proyecto(proceso) else externos).append(proceso)
        except psutil.NoSuchProcess:
            continue
        except (psutil.AccessDenied, OSError):
            externos.append(None)

    if externos:
        nombres = []
        for proceso in externos:
            if proceso is None:
                nombres.append("proceso no identificable")
                continue
            try:
                nombres.append(f"{proceso.name()} (PID {proceso.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                nombres.append(f"PID {proceso.pid}")
        informar(
            f"   [ERROR] Puerto {puerto} ocupado por " + ", ".join(nombres) +
            ". Ciérralo manualmente o configura otro puerto."
        )
        return False

    for proceso in propios:
        try:
            informar(
                f"   [!] Deteniendo una instancia anterior del backend "
                f"(PID {proceso.pid})"
            )
            proceso.terminate()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            informar(f"   [ERROR] Sin permiso para detener el PID {proceso.pid}")
            return False

    vivos = []
    if propios:
        _, vivos = psutil.wait_procs(propios, timeout=3)
    for proceso in vivos:
        try:
            informar(f"   [!] El PID {proceso.pid} no respondió; forzando cierre")
            proceso.kill()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            informar(f"   [ERROR] Sin permiso para cerrar el PID {proceso.pid}")
            return False

    limite = time.monotonic() + 2.0
    while _puerto_ocupado(puerto) and time.monotonic() < limite:
        time.sleep(0.1)

    libre = not _puerto_ocupado(puerto)
    informar(f"   [{'OK' if libre else 'ERROR'}] Puerto {puerto} " +
             ("libre" if libre else "continúa ocupado"))
    return libre
