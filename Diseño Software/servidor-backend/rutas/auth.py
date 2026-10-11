"""
Rutas de Autenticación y Auditoría
==================================
    POST /api/auth/login      -> emite token JWT
    GET  /api/auth/me         -> usuario y rol del token actual
    GET  /api/auth/auditoria  -> bitácora de eventos (solo tecnico/admin)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, field_validator

from config import settings
from seguridad.usuarios import autenticar
from seguridad.jwt_simple import crear_token
from seguridad.dependencias import obtener_usuario_actual, requiere_rol
from seguridad.auditoria import registrar_evento, listar_eventos
from seguridad.limitador_login import LimitadorLogin

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("username")
    @classmethod
    def validar_username(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor or any(c in valor for c in "\r\n\0"):
            raise ValueError("username inválido")
        return valor


_limitador_login = LimitadorLogin(
    settings.LOGIN_MAX_ATTEMPTS,
    settings.LOGIN_WINDOW_SECONDS,
    settings.LOGIN_LOCKOUT_SECONDS,
)


def _rechazar_por_limite(segundos: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Demasiados intentos de inicio de sesión; intente más tarde",
        headers={"Retry-After": str(max(1, segundos))},
    )


@router.post("/login")
async def login(datos: LoginRequest, request: Request):
    """Valida credenciales y devuelve un token JWT firmado."""
    ip = request.client.host if request.client else ""
    clave_ip = f"ip:{ip or 'desconocida'}"
    clave_usuario = f"usuario:{datos.username.casefold()}"
    claves = (clave_ip, clave_usuario)

    espera = _limitador_login.reintento_en(claves)
    if espera:
        _rechazar_por_limite(espera)

    usuario = autenticar(datos.username, datos.password)
    if not usuario:
        espera = _limitador_login.registrar_fallo(claves)
        registrar_evento(datos.username, "-", "LOGIN", "/api/auth/login",
                         "RECHAZADO", "credenciales inválidas", ip=ip)
        if espera:
            _rechazar_por_limite(espera)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    _limitador_login.limpiar((clave_usuario,))
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
