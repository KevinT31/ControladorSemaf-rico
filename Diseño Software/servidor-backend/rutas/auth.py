"""
Rutas de Autenticación y Auditoría
==================================
    POST /api/auth/login      -> emite token JWT
    GET  /api/auth/me         -> usuario y rol del token actual
    GET  /api/auth/auditoria  -> bitácora de eventos (solo tecnico/admin)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from config import settings
from seguridad.usuarios import autenticar
from seguridad.jwt_simple import crear_token
from seguridad.dependencias import obtener_usuario_actual, requiere_rol
from seguridad.auditoria import registrar_evento, listar_eventos

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(datos: LoginRequest, request: Request):
    """Valida credenciales y devuelve un token JWT firmado."""
    ip = request.client.host if request.client else ""
    usuario = autenticar(datos.username, datos.password)
    if not usuario:
        registrar_evento(datos.username, "-", "LOGIN", "/api/auth/login",
                         "RECHAZADO", "credenciales inválidas", ip=ip)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = crear_token(
        {"sub": usuario["username"], "rol": usuario["rol"]},
        settings.SECRET_KEY,
        settings.TOKEN_EXP_MIN * 60,
    )
    registrar_evento(usuario["username"], usuario["rol"], "LOGIN", "/api/auth/login",
                     "ACEPTADO", "inicio de sesión", ip=ip)
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": usuario,
        "expira_min": settings.TOKEN_EXP_MIN,
    }


@router.get("/me")
async def me(request: Request):
    """Devuelve el usuario y rol asociados al token actual."""
    return obtener_usuario_actual(request)


@router.get("/auditoria")
async def auditoria(request: Request, limite: int = 100,
                    _usuario: dict = Depends(requiere_rol("tecnico", "admin"))):
    """Lista los últimos eventos de auditoría (acceso restringido)."""
    return {"eventos": listar_eventos(limite)}
