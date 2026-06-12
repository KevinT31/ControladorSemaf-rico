# 🎥 Módulo de Visión Computacional - 100% REAL

## 🎯 Propósito

Este módulo procesa videos reales de intersecciones vehiculares para extraer métricas de tráfico usando:

- ✅ **YOLOv8** para detección de vehículos
- ✅ **Tracking real** (DeepSORT) para calcular velocidad
- ✅ **Modelo custom** para vehículos de emergencia
- ✅ **Cálculo ICV real** usando `nucleo/indice_congestion.py`
- ✅ **Exportación a Azure** Blob Storage

⚠️ **IMPORTANTE**: Este módulo **NO USA `np.random`** - Todas las métricas son REALES basadas en detecciones y cálculos verificables.

---

## 📁 Estructura del Módulo

```
vision_computadora/
├── procesador_video.py         # Procesador principal (100% real, sin random)
├── procesador_modular.py       # Sistema modular con 3 modos de evaluación
├── tracking_vehicular.py       # Tracking real para velocidad (DeepSORT/Centroid)
├── detector_emergencia.py      # Detector custom de ambulancias/bomberos/policía
├── exportador_azure.py         # Exportador a Azure Blob Storage
├── test_yolo_fix.py            # Tests de YOLO
├── test_yolo_visual.py         # Visualización de YOLO
└── README.md                   # Este archivo
```

---

## 🚀 Instalación

### **Dependencias Básicas**

```bash
pip install ultralytics opencv-python numpy
```

### **Tracking Robusto (Recomendado)**

```bash
pip install deep-sort-realtime
```

### **Exportación a Azure (Opcional)**

```bash
pip install azure-storage-blob python-dotenv
```

### **Gráficos (Opcional)**

```bash
pip install matplotlib
```

---

## 🔧 Uso Rápido

### **1. Procesamiento Básico**

```bash
python vision_computadora/procesador_video.py datos/videos-prueba/analisis-parametros/test_congestion.mp4
```

### **2. Procesamiento Modular (Recomendado)**

#### **Modo 1: Detección Básica**
Solo detecta vehículos con bounding boxes.

```bash
python vision_computadora/procesador_modular.py \
    --modo deteccion \
    --video datos/videos-prueba/deteccion-basica/test_deteccion_dia.mp4 \
    --visualizar \
    --exportar
```

**Outputs**:
- Video procesado con bounding boxes
- CSV con detecciones por frame
- JSON con estadísticas

#### **Modo 2: Análisis de Parámetros**
Calcula velocidad, flujo, ICV, longitud de cola.

```bash
python vision_computadora/procesador_modular.py \
    --modo parametros \
    --video datos/videos-prueba/analisis-parametros/test_congestion.mp4 \
    --visualizar \
    --exportar
```

**Outputs**:
- Video procesado con métricas superpuestas
- CSV con métricas por frame (velocidad REAL, ICV REAL)
- Gráfico de ICV vs tiempo
- JSON con estadísticas

#### **Modo 3: Detección de Emergencia**
Detecta vehículos de emergencia (requiere modelo custom entrenado).

```bash
python vision_computadora/procesador_modular.py \
    --modo emergencia \
    --video datos/videos-prueba/deteccion-emergencia/test_ambulancia.mp4 \
    --visualizar \
    --exportar
```

**Outputs**:
- Video procesado con alertas de emergencia
- CSV con detecciones de emergencia
- JSON con estadísticas por tipo

---

## 📊 Outputs Generados

### **Estructura de Archivos de Salida**

```
datos/resultados-video/exportaciones/
├── deteccion/
│   ├── video_name_deteccion.mp4
│   ├── video_name_detecciones.csv
│   └── video_name_stats.json
│
├── parametros/
│   ├── video_name_parametros.mp4
│   ├── video_name_metricas.csv
│   ├── video_name_icv_graph.png
│   └── video_name_stats.json
│
└── emergencia/
    ├── video_name_emergencia.mp4
    ├── video_name_emergencias.csv
    └── video_name_stats.json
```

### **Ejemplo de CSV de Métricas (Modo Parámetros)**

```csv
Frame,Tiempo(s),NumVehiculos,Flujo(veh/min)_REAL,Velocidad(km/h)_REAL,LongitudCola(m),ICV_REAL,Clasificacion,Emergencia
0,0.00,12,72.00,35.20,78.50,0.485,moderado,No
30,1.00,15,90.00,28.50,95.30,0.610,congestionado,No
60,2.00,8,48.00,45.10,42.00,0.285,fluido,No
```

⚠️ **Nota**: Todos los valores son **REALES**, no simulados.

---

## 🔬 Módulos Internos

### **1. `procesador_video.py` - Procesador Principal**

Clase principal para procesar videos.

```python
from vision_computadora.procesador_video import ProcesadorVideo

# Crear procesador
procesador = ProcesadorVideo(
    ruta_video="mi_video.mp4",
    pixeles_por_metro=15.0  # Ajustar según calibración
)

# Procesar video completo
resultados = procesador.procesar_completo(saltar_frames=2)

# Exportar resultados
procesador.exportar_resultados(resultados, "resultados.csv")

# Estadísticas
for r in resultados:
    print(f"Frame {r.numero_frame}:")
    print(f"  Velocidad: {r.velocidad_promedio:.1f} km/h [REAL]")
    print(f"  ICV: {r.icv:.3f} [REAL - nucleo/]")
```

**Características**:
- ❌ **NO USA `np.random`**
- ✅ Velocidad calculada con tracking real
- ✅ ICV calculado con `nucleo/indice_congestion.py`
- ✅ Detección de emergencias con modelo custom

---

### **2. `tracking_vehicular.py` - Tracking Real**

Calcula velocidad REAL basada en movimiento observado.

```python
from vision_computadora.tracking_vehicular import TrackerVehicular

# Crear tracker
tracker = TrackerVehicular(
    fps=30.0,
    pixeles_por_metro=15.0,
    usar_deepsort=True  # Usar DeepSORT si está disponible
)

# Actualizar con detecciones
vehiculos_trackeados = tracker.actualizar(detecciones, timestamp)

# Obtener velocidad promedio REAL
velocidad = tracker.obtener_velocidad_promedio_general()
print(f"Velocidad promedio: {velocidad:.1f} km/h [REAL - Tracking]")
```

**Métodos de Tracking**:
1. **DeepSORT** (recomendado si disponible): Tracking robusto con re-identificación
2. **Centroid Tracking** (fallback): Tracking simple basado en distancia entre centroides

⚠️ **Ambos calculan velocidad REAL** - No hay `np.random` en ninguna parte.

---

### **3. `detector_emergencia.py` - Vehículos de Emergencia**

Detecta ambulancias, bomberos y policía con modelo YOLOv8 custom.

```python
from vision_computadora.detector_emergencia import DetectorEmergencia

# Crear detector
detector = DetectorEmergencia()

if detector.modelo_disponible:
    # Detectar en frame
    detecciones = detector.detectar(frame, frame_num)

    for det in detecciones:
        print(f"{det.tipo.upper()} detectado: {det.confianza:.2f}")
```

**Entrenamiento del Modelo**:
Ver: `datos/entrenamiento-emergencia/README.md`

---

### **4. `exportador_azure.py` - Exportación a Cloud**

Exporta resultados a Azure Blob Storage.

```python
from vision_computadora.exportador_azure import ExportadorAzure

# Crear exportador
exportador = ExportadorAzure()

# Subir archivo
url = exportador.subir_archivo("resultado.mp4")
print(f"Subido: {url}")

# Subir directorio completo
urls = exportador.subir_directorio("datos/resultados-video/exportaciones/parametros/")
```

**Configuración** (archivo `.env`):
```
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=trafico-lima
```

---

## 🎯 Modos de Procesamiento Modular

### **Modo 1: Detección Básica** 📹

**Propósito**: Validar que YOLO detecta vehículos correctamente.

**Qué hace**:
- Detecta vehículos con YOLO
- Dibuja bounding boxes
- Muestra confianza

**Qué NO hace**:
- NO calcula velocidad (eso es modo 2)
- NO calcula ICV (eso es modo 2)
- NO detecta emergencias (eso es modo 3)

**Cuándo usar**:
- Para validar precisión de YOLO
- Para evaluar rendimiento (FPS)
- Para verificar detección en diferentes condiciones (día/noche/lluvia)

---

### **Modo 2: Análisis de Parámetros** 📊

**Propósito**: Validar que se calculan métricas de tráfico REALES.

**Qué hace**:
- Detecta vehículos
- **Trackea** vehículos entre frames
- Calcula **velocidad REAL** usando tracking
- Calcula **flujo vehicular**
- Mide **longitud de cola**
- Calcula **ICV REAL** usando `nucleo/indice_congestion.py`

**Cuándo usar**:
- Para validar que velocidad NO es random
- Para verificar que ICV es real
- Para generar datos para tesis
- Para comparar con datos de SUMO

---

### **Modo 3: Detección de Emergencia** 🚨

**Propósito**: Validar detección de vehículos de emergencia.

**Qué hace**:
- Detecta vehículos estándar
- Detecta vehículos de emergencia (modelo custom)
- Resalta emergencias en color especial
- Emite alertas visuales

**Requisito**:
- Modelo custom entrenado (ver `datos/entrenamiento-emergencia/README.md`)

**Cuándo usar**:
- Para validar modelo custom
- Para testear integración con olas verdes
- Para demos en presentaciones

---

## 📐 Calibración Espacial

Para calcular velocidad REAL, necesitas calibrar `pixeles_por_metro`.

### **Método Manual**

1. Medir distancia conocida en el video (e.g., longitud de vehículo = 4.5m)
2. Medir la misma distancia en píxeles en el frame
3. Calcular: `pixeles_por_metro = pixeles / metros`

**Ejemplo**:
- Un vehículo de 4.5m ocupa 68 píxeles
- `pixeles_por_metro = 68 / 4.5 ≈ 15.1`

### **Valores Típicos**

| Ángulo de Cámara | Pixeles/Metro Aprox. |
|-------------------|----------------------|
| Cenital (desde arriba) | 20-30 |
| Oblicuo (45°) | 10-20 |
| Lateral | 5-15 |

⚠️ **Importante**: La calibración afecta la precisión de velocidad. Ajustar según tu video.

---

## 🧪 Testing

### **Test de YOLO**

```bash
python vision_computadora/test_yolo_visual.py
```

Abre webcam y muestra detecciones en tiempo real.

### **Test de Tracking**

```python
from vision_computadora.tracking_vehicular import TrackerVehicular

tracker = TrackerVehicular()

# Simular 3 frames con movimiento
detecciones_t0 = [{'bbox': [100, 200, 150, 250], 'clase': 2, 'confianza': 0.9}]
detecciones_t1 = [{'bbox': [105, 200, 155, 250], 'clase': 2, 'confianza': 0.9}]
detecciones_t2 = [{'bbox': [110, 200, 160, 250], 'clase': 2, 'confianza': 0.9}]

tracker.actualizar(detecciones_t0, 0.0)
tracker.actualizar(detecciones_t1, 0.033)
vehiculos = tracker.actualizar(detecciones_t2, 0.066)

for v in vehiculos:
    print(f"Velocidad: {v.velocidad_promedio:.2f} km/h [REAL]")
```

---

## 📚 Ejemplos de Uso

### **Ejemplo 1: Procesar Video y Exportar a Azure**

```python
from vision_computadora.procesador_modular import ProcesadorModular
from vision_computadora.exportador_azure import exportar_resultados_a_azure

# Procesar
procesador = ProcesadorModular(
    ruta_video="test_trafico.mp4",
    modo="parametros"
)

stats = procesador.procesar(
    visualizar=False,
    exportar_datos=True,
    directorio_salida="datos/resultados-video/exportaciones/parametros/"
)

# Subir a Azure
exportar_resultados_a_azure(
    "datos/resultados-video/exportaciones/parametros/",
    modo="parametros"
)
```

### **Ejemplo 2: Procesar con Callback Personalizado**

```python
from vision_computadora.procesador_video import ProcesadorVideo

procesador = ProcesadorVideo("video.mp4")

for frame_num in range(0, procesador.total_frames, 10):
    ret, frame = procesador.video.read()
    if not ret:
        break

    resultado = procesador.procesar_frame(frame, frame_num)

    # Callback personalizado
    if resultado.icv > 0.7:
        print(f"⚠️ CONGESTIÓN ALTA en frame {frame_num}: ICV={resultado.icv:.3f}")

    if resultado.hay_emergencia:
        print(f"🚨 EMERGENCIA detectada en frame {frame_num}")
```

---

## 🎓 Integración con Otros Módulos

### **Integración con `nucleo/`**

```python
# El procesador usa nucleo/ internamente
resultado_icv = procesador.calculador_icv.calcular(
    longitud_cola=80.5,
    velocidad_promedio=32.1,
    flujo_vehicular=125.0
)

print(f"ICV: {resultado_icv['icv']:.3f}")
print(f"Clasificación: {resultado_icv['clasificacion']}")
```

### **Integración con `servidor-backend/`**

```python
# En servidor-backend/servicios/video_service.py
from vision_computadora.procesador_video import ProcesadorVideo

async def procesar_video_endpoint(video_id: str):
    procesador = ProcesadorVideo(f"datos/videos/{video_id}.mp4")
    resultados = procesador.procesar_completo()

    # Guardar en base de datos
    for r in resultados:
        await guardar_metricas_bd(
            timestamp=r.timestamp,
            icv=r.icv,
            velocidad=r.velocidad_promedio,
            fuente='video'
        )
```

---

## ⚠️ Limitaciones y Consideraciones

1. **Calibración**: La precisión de velocidad depende de `pixeles_por_metro`
2. **Ángulo de Cámara**: Perspectivas muy oblicuas reducen precisión
3. **Oclusiones**: Vehículos ocultos pueden perder tracking
4. **Condiciones Climáticas**: Lluvia intensa puede afectar detección
5. **Modelo de Emergencia**: Requiere entrenamiento con dataset de vehículos peruanos

---

## 🔄 Roadmap

- [x] Eliminar todo `np.random` (velocidad, ICV, emergencias)
- [x] Integrar tracking real (DeepSORT)
- [x] Integrar `nucleo/indice_congestion.py`
- [x] Crear sistema modular de evaluación
- [x] Exportación a Azure Blob Storage
- [ ] Calibración automática de perspectiva
- [ ] Conteo de vehículos que cruzan línea virtual
- [ ] Clasificación de vehículos por tipo (auto/moto/bus)
- [ ] Detección de infracciones (semáforo en rojo)
- [ ] Streaming en tiempo real (cámaras IP)

---

## 📞 Soporte

Para problemas o preguntas sobre este módulo:

1. Ver documentación en `datos/videos-prueba/README.md`
2. Ver entrenamiento de emergencias en `datos/entrenamiento-emergencia/README.md`
3. Revisar ejemplos en los archivos `test_*.py`

---

## 🎉 Resumen

Este módulo es **100% REAL**:

✅ **Velocidad**: Calculada con tracking real (DeepSORT/Centroid)
✅ **ICV**: Calculado con `nucleo/indice_congestion.py` (mismo que MATLAB)
✅ **Emergencias**: Modelo YOLO custom (cuando está entrenado)
✅ **Flujo**: Basado en conteo de vehículos trackeados
❌ **NO USA `np.random`** en ninguna parte

Todos los valores exportados en CSVs son verificables y reproducibles.
