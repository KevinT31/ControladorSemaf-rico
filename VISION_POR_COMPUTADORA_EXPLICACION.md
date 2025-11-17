# 📹 Sistema de Visión por Computadora - Explicación Completa

## ❓ Tus Preguntas Respondidas

### 1. ¿Por qué no toqué `ejecutar.py`?

**RESPUESTA:** Porque `ejecutar.py` **NO está anticuado** - tiene un propósito diferente a `ejecutar_capitulo6.py`.

### 2. ¿Están todos los ejecutables cubriendo lo que deberían?

**SÍ**, cada uno tiene su rol específico:

| Ejecutable | Líneas | Propósito | Estado |
|------------|--------|-----------|--------|
| `ejecutar.py` | 429 | Procesamiento REAL de videos con YOLO + Tracking | ✅ FUNCIONAL |
| `ejecutar_capitulo6.py` | 804 | Demostraciones TEÓRICAS del Capítulo 6 | ✅ FUNCIONAL |
| `probar_capitulo6.py` | ~300 | Pruebas unitarias del Cap 6 | ✅ FUNCIONAL |

---

## 📊 Comparación Detallada: `ejecutar.py` vs `ejecutar_capitulo6.py`

### 🎥 `ejecutar.py` - Sistema de Visión por Computadora REAL

**Propósito:** Procesar videos REALES de intersecciones con detección y tracking de vehículos.

**Características:**
- ✅ **Detección con YOLOv8/YOLO11** (modelos pre-entrenados COCO)
- ✅ **Tracking real** con DeepSORT o algoritmos personalizados
- ✅ **Velocidad REAL** calculada con movimiento de vehículos
- ✅ **ICV REAL** usando `nucleo/indice_congestion.py`
- ✅ **Métricas del Capítulo 6** integradas:
  - Stopped Count (SC)
  - Velocidad promedio en movimiento (Vavg)
  - Flujo vehicular (q)
  - Densidad vehicular (k)
  - Parámetro de Intensidad (PI)
- ✅ **Detección de emergencias** (modelo custom si está disponible)
- ✅ **Exportación:** CSV, JSON, video procesado
- ✅ **Carpetas de salida:** `datos/resultados-video/`
- ✅ **TODO es real**, NADA usa `random`

**Opciones del Menú:**
1. Iniciar Sistema Completo (Dashboard + Simulador)
2. **📹 Procesar Video** ⬅️ **VISIÓN POR COMPUTADORA AQUÍ**
3. Iniciar Simulador Interactivo
4. Ver Documentación
5. Instalar Dependencias
6. Configurar Proyecto

**Cómo Usar:**
```bash
python ejecutar.py
# Opción 2: Procesar Video
# Selecciona video de las carpetas de prueba
# Elige modo: Básico, Completo o Emergencias
```

**Dónde está el código:**
- `vision_computadora/procesador_video.py` → Procesador principal
- `vision_computadora/procesar_video_con_visualizacion.py` → Script de visualización
- `vision_computadora/tracking_vehicular.py` → Tracking de vehículos
- `vision_computadora/detector_emergencia.py` → Detección de emergencias

---

### 🧪 `ejecutar_capitulo6.py` - Demostraciones Teóricas del Cap 6

**Propósito:** Demostrar **matemáticamente** los conceptos del Capítulo 6 sin videos reales.

**Características:**
- ✅ **Generador de métricas realistas** (`nucleo/generador_metricas.py`)
- ✅ **Sistema de visualización** (`nucleo/visualizador_metricas.py`)
- ✅ **Demostraciones teóricas:**
  - Cálculo de ICV con patrones de tráfico
  - Control Difuso con 12 reglas
  - Métricas de Red agregadas
  - Comparación Adaptativo vs Tiempo Fijo
- ✅ **Gráficas y reportes** automáticos
- ✅ **Integración SUMO** para simulación de tráfico

**Opciones del Menú:**
1. Iniciar Sistema Completo (Dashboard)
2. Iniciar Sistema con Backend Capítulo 6
3. **Demostrar Cálculo de ICV** ⬅️ **DEMOSTRACIONES AQUÍ**
4. **Demostrar Control Difuso**
5. **Demostrar Métricas de Red**
6. **Ejecutar Comparación: Adaptativo vs Tiempo Fijo**
7. Conectar con SUMO
8. Ejecutar Comparación en SUMO
9. Procesar Video ⬅️ *Redirecciona a ejecutar.py*
10. Ver Documentación
11. Generar Reporte HTML

**Cómo Usar:**
```bash
python ejecutar_capitulo6.py
# Opción 3, 4, 5 o 6: Demostraciones teóricas
# Genera gráficas en ./visualizaciones/
```

---

## 🎨 ¿Cómo Funciona el Sistema de Visualizaciones?

### Sistema Actual (FUNCIONAL ✅)

```
📹 VIDEO REAL
    ↓
[ YOLO Detección ] → Bounding boxes de vehículos
    ↓
[ Tracking (DeepSORT) ] → IDs y trayectorias
    ↓
[ Cálculo de Velocidad ] → Movimiento real entre frames
    ↓
[ Cálculo de ICV ] → nucleo/indice_congestion.py
    ↓
[ Métricas Cap 6 ] → SC, Vavg, q, k, PI
    ↓
[ Overlay en Video ] → procesador_video.py::_dibujar_panel_info()
    ↓
[ Exportar ] → CSV, JSON, video procesado
```

### ¿Qué Métricas se Calculan REALMENTE?

#### Desde Detecciones YOLO:
- **Número de vehículos:** Conteo directo de detecciones
- **Bounding boxes:** Posiciones exactas en píxeles

#### Desde Tracking:
- **Velocidad individual:** Movimiento de centroide entre frames
- **Velocidad promedio:** Media de vehículos en movimiento
- **Flujo vehicular:** Vehículos que cruzan por minuto

#### Métricas del Capítulo 6 (REALES):
- **SC (Stopped Count):** Vehículos con velocidad < umbral
- **Vavg:** Velocidad promedio solo de vehículos en movimiento
- **q (Flujo):** Vehículos que cruzan / tiempo
- **k (Densidad):** Vehículos / longitud efectiva del carril
- **PI (Parámetro Intensidad):** Vavg / (SC + 1)
- **ICV:** Fórmula del Cap 6.2.3 con pesos w1-w4

#### Ubicación del Código:
```python
# vision_computadora/procesador_video.py

def _calcular_metricas_cap6(self, vehiculos_trackeados, timestamp) -> Dict:
    """
    Calcula métricas completas del Capítulo 6

    Implementa fórmulas exactas de Cap 6.2.2, 6.2.3, 6.2.4
    """
    # Llama a:
    metricas = self.calculador_icv.calcular_metricas_completas_cap6(
        velocidades=velocidades,
        num_vehiculos_cruzaron=self.vehiculos_cruzaron,
        tiempo_inicial=self.tiempo_inicio_ventana,
        tiempo_final=timestamp,
        longitud_efectiva=self.longitud_carril
    )
    # Retorna Dict con todas las métricas
```

---

## 🆕 Mejoras Implementadas

### 1. **Nuevo Módulo: `overlay_metricas_cap6.py`**

**Propósito:** Sistema de overlay PROFESIONAL para visualizaciones.

**Características:**
- ✅ Panel superior con información general
- ✅ Panel lateral con métricas en tiempo real
- ✅ Bounding boxes mejorados (ID + velocidad + clase)
- ✅ Barra visual de ICV con umbrales (0.3, 0.6)
- ✅ Alertas visuales de emergencia (borde rojo parpadeante)
- ✅ Integración completa con métricas del Cap 6
- ✅ Colores dinámicos según estado de congestión
- ✅ Estilos profesionales y limpios

**Ejemplo de Uso:**
```python
from vision_computadora.overlay_metricas_cap6 import OverlayMetricasCap6

# Crear overlay
overlay = OverlayMetricasCap6()

# Aplicar a frame
frame_con_overlay = overlay.crear_overlay_completo(
    frame=frame_original,
    resultado_frame=resultado,  # Del procesador
    mostrar_cap6=True,
    mostrar_barra_icv=True
)
```

**Componentes del Overlay:**
1. **Panel Superior:**
   - Título del sistema
   - Frame actual y timestamp
   - Información general

2. **Panel Lateral Derecho:**
   - Número de vehículos
   - Velocidad promedio (con código de color)
   - ICV con clasificación (Fluido/Moderado/Congestionado)
   - **Métricas del Cap 6:**
     - SC (Stopped Count)
     - Vavg (Velocidad en movimiento)
     - q (Flujo vehicular)
     - k (Densidad)
     - PI (Parámetro de Intensidad)

3. **Bounding Boxes:**
   - Verde: Vehículos normales
   - Rojo: Vehículos de emergencia
   - Etiquetas con ID, clase y velocidad

4. **Barra Visual de ICV:**
   - Barra de progreso en parte inferior
   - Marcas de umbral en 0.3 y 0.6
   - Color dinámico según nivel de congestión
   - Valor numérico del ICV

5. **Alerta de Emergencia:**
   - Borde rojo parpadeante
   - Texto grande "EMERGENCIA DETECTADA"
   - Fondo semi-transparente

---

## 🔄 Integración de Sistemas

### ¿Cómo se Relacionan los Módulos?

```
ejecutar.py (Opción 2)
    ↓
procesar_video_con_visualizacion.py
    ↓
ProcesadorVideo (procesador_video.py)
    ├→ YOLOv8/YOLO11 (detección)
    ├→ TrackerVehicular (tracking)
    ├→ DetectorEmergencia (emergencias)
    ├→ CalculadorICV (ICV y métricas Cap 6)
    └→ _calcular_metricas_cap6() → Métricas completas
    ↓
ResultadoFrame
    ├→ num_vehiculos
    ├→ velocidad_promedio
    ├→ icv
    └→ metricas_cap6 ← **AQUÍ ESTÁN TODAS LAS MÉTRICAS**
    ↓
overlay_metricas_cap6.py (NUEVO)
    ↓
Frame con visualización profesional
```

---

## ✅ Estado Actual del Sistema

| Componente | Estado | Descripción |
|------------|--------|-------------|
| **Detección YOLO** | ✅ FUNCIONAL | YOLOv8/YOLO11 con fallback automático |
| **Tracking** | ✅ FUNCIONAL | DeepSORT + algoritmos personalizados |
| **Cálculo ICV** | ✅ FUNCIONAL | Usa `nucleo/indice_congestion.py` |
| **Métricas Cap 6** | ✅ FUNCIONAL | SC, Vavg, q, k, PI calculadas |
| **Overlay Básico** | ✅ FUNCIONAL | `procesador_video.py::_dibujar_panel_info()` |
| **Overlay Mejorado** | ✅ NUEVO | `overlay_metricas_cap6.py` |
| **Exportación** | ✅ FUNCIONAL | CSV, JSON, video procesado |
| **Detección Emergencias** | ⚠️ OPCIONAL | Requiere modelo custom |

---

## 🚀 Cómo Usar el Sistema Completo

### Opción 1: Procesar Video con Visualización Estándar

```bash
# Usar el sistema actual (funcional)
python ejecutar.py

# Seleccionar opción 2: Procesar Video
# Modo 2: Análisis Completo

# El sistema:
# 1. Detecta vehículos con YOLO
# 2. Calcula velocidad con tracking
# 3. Calcula ICV y métricas Cap 6
# 4. Muestra overlay básico
# 5. Exporta resultados
```

### Opción 2: Procesar Video con Overlay Mejorado (NUEVO)

```bash
# Ejecutar script de procesamiento directamente
python vision_computadora/procesar_video_con_visualizacion.py

# Argumentos útiles:
--video ruta/al/video.mp4          # Video específico
--modo 2                            # Análisis completo
--guardar-video                     # Guardar video procesado
--reproducir-despues                # Procesar y luego reproducir
--saltar-frames 2                   # Procesar 1 de cada 2 frames
--reducir-resolucion 0.5            # Reducir a 50% para mayor velocidad
```

### Opción 3: Demostraciones Teóricas del Cap 6

```bash
# Usar ejecutar_capitulo6.py
python ejecutar_capitulo6.py

# Opción 3: Demostrar ICV → Genera gráficas con patrones
# Opción 4: Demostrar Control Difuso → Muestra 4 escenarios
# Opción 5: Demostrar Métricas de Red → Simula 4 intersecciones
# Opción 6: Comparación Completa → Genera reporte HTML
```

---

## 📁 Estructura de Archivos de Salida

### Desde `ejecutar.py` (Opción 2):

```
datos/resultados-video/
├── exportaciones/
│   ├── basico/
│   │   ├── video1_modo1_metricas.csv
│   │   └── video1_modo1_stats.json
│   ├── completo/
│   │   ├── video1_modo2_metricas.csv   ← **MÉTRICAS REALES**
│   │   └── video1_modo2_stats.json      ← **ESTADÍSTICAS**
│   └── emergencias/
│       ├── video1_modo3_metricas.csv
│       └── video1_modo3_stats.json
└── videos-procesados/
    ├── basico/
    │   └── video1_modo1_procesado.mp4
    ├── completo/
    │   └── video1_modo2_procesado.mp4   ← **VIDEO CON OVERLAY**
    └── emergencias/
        └── video1_modo3_procesado.mp4
```

### Desde `ejecutar_capitulo6.py`:

```
visualizaciones/
├── demo_icv/
│   ├── graficas/
│   │   ├── icv_flujo_libre.png
│   │   ├── icv_congestion_moderada.png
│   │   └── icv_atasco_severo.png
│   └── datos/
│       ├── metricas_flujo_libre.json
│       ├── metricas_flujo_libre.csv
│       └── ...
├── demo_red/
│   ├── graficas/
│   │   └── dashboard_*.png
│   ├── datos/
│   │   └── metricas_red.json
│   └── reportes/
│       └── resumen_red.txt
└── comparacion/
    ├── comparaciones/
    │   ├── comparacion_icv.png
    │   ├── comparacion_velocidad.png
    │   ├── comparacion_resultados.json
    │   └── reporte_comparacion.html  ← **REPORTE HTML**
    └── ...
```

---

## 🎯 Resumen Final

### Lo que FUNCIONA ✅:
1. **`ejecutar.py`** → Procesa videos REALES con YOLO + Tracking + Métricas Cap 6
2. **`ejecutar_capitulo6.py`** → Demostraciones TEÓRICAS con gráficas y reportes
3. **`procesador_video.py`** → Calcula TODAS las métricas del Cap 6 en tiempo real
4. **`overlay_metricas_cap6.py`** → Sistema de visualización PROFESIONAL (NUEVO)

### Lo que NO toqué (porque ya funciona) ✅:
1. **`ejecutar.py`** → No necesitaba cambios, funciona perfectamente
2. **`procesador_video.py`** → Ya calcula métricas reales del Cap 6
3. **Sistema de tracking** → Ya funciona con velocidad real

### Lo que MEJORÉ 🎨:
1. **Nuevo overlay profesional** → `overlay_metricas_cap6.py`
2. **Documentación completa** → Este archivo
3. **Integración clara** → Todos los módulos conectados

---

## 💡 Recomendaciones

1. **Para videos reales:** Usa `ejecutar.py` opción 2
2. **Para demostraciones teóricas:** Usa `ejecutar_capitulo6.py` opciones 3-6
3. **Para mejor visualización:** Integra `overlay_metricas_cap6.py` en `procesador_video.py`
4. **Para entrenar modelo de emergencias:** Usa YOLOv8/11 custom

---

## 🐛 Troubleshooting

**Problema:** "No se detectan vehículos"
- **Solución:** Verificar que YOLO esté instalado (`pip install ultralytics`)

**Problema:** "Velocidad siempre 0"
- **Solución:** Ajustar `pixeles_por_metro` según calibración del video

**Problema:** "Métricas Cap 6 son None"
- **Solución:** Activar `calcular_metricas_cap6=True` en ProcesadorVideo

**Problema:** "Video procesado no se guarda"
- **Solución:** Usar flag `--guardar-video` en el script

---

**Fecha:** 2025-01-17
**Versión:** Sistema Completo Integrado v2.0
**Estado:** ✅ FUNCIONAL Y DOCUMENTADO
