"""
Modelo ORM: Evento de auditoría (registro inmutable de acciones sensibles)
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from .base import Base


class EventoAuditoriaDB(Base):
    __tablename__ = "eventos_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    usuario = Column(String(64), default="-")
    rol = Column(String(32), default="-")
    accion = Column(String(64), default="")        # p.ej. ACTUALIZAR_PARAMETROS
    recurso = Column(String(160), default="")      # endpoint / recurso afectado
    resultado = Column(String(16), default="")     # ACEPTADO | RECHAZADO
    motivo = Column(Text, default="")
    detalle = Column(Text, default="")             # JSON del payload involucrado
    ip = Column(String(64), default="")

    def __repr__(self):
        return f"<EventoAuditoria {self.resultado} {self.accion} {self.usuario}>"
