# 🎬 Videos de Prueba - Procesador de Video Modular

## 🎯 Propósito

Esta carpeta contiene **videos de prueba** para evaluar cada módulo del procesador de video de forma independiente. Esto te permite:

- ✅ Validar que cada componente funciona correctamente
- 📊 Mostrar en presentaciones cómo funciona cada parte
- 🐛 Debuggear problemas específicos sin procesar videos completos
- 🎓 Demostrar el sistema en tu tesis/TFC

---

## 📁 Estructura de Carpetas

```
videos-prueba/
├── deteccion-basica/           # Modo 1: Detección de vehículos
│   ├── test_deteccion_dia.mp4
│   ├── test_deteccion_noche.mp4
│   └── test_deteccion_lluvia.mp4
│
├── analisis-parametros/        # Modo 2: Análisis de parámetros (flujo, velocidad, cola)
│   ├── test_flujo_bajo.mp4
│   ├── test_flujo_moderado.mp4
│   ├── test_congestion.mp4
│   └── test_velocidad.mp4
│
└── deteccion-emergencia/       # Modo 3: Detección de vehículos de emergencia
    ├── test_ambulancia.mp4
    ├── test_bomberos.mp4
    └── test_policia.mp4
```

---

## 🔧 Modos de Procesamiento

### **Modo 1: Detección Básica** 📹
**Carpeta**: `deteccion-basica/`

**Qué hace**:
- Detecta todos los vehículos en el frame
- Dibuja bounding boxes
- Muestra clase y confianza
- **NO** calcula parámetros de tráfico

**Propósito**:
- Validar que YOLO está funcionando
- Verificar precisión de detección
- Evaluar rendimiento en diferentes condiciones

**Comando**:
```bash
python vision_computadora/procesador_modular.py --modo deteccion --video datos/videos-prueba/deteccion-basica/test_deteccion_dia.mp4
```

**Métricas mostradas**:
- Número de vehículos detectados
- FPS de procesamiento
- Confianza promedio de detecciones

---

### **Modo 2: Análisis de Parámetros** 📊
**Carpeta**: `analisis-parametros/`

**Qué hace**:
- Detecta vehículos
- **Trackea** vehículos entre frames
- Calcula **velocidad real** usando tracking
- Calcula **flujo vehicular** (veh/min)
- Mide **longitud de cola** (metros)
- Calcula **ICV real** usando `nucleo/indice_congestion.py`

**Propósito**:
- Validar cálculos de parámetros de tráfico
- Verificar que el tracking funciona
- Evaluar precisión de velocidad estimada
- Confirmar que ICV es real (no random)

**Comando**:
```bash
python vision_computadora/procesador_modular.py --modo parametros --video datos/videos-prueba/analisis-parametros/test_congestion.mp4
```

**Métricas mostradas**:
- Flujo vehicular (veh/min)
- Velocidad promedio (km/h) - **REAL via tracking**
- Longitud de cola (metros)
- ICV - **REAL usando nucleo/**
- Clasificación: Fluido / Moderado / Congestionado

---

### **Modo 3: Detección de Emergencia** 🚑
**Carpeta**: `deteccion-emergencia/`

**Qué hace**:
- Detecta vehículos estándar (YOLO COCO)
- Detecta vehículos de emergencia (YOLO custom)
- Resalta vehículos de emergencia en color especial
- Emite alerta visual/sonora cuando detecta emergencia
- Registra timestamp de detección

**Propósito**:
- Validar modelo custom de emergencias
- Verificar que se distinguen ambulancias/bomberos/policía
- Preparar para integración con sistema de olas verdes

**Comando**:
```bash
python vision_computadora/procesador_modular.py --modo emergencia --video datos/videos-prueba/deteccion-emergencia/test_ambulancia.mp4
```

**Métricas mostradas**:
- Tipo de vehículo de emergencia detectado
- Confianza de detección
- Timestamp de detección
- Alerta de ola verde sugerida

---

## 📥 Cómo Obtener Videos de Prueba

### **Opción 1: Descargar de YouTube**

```python
from pytube import YouTube

# Videos de tráfico en Lima
videos_recomendados = [
    'https://www.youtube.com/watch?v=XXX',  # Tráfico Lima - Av. Arequipa
    'https://www.youtube.com/watch?v=YYY',  # Tráfico nocturno
]

yt = YouTube(videos_recomendados[0])
stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
stream.download(output_path='datos/videos-prueba/deteccion-basica/', filename='test_deteccion_dia.mp4')
```

### **Opción 2: Grabar con Smartphone**

- Grabar intersecciones reales de Lima
- Duración: 1-2 minutos por video
- Resolución: 1080p mínimo
- Formato: MP4 (H.264)
- Posición: Elevada, ángulo oblicuo

### **Opción 3: Usar Videos de Ejemplo**

Datasets públicos con licencia:
- **DETRAC Dataset**: http://detrac-db.rit.albany.edu/
- **UA-DETRAC**: Tráfico urbano con anotaciones
- **VisDrone**: Videos de drones (incluye tráfico)

### **Opción 4: Generar con SUMO**

```bash
# Exportar visualización de SUMO a video
sumo-gui -c lima_simulation.sumocfg --start --quit-on-end --screenshot output_

# Convertir frames a video
ffmpeg -framerate 30 -i output_%04d.png -c:v libx264 -pix_fmt yuv420p datos/videos-prueba/analisis-parametros/test_sumo.mp4
```

---

## 🎥 Recomendaciones de Videos

### **Detección Básica**
- **Día**: Tráfico normal, buena iluminación
- **Noche**: Probar detección con poca luz
- **Lluvia**: Validar robustez en mal clima

### **Análisis de Parámetros**
- **Flujo Bajo**: <30 veh/min (hora valle)
- **Flujo Moderado**: 30-60 veh/min (hora normal)
- **Congestión**: >60 veh/min (hora punta)
- **Velocidad**: Video con tráfico fluido para medir velocidad

### **Detección de Emergencia**
- Videos con ambulancias, bomberos, policía claramente visibles
- Duración: 30-60 segundos
- Vehículo de emergencia debe aparecer en al menos 5 segundos del video

---

## ⚙️ Procesamiento de Videos

### **Comando Unificado**

```bash
# Procesar con modo específico
python vision_computadora/procesador_modular.py \
    --modo [deteccion|parametros|emergencia] \
    --video datos/videos-prueba/[carpeta]/[video].mp4 \
    --visualizar \
    --exportar datos/resultados-video/exportaciones/
```

### **Ejemplo Real**

```bash
# Modo 1: Detección básica
python vision_computadora/procesador_modular.py --modo deteccion --video datos/videos-prueba/deteccion-basica/test_deteccion_dia.mp4 --visualizar

# Modo 2: Análisis de parámetros
python vision_computadora/procesador_modular.py --modo parametros --video datos/videos-prueba/analisis-parametros/test_congestion.mp4 --exportar

# Modo 3: Detección de emergencia
python vision_computadora/procesador_modular.py --modo emergencia --video datos/videos-prueba/deteccion-emergencia/test_ambulancia.mp4 --visualizar --exportar
```

---

## 📊 Outputs Generados

Cada modo genera diferentes outputs en `datos/resultados-video/`:

### **Detección Básica**
```
resultados-video/exportaciones/deteccion_basica/
├── test_deteccion_dia_processed.mp4    # Video con bounding boxes
├── test_deteccion_dia_stats.json       # Estadísticas de detección
└── test_deteccion_dia_detections.csv   # Detecciones frame por frame
```

### **Análisis de Parámetros**
```
resultados-video/exportaciones/analisis_parametros/
├── test_congestion_processed.mp4       # Video con métricas
├── test_congestion_metricas.csv        # Flujo, velocidad, ICV por frame
├── test_congestion_icv_graph.png       # Gráfico de ICV vs tiempo
└── test_congestion_summary.json        # Resumen de métricas
```

### **Detección de Emergencia**
```
resultados-video/exportaciones/deteccion_emergencia/
├── test_ambulancia_processed.mp4       # Video con alertas
├── test_ambulancia_log.csv             # Log de detecciones
├── test_ambulancia_alerts.json         # Timestamps de alertas
└── test_ambulancia_route.json          # Ruta sugerida para ola verde
```

---

## 🎯 Checklist de Evaluación

### **Detección Básica** ✅
- [ ] Detecta autos correctamente
- [ ] Detecta motos correctamente
- [ ] Detecta buses correctamente
- [ ] Detecta camiones correctamente
- [ ] Confianza promedio > 0.7
- [ ] FPS > 15 (tiempo real)
- [ ] Funciona en día/noche/lluvia

### **Análisis de Parámetros** ✅
- [ ] Flujo vehicular es coherente con video
- [ ] Velocidad NO es random (tracking real)
- [ ] Longitud de cola aumenta en congestión
- [ ] ICV calculado usando `nucleo/` (no random)
- [ ] Clasificación correcta (fluido/moderado/congestionado)

### **Detección de Emergencia** ✅
- [ ] Detecta ambulancias
- [ ] Detecta bomberos
- [ ] Detecta policía
- [ ] Distingue emergencia de vehículos normales
- [ ] Alerta se activa correctamente
- [ ] Confianza > 0.6

---

## 🚀 Próximos Pasos

1. **Colocar videos de prueba** en las carpetas correspondientes
2. **Ejecutar procesamiento modular** para validar cada modo
3. **Revisar outputs** en `datos/resultados-video/`
4. **Iterar** si hay problemas (ajustar parámetros, re-entrenar)
5. **Integrar con backend** una vez validado

---

**Estado Actual**: 🟡 **Carpetas creadas - Esperando videos**

Coloca tus videos de prueba en las carpetas correspondientes y ejecuta el procesador modular.
