"""
Dependencias FastAPI: autenticación y control de acceso por roles (RBAC)
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request, HTTPException

from config import settings
from seguridad.jwt_simple import verificar_token


def _extraer_token(request: Request) -> Optional[str]:
    """Lee el token de 'Authorization: Bearer <t>' o, como respaldo, de ?token=."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("token")


def obtener_usuario_actual(request: Request) -> dict:
    """
    Devuelve {username, rol} del token válido. 401 si falta o es inválido.
    Reutiliza el usuario ya resuelto por el middleware si está disponible.
    """
    usuario = getattr(request.state, "usuario", None)
    if usuario:
        return usuario

    token = _extraer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado: falta token")
    try:
        payload = verificar_token(token, settings.SECRET_KEY)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")
    return {"username": payload.get("sub"), "rol": payload.get("rol")}


def requiere_rol(*roles_permitidos: str):
    """
    Factoría de dependencias RBAC. Uso:
        @router.put(..., dependencies=[Depends(requiere_rol('tecnico','admin'))])
    o como parámetro para recibir el usuario:
        usuario = Depends(requiere_rol('tecnico','admin'))
    """
    def dependencia(request: Request) -> dict:
        usuario = obtener_usuario_actual(request)
        if usuario.get("rol") not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail=(f"Permiso denegado: se requiere rol "
                        f"[{', '.join(roles_permitidos)}]; tu rol es "
                        f"'{usuario.get('rol')}'"))
        return usuario
    return dependencia
