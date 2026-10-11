"""
Configuración del Sistema
"""

import secrets
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuraciones del sistema"""

    # Información del sistema
    APP_NAME: str = "Sistema de Control Semafórico Adaptativo"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "API para control inteligente de semáforos con ICV + Lógica Difusa"

    # Servidor
    # Seguro por defecto para la demo local. Para acceso desde la LAN se debe
    # definir HOST=0.0.0.0 de forma explícita y colocar TLS delante del proceso.
    HOST: str = "127.0.0.1"
    PORT: int = Field(default=8000, ge=1, le=65535)
    DEBUG: bool = Field(default=False, description="Modo debug - configurable por .env")

    # Base de datos
    DATABASE_URL: str = f"sqlite:///{(_BASE_DIR / 'base-datos' / 'semaforos.db').as_posix()}"
    # Para PostgreSQL/TimescaleDB:
    # DATABASE_URL: str = "postgresql://USUARIO:CLAVE_ALEATORIA_LARGA@localhost:5432/semaforos"

    # Rutas
    BASE_DIR: Path = _BASE_DIR
    DATOS_DIR: Path = BASE_DIR / "datos"
    BASE_DATOS_DIR: Path = BASE_DIR / "base-datos"
    INTERFAZ_WEB_DIR: Path = BASE_DIR / "interfaz-web"

    # CORS (en producción: lista blanca de dominios, no "*")
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # ==================== Ciberseguridad ====================
    # Sin SECRET_KEY configurada se genera una clave aleatoria por proceso. Esto
    # elimina la clave pública commiteada y mantiene la demo local operativa;
    # despliegues persistentes/multiproceso deben definirla en .env / KeyVault.
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(48),
        min_length=32,
        description="Clave HMAC-SHA256 para firmar tokens JWT")
    TOKEN_EXP_MIN: int = Field(
        default=480, gt=0, le=10_080, description="Expiración del token en minutos")
    AUTH_ENABLED: bool = Field(
        default=True, description="Exigir autenticación en la API (desactivar solo para depurar)")

    # Protección de fuerza bruta del login (por IP y por nombre de usuario).
    LOGIN_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=100)
    LOGIN_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600)
    LOGIN_LOCKOUT_SECONDS: int = Field(default=300, ge=1, le=86_400)

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # segundos

    # Simulación
    SIMULACION_INTERVALO: float = 1.0  # segundos

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = DATOS_DIR / "logs-sistema" / "backend.log"

    class Config:
        env_file = str(_BASE_DIR / ".env")
        case_sensitive = True

    @property
    def secret_key_ephemeral(self) -> bool:
        """Indica que no se proporcionó una clave persistente por configuración."""
        return "SECRET_KEY" not in self.model_fields_set


settings = Settings()
