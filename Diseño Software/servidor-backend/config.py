"""
Configuración del Sistema
"""

from pathlib import Path
import secrets
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
    DATABASE_URL: str = (
        f"sqlite:///{(Path(__file__).parent.parent / 'base-datos' / 'semaforos.db').as_posix()}"
    )
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
    # Clave de firma JWT (HS256). En producción: definir SECRET_KEY en .env / KeyVault.
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(48),
        description=("Clave HMAC-SHA256 para firmar tokens JWT. Definir "
                     "SECRET_KEY en el entorno para conservar sesiones entre reinicios"))
    TOKEN_EXP_MIN: int = Field(default=480, description="Expiración del token en minutos")
    AUTH_ENABLED: bool = Field(
        default=True, description="Exigir autenticación en la API (desactivar solo para depurar)")

    # ==================== Control adaptativo (SUMO) ====================
    # Ejecuta el controlador canónico ControladorDifusoIA
    # (integracion-sumo/difuso_ia.py) sobre la simulación SUMO del backend.
    # Valores (env var CONTROL_ADAPTATIVO):
    #   'off'           : sin control adaptativo (comportamiento actual, defecto)
    #   'difuso_ia_off' : difuso acíclico puro (modo_ia='off', sin CNN-LSTM)
    #   'difuso_ia'     : difuso + guardia CNN-LSTM (modo_ia='guardia')
    CONTROL_ADAPTATIVO: str = Field(
        default='off',
        description="Controlador adaptativo sobre SUMO: 'off' | 'difuso_ia_off' | 'difuso_ia'")

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
