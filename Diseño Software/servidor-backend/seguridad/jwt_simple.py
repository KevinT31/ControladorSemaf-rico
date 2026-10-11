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
import math
import time
from typing import Dict, Any


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segmento: str) -> bytes:
    relleno = "=" * (-len(segmento) % 4)
    return base64.urlsafe_b64decode(segmento + relleno)


def _firmar(mensaje: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(mac)


def crear_token(payload: Dict[str, Any], secret: str, exp_segundos: int = 3600) -> str:
    """Genera un JWT HS256 con expiración (iat/exp incluidos)."""
    if not isinstance(payload, dict):
        raise TypeError("payload debe ser un diccionario")
    if not secret:
        raise ValueError("secret no puede estar vacío")
    if isinstance(exp_segundos, bool) or int(exp_segundos) <= 0:
        raise ValueError("exp_segundos debe ser mayor que cero")

    header = {"alg": "HS256", "typ": "JWT"}
    ahora = int(time.time())
    cuerpo = dict(payload)
    cuerpo["iat"] = ahora
    cuerpo["exp"] = ahora + int(exp_segundos)

    seg1 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    seg2 = _b64url_encode(json.dumps(cuerpo, separators=(",", ":")).encode("utf-8"))
    firma = _firmar(f"{seg1}.{seg2}", secret)
    return f"{seg1}.{seg2}.{firma}"


def verificar_token(token: str, secret: str) -> Dict[str, Any]:
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
        header = json.loads(_b64url_decode(seg1))
        payload = json.loads(_b64url_decode(seg2))
    except Exception:
        raise ValueError("token ilegible") from None

    if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise ValueError("cabecera JWT no permitida")
    if not isinstance(payload, dict):
        raise ValueError("payload JWT inválido")

    exp = payload.get("exp")
    iat = payload.get("iat")
    if (isinstance(exp, bool) or not isinstance(exp, (int, float))
            or not math.isfinite(float(exp))):
        raise ValueError("expiración inválida")
    if (isinstance(iat, bool) or not isinstance(iat, (int, float))
            or not math.isfinite(float(iat))):
        raise ValueError("fecha de emisión inválida")
    if float(exp) <= float(iat):
        raise ValueError("intervalo temporal inválido")

    ahora = time.time()
    if float(iat) > ahora + 60.0:
        raise ValueError("token emitido en el futuro")
    if ahora >= float(exp):
        raise ValueError("token expirado")

    return payload
