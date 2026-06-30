"""
JWT HS256 con librería estándar
===============================

Implementación mínima y conforme de JSON Web Tokens firmados con HMAC-SHA256.
Sin dependencias externas (solo stdlib): la firma es el mismo algoritmo
HMAC/SHA-256 que la tesis describe para proteger la integridad de la telemetría.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Dict


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segmento: str) -> bytes:
    relleno = "=" * (-len(segmento) % 4)
    return base64.urlsafe_b64decode(segmento + relleno)


def _firmar(mensaje: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(mac)


def crear_token(payload: Dict, secret: str, exp_segundos: int = 3600) -> str:
    """Genera un JWT HS256 con expiración (iat/exp incluidos)."""
    header = {"alg": "HS256", "typ": "JWT"}
    ahora = int(time.time())
    cuerpo = dict(payload)
    cuerpo["iat"] = ahora
    cuerpo["exp"] = ahora + int(exp_segundos)

    seg1 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    seg2 = _b64url_encode(json.dumps(cuerpo, separators=(",", ":")).encode("utf-8"))
    firma = _firmar(f"{seg1}.{seg2}", secret)
    return f"{seg1}.{seg2}.{firma}"


def verificar_token(token: str, secret: str) -> Dict:
    """
    Verifica firma y expiración. Devuelve el payload o lanza ValueError.
    """
    if not token or token.count(".") != 2:
        raise ValueError("token mal formado")

    seg1, seg2, firma = token.split(".")
    firma_esperada = _firmar(f"{seg1}.{seg2}", secret)
    # Comparación en tiempo constante para evitar timing attacks
    if not hmac.compare_digest(firma_esperada, firma):
        raise ValueError("firma inválida")

    try:
        payload = json.loads(_b64url_decode(seg2))
    except Exception:
        raise ValueError("payload ilegible")

    if "exp" in payload and time.time() > float(payload["exp"]):
        raise ValueError("token expirado")

    return payload
