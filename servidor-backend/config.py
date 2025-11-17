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

    # CORS
    CORS_ORIGINS: list = ["*"]

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
