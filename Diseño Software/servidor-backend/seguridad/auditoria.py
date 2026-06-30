"""
Bitácora de auditoría (append-only)
===================================

Registra cada acción sensible (cambio de parámetros, cambio de modo, activación
de ola verde) con: quién, cuándo, qué, resultado (ACEPTADO/RECHAZADO) y motivo.
Escribe en la base de datos Y en un archivo de texto, de modo que la trazabilidad
sobreviva aunque uno de los dos falle.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_LOG_PATH = Path(__file__).parent.parent.parent / "datos" / "logs-sistema" / "auditoria.log"


def registrar_evento(usuario: str, rol: str, accion: str, recurso: str,
                     resultado: str, motivo: str = "", detalle=None, ip: str = "") -> None:
    """Registra un evento en archivo y BD. resultado ∈ {ACEPTADO, RECHAZADO}."""
    try:
        detalle_str = json.dumps(detalle, ensure_ascii=False, default=str) if detalle is not None else ""
    except Exception:
        detalle_str = str(detalle)

    ts = datetime.utcnow()

    # 1) Archivo (siempre, robusto)
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        linea = (f"{ts.isoformat()}Z | {usuario} ({rol}) | {accion} {recurso} | "
                 f"{resultado} | {motivo} | {detalle_str}")
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception as e:
        logger.warning(f"No se pudo escribir auditoría en archivo: {e}")

    # 2) Base de datos
    try:
        from modelos_bd import SessionLocal
        from modelos_bd.evento_auditoria import EventoAuditoriaDB

        db = SessionLocal()
        try:
            db.add(EventoAuditoriaDB(
                timestamp=ts, usuario=str(usuario), rol=str(rol), accion=accion,
                recurso=recurso, resultado=resultado, motivo=motivo,
                detalle=detalle_str, ip=ip))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"No se pudo escribir auditoría en BD: {e}")

    if resultado == "RECHAZADO":
        logger.warning(f"AUDIT [RECHAZADO] {usuario}({rol}) {accion} {recurso} :: {motivo}")
    else:
        logger.info(f"AUDIT [{resultado}] {usuario}({rol}) {accion} {recurso} :: {motivo}")


def listar_eventos(limite: int = 100) -> List[dict]:
    """Devuelve los últimos eventos de auditoría (de la BD, más recientes primero)."""
    try:
        from modelos_bd import SessionLocal
        from modelos_bd.evento_auditoria import EventoAuditoriaDB

        db = SessionLocal()
        try:
            filas = (db.query(EventoAuditoriaDB)
                     .order_by(EventoAuditoriaDB.id.desc())
                     .limit(limite).all())
            return [{
                "id": f.id,
                "timestamp": (f.timestamp.isoformat() + "Z") if f.timestamp else "",
                "usuario": f.usuario, "rol": f.rol, "accion": f.accion,
                "recurso": f.recurso, "resultado": f.resultado,
                "motivo": f.motivo, "detalle": f.detalle,
            } for f in filas]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"No se pudo leer auditoría de BD: {e}")
        return []
