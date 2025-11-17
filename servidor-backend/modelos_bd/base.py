"""
Configuración base de SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Ruta a la base de datos
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "base-datos" / "semaforos.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# URL de conexión
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Motor SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Solo para SQLite
    echo=False  # True para debug SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para FastAPI que proporciona una sesión de base de datos

    Uso:
        @app.get("/")
        def read_data(db: Session = Depends(get_db)):
            return db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa todas las tablas de la base de datos
    """
    logger.info(f"Inicializando base de datos en: {DB_PATH}")

    # Importar todos los modelos para que SQLAlchemy los registre
    from . import interseccion, metrica, ola_verde, deteccion_video

    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    logger.info("Base de datos inicializada correctamente")
    logger.info(f"Tablas creadas: {list(Base.metadata.tables.keys())}")
