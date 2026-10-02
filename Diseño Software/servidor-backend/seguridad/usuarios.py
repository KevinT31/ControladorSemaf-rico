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

import logging
from typing import Dict, Optional

from config import settings
from .passwords import hash_password, verificar_password

logger = logging.getLogger(__name__)

ROLES_VALIDOS = ("operador", "tecnico", "admin")

def _usuarios_demo_configurados():
    """Usuarios demo cuyas contraseñas fueron definidas explícitamente en .env."""
    usuarios = [
        {"username": "operador", "password": settings.DEMO_OPERATOR_PASSWORD,
         "nombre": "Operador de Monitoreo", "rol": "operador"},
        {"username": "tecnico", "password": settings.DEMO_TECHNICIAN_PASSWORD,
         "nombre": "Técnico de Tráfico", "rol": "tecnico"},
        {"username": "admin", "password": settings.DEMO_ADMIN_PASSWORD,
         "nombre": "Administrador del Sistema", "rol": "admin"},
    ]
    return [u for u in usuarios if u["password"]]

_FALLBACK: Optional[Dict[str, Dict]] = None


def _construir_fallback() -> Dict[str, Dict]:
    global _FALLBACK
    if _FALLBACK is None:
        _FALLBACK = {
            u["username"]: {**u, "password_hash": hash_password(u["password"])}
            for u in _usuarios_demo_configurados()
        }
    return _FALLBACK


def seed_usuarios() -> None:
    """Crea los usuarios por defecto en la BD si no existen (idempotente)."""
    usuarios_demo = _usuarios_demo_configurados()
    if not usuarios_demo:
        logger.warning(
            "No hay contraseñas DEMO_* configuradas; no se sembrarán usuarios demo."
        )
        return

    try:
        from modelos_bd import SessionLocal
        from modelos_bd.usuario import UsuarioDB

        db = SessionLocal()
        try:
            creados = 0
            for u in _usuarios_demo_configurados():
                existe = db.query(UsuarioDB).filter(UsuarioDB.username == u["username"]).first()
                if not existe:
                    db.add(UsuarioDB(
                        username=u["username"], nombre=u["nombre"], rol=u["rol"],
                        password_hash=hash_password(u["password"])))
                    creados += 1
            db.commit()
            logger.info(f"Usuarios verificados (nuevos creados: {creados})")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"No se pudo sembrar usuarios en BD; se usará fallback en memoria: {e}")
        _construir_fallback()


def autenticar(username: str, password: str) -> Optional[Dict]:
    """Devuelve {username, nombre, rol} si las credenciales son válidas; si no, None."""
    db_consultada = False
    try:
        from modelos_bd import SessionLocal
        from modelos_bd.usuario import UsuarioDB

        db = SessionLocal()
        try:
            u = db.query(UsuarioDB).filter(UsuarioDB.username == username).first()
            db_consultada = True
            if u and verificar_password(password, u.password_hash):
                return {"username": u.username, "nombre": u.nombre, "rol": u.rol}
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Auth BD no disponible, usando fallback: {e}")

    if db_consultada:
        return None  # la BD respondió y no autenticó

    # Fallback solo si la BD no respondió
    fb = _construir_fallback().get(username)
    if fb and verificar_password(password, fb["password_hash"]):
        return {"username": fb["username"], "nombre": fb["nombre"], "rol": fb["rol"]}
    return None
