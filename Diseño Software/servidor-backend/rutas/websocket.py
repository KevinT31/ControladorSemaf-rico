"""
Rutas WebSocket para comunicación en tiempo real
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from seguridad.dependencias import identidad_desde_payload
from seguridad.jwt_simple import verificar_token

router = APIRouter(tags=["WebSocket"])

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para actualizaciones en tiempo real

    El cliente recibe automáticamente:
    - Métricas de intersecciones actualizadas cada segundo
    - Notificaciones de olas verdes activadas/desactivadas
    - Cambios de modo del sistema
    - Alertas de congestión

    Mensajes del cliente pueden incluir comandos:
    - {"comando": "suscribir", "interseccion_id": "LC-001"}
    - {"comando": "desuscribir", "interseccion_id": "LC-001"}
    """
    from servicios.websocket_manager import WebSocketManager

    if settings.AUTH_ENABLED:
        token = websocket.query_params.get("token")
        auth = websocket.headers.get("Authorization", "")
        if not token and auth.lower().startswith("bearer "):
            token = auth[7:].strip()

        try:
            if not token:
                raise ValueError("falta token")
            payload = verificar_token(token, settings.SECRET_KEY)
            usuario = identidad_desde_payload(payload)
        except ValueError as exc:
            cliente = websocket.client.host if websocket.client else "desconocido"
            logger.warning("WebSocket rechazado para %s: %s", cliente, exc)
            # Aceptar y cerrar sin registrar la conexión permite que clientes
            # WebSocket reales reciban el close frame 1008 (en vez de un 403
            # de handshake ambiguo).
            await websocket.accept()
            await websocket.close(code=1008, reason="No autenticado")
            return
    else:
        usuario = {"username": "anonimo", "rol": "operador"}

    await websocket.accept()

    conexion_id = WebSocketManager.agregar_conexion(websocket)
    logger.info(
        "Cliente WebSocket conectado. usuario=%s ID=%s Total=%s",
        usuario["username"], conexion_id, WebSocketManager.total_conexiones())

    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()

            # Procesar comandos del cliente (opcional)
            try:
                comando = json.loads(data)
                if not isinstance(comando, dict):
                    raise ValueError("el mensaje debe ser un objeto JSON")

                if comando.get('comando') == 'suscribir':
                    interseccion_id = comando.get('interseccion_id')
                    if not isinstance(interseccion_id, str) or not interseccion_id.strip():
                        raise ValueError("interseccion_id inválido")
                    WebSocketManager.suscribir_interseccion(conexion_id, interseccion_id)
                    await websocket.send_json({
                        'tipo': 'confirmacion',
                        'mensaje': f'Suscrito a {interseccion_id}'
                    })

                elif comando.get('comando') == 'desuscribir':
                    interseccion_id = comando.get('interseccion_id')
                    if not isinstance(interseccion_id, str) or not interseccion_id.strip():
                        raise ValueError("interseccion_id inválido")
                    WebSocketManager.desuscribir_interseccion(conexion_id, interseccion_id)
                    await websocket.send_json({
                        'tipo': 'confirmacion',
                        'mensaje': f'Desuscrito de {interseccion_id}'
                    })

                elif comando.get('comando') == 'ping':
                    await websocket.send_json({'tipo': 'pong', 'timestamp': comando.get('timestamp')})

            except json.JSONDecodeError:
                logger.warning("Mensaje WebSocket no JSON (longitud=%s)", len(data))
            except ValueError as exc:
                await websocket.send_json({'tipo': 'error', 'mensaje': str(exc)})
            except Exception as e:
                logger.error(f"Error procesando comando WebSocket: {e}")

    except WebSocketDisconnect:
        logger.info("Cliente WebSocket desconectado. ID: %s", conexion_id)
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
    finally:
        WebSocketManager.remover_conexion(conexion_id)
        logger.info("Conexiones WebSocket activas: %s", WebSocketManager.total_conexiones())
