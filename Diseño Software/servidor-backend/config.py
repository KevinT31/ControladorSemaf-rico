"""
Configuración del Sistema
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuraciones del sistema"""

    # Información del sistema
    APP_NAME: str = "Sistema de Control Semafórico Adaptativo"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "API para control inteligente de semáforos con ICV + Lógica Difusa"

    # Servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = Field(default=False, description="Modo debug - configurable por .env")

    # Base de datos
    DATABASE_URL: str = "sqlite:///./base-datos/semaforos.db"
    # Para PostgreSQL/TimescaleDB:
    # DATABASE_URL: str = "postgresql://user:password@localhost:5432/semaforos"

    # Rutas
    BASE_DIR: Path = Path(__file__).parent.parent
    DATOS_DIR: Path = BASE_DIR / "datos"
    BASE_DATOS_DIR: Path = BASE_DIR / "base-datos"
    INTERFAZ_WEB_DIR: Path = BASE_DIR / "interfaz-web"

    # CORS (en producción: lista blanca de dominios, no "*")
    CORS_ORIGINS: list = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # ==================== Ciberseguridad ====================
    # Clave de firma JWT (HS256). Debe definirse fuera del repositorio.
    SECRET_KEY: str = Field(
        default="",
        description="Clave HMAC-SHA256 para firmar tokens JWT")
    TOKEN_EXP_MIN: int = Field(default=480, description="Expiración del token en minutos")
    AUTH_ENABLED: bool = Field(
        default=True, description="Exigir autenticación en la API (desactivar solo para depurar)")

    # Credenciales de demostración. Configurarlas únicamente mediante .env.
    DEMO_OPERATOR_PASSWORD: str = ""
    DEMO_TECHNICIAN_PASSWORD: str = ""
    DEMO_ADMIN_PASSWORD: str = ""

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # segundos

    # Simulación
    SIMULACION_INTERVALO: float = 1.0  # segundos

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = DATOS_DIR / "logs-sistema" / "backend.log"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

if settings.AUTH_ENABLED:
    if len(settings.SECRET_KEY) < 32 or settings.SECRET_KEY.startswith("REPLACE_"):
        raise RuntimeError(
            "SECRET_KEY debe reemplazarse en .env por una clave aleatoria "
            "de al menos 32 caracteres cuando AUTH_ENABLED=true."
        )

    for nombre, valor in {
        "DEMO_OPERATOR_PASSWORD": settings.DEMO_OPERATOR_PASSWORD,
        "DEMO_TECHNICIAN_PASSWORD": settings.DEMO_TECHNICIAN_PASSWORD,
        "DEMO_ADMIN_PASSWORD": settings.DEMO_ADMIN_PASSWORD,
    }.items():
        if valor.startswith("REPLACE_"):
            raise RuntimeError(
                f"{nombre} todavía contiene el placeholder de .env.example."
            )
