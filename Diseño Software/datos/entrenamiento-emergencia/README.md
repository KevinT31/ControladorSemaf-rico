# 🚑 Entrenamiento de Detector de Vehículos de Emergencia

## 🎯 Propósito

Este directorio contiene el dataset y configuración para entrenar un modelo **YOLOv8 custom** que detecte vehículos de emergencia peruanos:

- 🚑 **Ambulancias**
- 🚒 **Bomberos**
- 🚓 **Policía**

El modelo COCO estándar de YOLO no distingue vehículos de emergencia, por lo que necesitamos entrenamiento personalizado.

---

## 📁 Estructura del Dataset

```
entrenamiento-emergencia/
├── dataset.yaml           # Configuración del dataset para YOLO
├── images/
│   ├── train/            # Imágenes de entrenamiento (70-80%)
│   │   ├── ambulancia_001.jpg
│   │   ├── bomberos_001.jpg
│   │   └── policia_001.jpg
│   └── val/              # Imágenes de validación (20-30%)
│       ├── ambulancia_val_001.jpg
│       └── ...
└── labels/
    ├── train/            # Anotaciones YOLO (formato .txt)
    │   ├── ambulancia_001.txt
    │   ├── bomberos_001.txt
    │   └── policia_001.txt
    └── val/
        ├── ambulancia_val_001.txt
        └── ...
```

---

## 🛠️ Proceso de Entrenamiento

### **1. Recolectar Imágenes**

**Fuentes Recomendadas:**
- 📹 YouTube: Videos de tráfico en Lima (extraer frames con `cv2`)
- 🌍 Google Street View: Capturar intersecciones de Lima
- 🗂️ Roboflow Universe: Buscar datasets públicos de vehículos de emergencia
- 🎬 SUMO: Generar tráfico simulado con vehículos de emergencia custom

**Mínimo por Clase:**
- ⚠️ Básico: 100 imágenes (para pruebas)
- ✅ Recomendado: 500 imágenes (para producción)
- 🏆 Óptimo: 1000+ imágenes (para alta precisión)

**Diversidad:**
- ☀️ Diferentes horas del día (día, noche, crepúsculo)
- 🌦️ Diferentes condiciones climáticas
- 📐 Diferentes ángulos y distancias
- 🚦 Con/sin luces de emergencia encendidas

---

### **2. Anotar Imágenes**

**Herramientas:**

1. **LabelImg** (local, gratuita)
   ```bash
   pip install labelImg
   labelImg
   ```
   - Configurar formato: "YOLO"
   - Anotar cada vehículo con bounding box
   - Guardar automáticamente genera `.txt` con formato YOLO

2. **Roboflow** (online, gratuita con límites)
   - https://roboflow.com/
   - Cargar imágenes → Anotar → Exportar formato YOLO

**Formato de Anotación YOLO:**
```
<class_id> <x_center> <y_center> <width> <height>
```
- Valores normalizados entre 0 y 1
- `class_id`: 0=ambulancia, 1=bomberos, 2=policia
- Ejemplo: `0 0.5 0.5 0.3 0.2`

**Ejemplo de archivo `ambulancia_001.txt`:**
```
0 0.512 0.345 0.234 0.189
```

---

### **3. Entrenar el Modelo**

**Comando de Entrenamiento:**

```bash
cd C:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2

# Entrenamiento básico (50 epochs)
yolo train data=datos/entrenamiento-emergencia/dataset.yaml model=yolov8n.pt epochs=50 imgsz=640 batch=16

# Entrenamiento avanzado (100 epochs con data augmentation)
yolo train data=datos/entrenamiento-emergencia/dataset.yaml model=yolov8s.pt epochs=100 imgsz=640 batch=16 patience=20 augment=True
```

**Parámetros:**
- `model=yolov8n.pt`: Modelo base (nano - rápido)
- `model=yolov8s.pt`: Modelo base (small - más preciso)
- `epochs=50`: Número de iteraciones
- `imgsz=640`: Tamaño de imagen de entrada
- `batch=16`: Tamaño de lote (ajustar según GPU)
- `patience=20`: Early stopping si no mejora

**Modelos Disponibles:**
- `yolov8n.pt` - Nano (más rápido, menos preciso)
- `yolov8s.pt` - Small (balance)
- `yolov8m.pt` - Medium (más preciso, más lento)

---

### **4. Validar el Modelo**

```bash
# Validar en dataset de validación
yolo val model=runs/detect/train/weights/best.pt data=datos/entrenamiento-emergencia/dataset.yaml

# Probar en video de prueba
yolo predict model=runs/detect/train/weights/best.pt source=datos/videos-prueba/deteccion-emergencia/test_ambulancia.mp4
```

**Métricas Clave:**
- **mAP50**: Mean Average Precision @ IoU 0.5 (>0.7 es bueno)
- **Precision**: Qué porcentaje de detecciones son correctas
- **Recall**: Qué porcentaje de vehículos se detectaron

---

### **5. Usar el Modelo Entrenado**

```python
from ultralytics import YOLO

# Cargar modelo custom
modelo_emergencia = YOLO('runs/detect/train/weights/best.pt')

# Detectar en imagen
resultados = modelo_emergencia('test_image.jpg')

# Procesar resultados
for r in resultados:
    for box in r.boxes:
        clase = int(box.cls[0])
        nombres = ['ambulancia', 'bomberos', 'policia']
        print(f"Detectado: {nombres[clase]}")
```

---

## 📊 Estrategia si No Tienes Imágenes

### **Opción 1: Usar Dataset Público Existente**

```python
# Descargar dataset de Roboflow
from roboflow import Roboflow

rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("emergency-vehicles").project("emergency-vehicle-detection")
dataset = project.version(1).download("yolov8")
```

### **Opción 2: Extraer Frames de Videos de YouTube**

```python
import cv2
from pytube import YouTube

# Descargar video de tráfico de Lima
yt = YouTube('https://www.youtube.com/watch?v=VIDEO_ID')
stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
stream.download(filename='trafico_lima.mp4')

# Extraer frames cada segundo
cap = cv2.VideoCapture('trafico_lima.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Guardar 1 frame por segundo
    if frame_count % int(fps) == 0:
        cv2.imwrite(f'images/train/frame_{frame_count}.jpg', frame)

    frame_count += 1

cap.release()
```

### **Opción 3: Fine-Tuning con Transfer Learning**

Si no tienes suficientes imágenes, usa transfer learning:

```bash
# Entrenar con menos épocas y congelar capas iniciales
yolo train data=dataset.yaml model=yolov8n.pt epochs=30 freeze=10
```

---

## 🎯 Roadmap

- [ ] Recolectar 100 imágenes por clase (mínimo viable)
- [ ] Anotar imágenes con LabelImg/Roboflow
- [ ] Entrenar modelo inicial (50 epochs)
- [ ] Validar en videos de prueba
- [ ] Recolectar 500 imágenes por clase (producción)
- [ ] Re-entrenar modelo mejorado (100 epochs)
- [ ] Integrar en `detector_emergencia.py`
- [ ] Desplegar en sistema de producción

---

## 📚 Recursos

- **YOLOv8 Docs**: https://docs.ultralytics.com/
- **LabelImg**: https://github.com/tzutalin/labelImg
- **Roboflow**: https://roboflow.com/
- **COCO Dataset**: https://cocodataset.org/
- **YouTube Traffic Videos Lima**: Buscar "tráfico Lima tiempo real"

---

## ⚠️ Notas Importantes

1. **Propiedad Intelectual**: Solo usar imágenes con licencia apropiada
2. **Privacidad**: Difuminar rostros y placas si es necesario
3. **Bias**: Incluir diversidad de modelos de vehículos peruanos
4. **Calidad**: Imágenes nítidas, bien iluminadas, sin blur excesivo

---

**Estado Actual**: 🟡 **Dataset vacío - Necesita población**

Una vez tengas imágenes anotadas, el entrenamiento tomará ~30 minutos con GPU o ~2 horas con CPU.
