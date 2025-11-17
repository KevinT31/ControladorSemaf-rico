# Sistema de Control Semafórico Adaptativo Inteligente

Sistema de control semafórico basado en ICV y Lógica Difusa con detección YOLO y DeepSORT.

## Inicio Rápido

```bash
# Ejecutar menú principal
python ejecutar.py

# Iniciar servidor web
python servidor-backend/main.py
```

## Modos Disponibles

### 1. Simulador
Genera tráfico aleatorio y semáforos en Lima Metropolitana.

### 2. Procesador de Video
- **Opción 1**: Análisis básico (solo detección)
- **Opción 2**: Análisis completo (ICV, velocidad, flujo)
- **Opción 3**: Detección de emergencias

### 3. Frontend (http://localhost:8000)
- **Simulador**: Tráfico generado
- **Procesador Video**: Cámara en tiempo real con detección
- **SUMO**: Integración con simulador SUMO

## Estructura

```
ejecutar.py                 # Punto de entrada principal
servidor-backend/           # API FastAPI
interfaz-web/              # Frontend HTML/JS
vision_computadora/        # YOLO + DeepSORT
nucleo/                    # Motor de lógica difusa e ICV
```

## Requisitos

- Python 3.8+
- OpenCV
- YOLOv8
- FastAPI
- Cámara (para modo video en frontend)
