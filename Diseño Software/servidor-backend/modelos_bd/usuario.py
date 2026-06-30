"""
Modelo ORM: Usuario del sistema (operador / técnico / administrador)
"""

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from .base import Base


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    nombre = Column(String(128), nullable=False, default="")
    rol = Column(String(32), nullable=False, default="operador")  # operador|tecnico|admin
    password_hash = Column(String(256), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UsuarioDB {self.username} ({self.rol})>"
