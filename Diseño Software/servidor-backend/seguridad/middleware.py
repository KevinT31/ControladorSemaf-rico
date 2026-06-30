"""
Middleware de autenticación
===========================

Exige un token JWT válido para acceder a la API (/api/*), tanto para telemetría
de lectura como para comandos. Deja públicas las rutas necesarias para poder
iniciar sesión y servir la interfaz (login, estáticos, documentación).

Nota: el WebSocket /ws no pasa por este middleware HTTP (Starlette lo omite),
de modo que el flujo de telemetría en tiempo real no se interrumpe; la
autorización de COMANDOS se exige en los endpoints HTTP correspondientes.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import settings
from seguridad.jwt_simple import verificar_token

# Rutas públicas (no requieren token)
RUTAS_PUBLICAS = (
    "/api/auth/login",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _es_publica(path: str) -> bool:
    # Todo lo que no es /api (estáticos, '/', login.html, etc.) es público
    if not path.startswith("/api"):
        return True
    return any(path == r or path.startswith(r) for r in RUTAS_PUBLICAS)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Dejar pasar preflight CORS y rutas públicas / autenticación desactivada
        if request.method == "OPTIONS":
            return await call_next(request)
        if not getattr(settings, "AUTH_ENABLED", True) or _es_publica(path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        else:
            token = request.query_params.get("token")

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "No autenticado: inicie sesión para acceder a la API"})

        try:
            payload = verificar_token(token, settings.SECRET_KEY)
            request.state.usuario = {
                "username": payload.get("sub"),
                "rol": payload.get("rol"),
            }
        except ValueError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Token inválido: {e}"})

        return await call_next(request)
