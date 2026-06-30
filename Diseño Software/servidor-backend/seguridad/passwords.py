"""
Hashing de contraseñas con PBKDF2-HMAC-SHA256 (stdlib)
======================================================

Nunca se almacenan contraseñas en claro. Formato almacenado:
    pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ALGO = "pbkdf2_sha256"
_ITERACIONES = 200_000


def hash_password(password: str) -> str:
    """Devuelve el hash codificado de una contraseña (con salt aleatorio)."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERACIONES)
    return f"{_ALGO}${_ITERACIONES}${salt.hex()}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    """Compara una contraseña con su hash almacenado (tiempo constante)."""
    try:
        algo, iteraciones, salt_hex, hash_hex = almacenado.split("$")
        if algo != _ALGO:
            return False
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iteraciones))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False
