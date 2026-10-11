"""
Almacén de usuarios y roles
===========================

Tres roles, con privilegios crecientes (RBAC):
    - operador : solo lectura (monitoreo). NO puede enviar comandos.
    - tecnico  : ajusta parámetros del controlador y activa olas verdes.
    - admin    : todo lo anterior + gestión.

Los usuarios se siembran en la BD (idempotente). Si la BD no está disponible,
se usa un fallback en memoria para que la demo nunca se quede sin login.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Dict, Optional

from .passwords import hash_password, verificar_password

logger = logging.getLogger(__name__)

ROLES_VALIDOS = ("operador", "tecnico", "admin")

_BASE_DIR = Path(__file__).resolve().parents[2]
_ruta_credenciales = Path(
    os.environ.get("DEMO_CREDENTIALS_FILE", ".demo_credentials.json")
).expanduser()
if not _ruta_credenciales.is_absolute():
    _ruta_credenciales = _BASE_DIR / _ruta_credenciales
_CREDENTIALS_FILE = _ruta_credenciales.resolve()

_USUARIOS_CACHE: Optional[list[Dict[str, str]]] = None
_CREDENTIALS_LOCK = threading.Lock()

_FALLBACK: Optional[Dict[str, Dict]] = None
_HASH_COMPARACION = hash_password("credencial-inexistente-comparacion-temporal")


def _validar_password(password: object, origen: str) -> str:
    if not isinstance(password, str) or not (12 <= len(password) <= 256):
        raise ValueError(f"{origen} debe contener entre 12 y 256 caracteres")
    if any(caracter in password for caracter in "\r\n\0"):
        raise ValueError(f"{origen} contiene caracteres no permitidos")
    return password


def _leer_passwords_entorno() -> Optional[Dict[str, str]]:
    nombres = {
        "operador": "DEMO_OPERADOR_PASSWORD",
        "tecnico": "DEMO_TECNICO_PASSWORD",
        "admin": "DEMO_ADMIN_PASSWORD",
    }
    # Alias en inglés (DEMO_OPERATOR/TECHNICIAN_PASSWORD) por compatibilidad.
    alias = {
        "operador": "DEMO_OPERATOR_PASSWORD",
        "tecnico": "DEMO_TECHNICIAN_PASSWORD",
        "admin": "DEMO_ADMIN_PASSWORD",
    }
    presentes = {
        usuario: os.environ.get(variable) or os.environ.get(alias[usuario]) or None
        for usuario, variable in nombres.items()
    }
    if not any(valor is not None for valor in presentes.values()):
        return None
    faltantes = [nombres[u] for u, valor in presentes.items() if valor is None]
    if faltantes:
        raise ValueError(
            "Define las tres credenciales de demo; faltan: " + ", ".join(faltantes)
        )
    return {
        usuario: _validar_password(valor, nombres[usuario])
        for usuario, valor in presentes.items()
    }


def _leer_archivo_credenciales() -> Dict[str, str]:
    contenido = json.loads(_CREDENTIALS_FILE.read_text(encoding="utf-8"))
    if not isinstance(contenido, dict):
        raise ValueError("el archivo de credenciales debe contener un objeto JSON")
    return {
        usuario: _validar_password(contenido.get(usuario), f"credencial de {usuario}")
        for usuario in ROLES_VALIDOS
    }


def _generar_archivo_credenciales() -> Dict[str, str]:
    passwords = {usuario: secrets.token_urlsafe(18) for usuario in ROLES_VALIDOS}
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            _CREDENTIALS_FILE,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        return _leer_archivo_credenciales()

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(passwords, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
    except Exception:
        _CREDENTIALS_FILE.unlink(missing_ok=True)
        raise

    logger.warning(
        "Credenciales locales aleatorias generadas en %s. Proteja ese archivo.",
        _CREDENTIALS_FILE,
    )
    return passwords


def obtener_usuarios_demo() -> list[Dict[str, str]]:
    """Carga credenciales desde entorno o desde el archivo local persistente."""
    global _USUARIOS_CACHE
    if _USUARIOS_CACHE is not None:
        return _USUARIOS_CACHE

    with _CREDENTIALS_LOCK:
        if _USUARIOS_CACHE is not None:
            return _USUARIOS_CACHE
        passwords = _leer_passwords_entorno()
        if passwords is None:
            passwords = (
                _leer_archivo_credenciales()
                if _CREDENTIALS_FILE.is_file()
                else _generar_archivo_credenciales()
            )
        _USUARIOS_CACHE = [
            {"username": "operador", "password": passwords["operador"],
             "nombre": "Operador de Monitoreo", "rol": "operador"},
            {"username": "tecnico", "password": passwords["tecnico"],
             "nombre": "Técnico de Tráfico", "rol": "tecnico"},
            {"username": "admin", "password": passwords["admin"],
             "nombre": "Administrador del Sistema", "rol": "admin"},
        ]
        return _USUARIOS_CACHE


def _construir_fallback() -> Dict[str, Dict]:
    global _FALLBACK
    if _FALLBACK is None:
        _FALLBACK = {
            u["username"]: {
                "username": u["username"],
                "nombre": u["nombre"],
                "rol": u["rol"],
                "password_hash": hash_password(u["password"]),
            }
            for u in obtener_usuarios_demo()
        }
    return _FALLBACK


def seed_usuarios() -> None:
    """Sincroniza en la BD las cuentas de demo configuradas localmente."""
    try:
        from modelos_bd import SessionLocal
        from modelos_bd.usuario import UsuarioDB

        db = SessionLocal()
        try:
            creados = 0
            actualizados = 0
            for u in obtener_usuarios_demo():
                existe = db.query(UsuarioDB).filter(UsuarioDB.username == u["username"]).first()
                if not existe:
                    db.add(UsuarioDB(
                        username=u["username"], nombre=u["nombre"], rol=u["rol"],
                        password_hash=hash_password(u["password"])))
                    creados += 1
                else:
                    cambio = False
                    if not verificar_password(u["password"], existe.password_hash):
                        existe.password_hash = hash_password(u["password"])
                        cambio = True
                    if existe.nombre != u["nombre"] or existe.rol != u["rol"]:
                        existe.nombre = u["nombre"]
                        existe.rol = u["rol"]
                        cambio = True
                    actualizados += int(cambio)
            db.commit()
            logger.info(
                "Usuarios verificados (creados=%s, actualizados=%s)",
                creados,
                actualizados,
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"No se pudo sembrar usuarios en BD; se usará fallback en memoria: {e}")
        _construir_fallback()


def autenticar(username: str, password: str) -> Optional[Dict]:
    """Devuelve {username, nombre, rol} si las credenciales son válidas; si no, None."""
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    db_consultada = False
    try:
        from modelos_bd import SessionLocal
        from modelos_bd.usuario import UsuarioDB

        db = SessionLocal()
        try:
            u = db.query(UsuarioDB).filter(UsuarioDB.username == username).first()
            db_consultada = True
            password_hash = u.password_hash if u else _HASH_COMPARACION
            credencial_valida = verificar_password(password, password_hash)
            if u and credencial_valida:
                return {"username": u.username, "nombre": u.nombre, "rol": u.rol}
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Auth BD no disponible, usando fallback: {e}")

    if db_consultada:
        return None  # la BD respondió y no autenticó

    # Fallback solo si la BD no respondió
    fb = _construir_fallback().get(username)
    password_hash = fb["password_hash"] if fb else _HASH_COMPARACION
    credencial_valida = verificar_password(password, password_hash)
    if fb and credencial_valida:
        return {"username": fb["username"], "nombre": fb["nombre"], "rol": fb["rol"]}
    return None
