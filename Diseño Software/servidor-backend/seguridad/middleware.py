"""
Middleware de autenticación
===========================

Exige un token JWT válido para acceder a la API (/api/*), tanto para telemetría
de lectura como para comandos. Deja públicas las rutas necesarias para poder
iniciar sesión y servir la interfaz (login, estáticos, documentación).

Nota: el WebSocket /ws no pasa por este middleware HTTP (Starlette lo omite),
por lo que su endpoint valida el JWT explícitamente antes de aceptar la
conexión. Los comandos mutables siguen protegidos además por RBAC en HTTP.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config import settings
from seguridad.jwt_simple import verificar_token
from seguridad.dependencias import identidad_desde_payload

# Rutas públicas (no requieren token)
RUTAS_PUBLICAS = (
    "/api/auth/login",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)

# Un elemento <img> no permite enviar Authorization. Se admite query token
# exclusivamente en los streams MJPEG; el resto de la API exige Bearer header.
RUTAS_TOKEN_QUERY = (
    "/api/video/stream-camera",
    "/api/video/stream-processed-loop",
)
PREFIJOS_TOKEN_QUERY = (
    "/api/video/stream-video-index/",
)


def _es_publica(path: str) -> bool:
    # Todo lo que no es /api (estáticos, '/', login.html, etc.) es público
    if not path.startswith("/api"):
        return True
    return any(path == ruta or path.startswith(f"{ruta}/") for ruta in RUTAS_PUBLICAS)


def _admite_token_query(path: str) -> bool:
    return path in RUTAS_TOKEN_QUERY or any(
        path.startswith(prefijo) for prefijo in PREFIJOS_TOKEN_QUERY)


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
            token = request.query_params.get("token") if _admite_token_query(path) else None

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "No autenticado: inicie sesión para acceder a la API"})

        try:
            payload = verificar_token(token, settings.SECRET_KEY)
            request.state.usuario = identidad_desde_payload(payload)
        except ValueError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": f"Token inválido: {e}"})

        return await call_next(request)
