"""
Rutas WebSocket para comunicación en tiempo real
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

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

    await websocket.accept()

    conexion_id = WebSocketManager.agregar_conexion(websocket)
    logger.info(f"Cliente WebSocket conectado. ID: {conexion_id}. Total: {WebSocketManager.total_conexiones()}")

    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()

            # Procesar comandos del cliente (opcional)
            try:
                import json
                comando = json.loads(data)

                if comando.get('comando') == 'suscribir':
                    interseccion_id = comando.get('interseccion_id')
                    WebSocketManager.suscribir_interseccion(conexion_id, interseccion_id)
                    await websocket.send_json({
                        'tipo': 'confirmacion',
                        'mensaje': f'Suscrito a {interseccion_id}'
                    })

                elif comando.get('comando') == 'desuscribir':
                    interseccion_id = comando.get('interseccion_id')
                    WebSocketManager.desuscribir_interseccion(conexion_id, interseccion_id)
                    await websocket.send_json({
                        'tipo': 'confirmacion',
                        'mensaje': f'Desuscrito de {interseccion_id}'
                    })

                elif comando.get('comando') == 'ping':
                    await websocket.send_json({'tipo': 'pong', 'timestamp': comando.get('timestamp')})

            except json.JSONDecodeError:
                logger.warning(f"Mensaje no JSON recibido: {data}")
            except Exception as e:
                logger.error(f"Error procesando comando WebSocket: {e}")

    except WebSocketDisconnect:
        WebSocketManager.remover_conexion(conexion_id)
        logger.info(f"Cliente WebSocket desconectado. ID: {conexion_id}. Total: {WebSocketManager.total_conexiones()}")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        WebSocketManager.remover_conexion(conexion_id)
