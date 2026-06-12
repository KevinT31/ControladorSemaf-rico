"""
Script simple para servidor de cámara web
"""
import cv2
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import threading
import time
import numpy as np

app = FastAPI()

# Variables globales
camara_activa = False
ultimo_frame = None
lock = threading.Lock()

def capturar_camara():
    """Thread que captura continuamente de la cámara"""
    global camara_activa, ultimo_frame

    cap = cv2.VideoCapture(0)  # Abrir cámara

    if not cap.isOpened():
        print("No se pudo abrir la camara")
        return

    print("Camara abierta correctamente")
    camara_activa = True

    try:
        while camara_activa:
            ret, frame = cap.read()
            if not ret:
                print("No se pudo leer frame")
                time.sleep(0.1)
                continue

            # Codificar frame como JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                with lock:
                    ultimo_frame = buffer.tobytes()

            time.sleep(0.033)  # ~30 FPS
    finally:
        cap.release()
        print("Camara liberada")

@app.on_event("startup")
async def startup_event():
    """Iniciar thread de cámara al arrancar"""
    thread = threading.Thread(target=capturar_camara, daemon=True)
    thread.start()
    print("Servidor de camara iniciado")

@app.get("/frame")
async def obtener_frame():
    """Obtener el último frame capturado"""
    global ultimo_frame

    with lock:
        if ultimo_frame is None:
            # Generar un frame negro si no hay frame
            frame_negro = np.zeros((480, 640, 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', frame_negro)
            frame_actual = buffer.tobytes()
        else:
            frame_actual = ultimo_frame

    return Response(content=frame_actual, media_type="image/jpeg")

@app.get("/")
async def root():
    return {"status": "ok", "camara_activa": camara_activa}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
