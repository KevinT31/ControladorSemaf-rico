"""
Configuración base de SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import logging

from config import settings

logger = logging.getLogger(__name__)

# Ruta a la base de datos
_url = make_url(settings.DATABASE_URL)
DB_PATH = None
if _url.drivername.startswith("sqlite") and _url.database not in (None, "", ":memory:"):
    DB_PATH = Path(_url.database)
    if not DB_PATH.is_absolute():
        DB_PATH = (settings.BASE_DIR / DB_PATH).resolve()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _url = _url.set(database=DB_PATH.as_posix())

DATABASE_URL = _url.render_as_string(hide_password=False)
_CONNECT_ARGS = ({"check_same_thread": False}
                 if _url.drivername.startswith("sqlite") else {})

# Motor SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args=_CONNECT_ARGS,
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
    destino = str(DB_PATH) if DB_PATH else _url.render_as_string(hide_password=True)
    logger.info(f"Inicializando base de datos en: {destino}")

    # Importar todos los modelos para que SQLAlchemy los registre
    from . import interseccion, metrica, ola_verde, deteccion_video, usuario, evento_auditoria

    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    logger.info("Base de datos inicializada correctamente")
    logger.info(f"Tablas creadas: {list(Base.metadata.tables.keys())}")
