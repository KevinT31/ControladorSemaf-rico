# 📊 Visualizaciones Interactivas para Tesis

Sistema de dashboards profesionales diseñados específicamente para documentar la tesis de **Control Semafórico Adaptativo Inteligente**.

---

## 🚀 Inicio Rápido

### **Opción 1: Abrir en Navegador (Recomendado)**

```bash
# Desde la raíz del proyecto:
cd visualizaciones-tesis

# Abrir el índice principal:
# - Windows: start index.html
# - Mac: open index.html
# - Linux: xdg-open index.html

# O abrir directamente cualquier visualización específica:
open 01_arquitectura_completa.html
```

### **Opción 2: Servidor Local (Para desarrollo)**

```bash
# Con Python 3:
python3 -m http.server 8080

# Luego abrir en navegador:
# http://localhost:8080
```

---

## 📸 Cómo Capturar para Tesis

### **Método 1: Captura de Pantalla Directa**

1. Abrir visualización en navegador
2. Presionar **F11** para pantalla completa
3. Ajustar zoom al **100%** (Ctrl+0)
4. Capturar con tu herramienta favorita:
   - **Windows:** Win+Shift+S (Snipping Tool)
   - **Mac:** Cmd+Shift+4
   - **Linux:** Print Screen

### **Método 2: Exportar a PDF (Alta Calidad)**

1. Abrir visualización
2. **Ctrl+P** (Imprimir)
3. Seleccionar "Guardar como PDF"
4. Configurar:
   - Orientación: Horizontal
   - Márgenes: Ninguno
   - Escala: 100%
5. Guardar

### **Método 3: Screenshot de Página Completa**

Instalar extensión del navegador:
- Chrome/Edge: "Full Page Screen Capture"
- Firefox: "Nimbus Screenshot"

Resultado: Imagen PNG en resolución completa.

---

## 📁 Contenido de Visualizaciones

### **Categoría 1: Arquitectura General** (Capítulo 4)

| # | Archivo | Descripción | Dimensiones |
|---|---------|-------------|-------------|
| 1 | `01_arquitectura_completa.html` | Diagrama 3 capas: Cloud/4G/Edge | 1200×800 |
| 2 | `02_arquitectura_edge_cloud.html` | Comparación procesamiento Edge vs Cloud | 1400×900 |

**Usar en:**
- Capítulo 4: Diseño del Sistema
- Sección 4.2: Arquitectura Propuesta
- Figura 4.1, 4.2

---

### **Categoría 2: Flujos de Procesamiento** (Capítulo 5)

| # | Archivo | Descripción | Dimensiones |
|---|---------|-------------|-------------|
| 3 | `03_flujo_control_local.html` | Diagrama flujo ciclo 5s (Edge) | 1000×1600 |
| 4 | `04_flujo_azure.html` | Pipeline Azure: IoT Hub → ML → Comandos | 1600×800 |
| 5 | `05_sistema_difuso_interactivo.html` | 27 reglas difusas + sliders interactivos | 1200×1000 |

**Usar en:**
- Capítulo 5: Implementación
- Sección 5.3: Algoritmo de Control
- Figuras 5.1-5.5

---

### **Categoría 3: Métricas del Capítulo 6**

| # | Archivo | Descripción | Dimensiones |
|---|---------|-------------|-------------|
| 6 | `06_calculo_icv_visual.html` | Fórmula ICV paso a paso con animación | 1200×900 |
| 7 | `07_funciones_pertenencia.html` | Gráficos funciones membership (ICV, PI, EV) | 1400×800 |
| 8 | `08_olas_verdes.html` | Algoritmo A* + sincronización semáforos | 1300×900 |

**Usar en:**
- Capítulo 6: Metodología
- Sección 6.2.3: Índice de Congestión Vehicular
- Sección 6.3.5: Olas Verdes Dinámicas
- Sección 6.3.6: Controlador Difuso
- Figuras 6.5-6.12

---

### **Categoría 4: Resultados Experimentales** (Capítulo 7)

| # | Archivo | Descripción | Dimensiones |
|---|---------|-------------|-------------|
| 9 | `09_comparacion_controladores.html` | Gráficos tiempo fijo vs adaptativo | 1400×900 |
| 10 | `10_dashboard_tiempo_real.html` | Dashboard simulado del sistema funcionando | 1600×900 |

**Usar en:**
- Capítulo 7: Resultados y Discusión
- Sección 7.2: Comparación de Controladores
- Sección 7.3: Validación en Simulación
- Figuras 7.1-7.8

---

## 🎨 Personalización

Todas las visualizaciones son HTML/CSS/SVG puro, sin dependencias externas.

### **Cambiar Colores**

Editar variables CSS al inicio de cada archivo:

```css
/* Colores principales */
--azure-blue: #0078D4;
--success-green: #10B981;
--warning-orange: #F97316;
--danger-red: #EF4444;
```

### **Ajustar Dimensiones**

Modificar en la etiqueta `.container`:

```css
.container {
    width: 1200px;  /* Cambiar aquí */
    height: 800px;  /* Y aquí */
}
```

### **Cambiar Datos**

Buscar la sección de datos en JavaScript:

```javascript
// Ejemplo en 05_sistema_difuso_interactivo.html
const datos = {
    icv: 0.65,  // Cambiar valor
    pi: 0.45,
    ev: 0.0
};
```

---

## 🖨️ Configuración de Impresión

Para obtener PDFs de máxima calidad:

```css
@media print {
    body {
        width: 297mm;  /* A4 horizontal */
        height: 210mm;
    }

    .container {
        box-shadow: none;
        page-break-inside: avoid;
    }
}
```

Ya incluido en todos los archivos.

---

## 🔧 Solución de Problemas

### **Problema: Los gráficos se ven pixelados**

**Solución:**
1. Abrir en Chrome/Edge (mejor renderizado SVG)
2. Zoom al 100% exacto
3. Usar "Imprimir → PDF" en lugar de captura de pantalla

---

### **Problema: Las animaciones no funcionan**

**Solución:**
1. Asegurar que JavaScript está habilitado
2. Abrir en navegador moderno (Chrome 90+, Firefox 88+, Edge 90+)
3. No usar "Vista de Lectura" o modo simplificado

---

### **Problema: Colores diferentes a los esperados**

**Solución:**
1. Verificar que el navegador no tiene extensiones de "Dark Mode"
2. Desactivar filtros de luz azul del sistema operativo
3. Usar monitor calibrado para capturas finales

---

## 📊 Integración con LaTeX

### **Incluir figuras en tesis:**

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{imagenes/01_arquitectura_completa.pdf}
    \caption{Arquitectura completa del sistema de control adaptativo}
    \label{fig:arquitectura-completa}
\end{figure}
```

### **Referencia en texto:**

```latex
Como se observa en la Figura~\ref{fig:arquitectura-completa},
el sistema implementa una arquitectura híbrida Edge-Cloud...
```

---

## 📈 Métricas de las Visualizaciones

| Métrica | Valor |
|---------|-------|
| Total de visualizaciones | 10 |
| Líneas de código (total) | ~5,000 |
| Tecnologías | HTML5, CSS3, SVG, Vanilla JS |
| Compatibilidad | Chrome 90+, Firefox 88+, Edge 90+ |
| Tamaño total | <500 KB |
| Dependencias externas | 0 (standalone) |
| Tiempo de carga | <100ms |

---

## 🎯 Checklist de Uso para Tesis

### **Antes de capturar:**

- [ ] Navegador en pantalla completa (F11)
- [ ] Zoom al 100% (Ctrl+0)
- [ ] Extensiones de Dark Mode desactivadas
- [ ] Monitor en brillo estándar
- [ ] JavaScript habilitado

### **Al capturar:**

- [ ] Formato PNG o PDF (no JPEG)
- [ ] Resolución mínima: 1200×800
- [ ] Fondo blanco sin transparencias
- [ ] Leyendas y etiquetas legibles

### **Después de capturar:**

- [ ] Verificar calidad de imagen
- [ ] Renombrar archivo con nombre descriptivo
- [ ] Guardar en carpeta `imagenes/` de tesis
- [ ] Actualizar caption en documento LaTeX
- [ ] Verificar referencia cruzada funcionando

---

## 🚀 Ejemplos de Uso

### **Ejemplo 1: Explicar arquitectura en presentación**

```bash
# Abrir visualización 1
open 01_arquitectura_completa.html

# En presentación PowerPoint/Beamer:
# - Capturar como PDF
# - Insertar como imagen de fondo
# - Animar aparición de componentes por capa
```

### **Ejemplo 2: Mostrar sistema difuso en defensa**

```bash
# Abrir visualización 5 (interactiva)
open 05_sistema_difuso_interactivo.html

# Durante defensa:
# - Proyectar en pantalla
# - Ajustar sliders en vivo
# - Mostrar activación de reglas en tiempo real
```

### **Ejemplo 3: Comparar resultados en documento**

```bash
# Abrir visualización 9
open 09_comparacion_controladores.html

# Capturar y usar en:
# Capítulo 7, Tabla 7.1
# Figura 7.3: "Comparación de métricas..."
```

---

## 📚 Recursos Adicionales

### **Herramientas Recomendadas:**

- **Captura:** ShareX (Windows), Skitch (Mac), Flameshot (Linux)
- **Edición:** Inkscape (vectorial), GIMP (raster)
- **Conversión:** ImageMagick, Ghostscript
- **Compresión:** TinyPNG, OptiPNG

### **Documentación de Referencia:**

- MDN Web Docs (HTML/CSS/SVG): https://developer.mozilla.org
- Can I Use (Compatibilidad): https://caniuse.com
- SVG Tutorial: https://www.w3.org/Graphics/SVG/

---

## 💡 Tips Profesionales

### **1. Consistencia Visual**

- Usar siempre la misma paleta de colores
- Mantener tamaños de fuente uniformes
- Alinear elementos con grid invisible

### **2. Accesibilidad**

- Contrasteadecuado (mínimo 4.5:1)
- Etiquetas descriptivas
- No depender solo del color para transmitir información

### **3. Escalabilidad**

- Usar SVG en lugar de PNG cuando sea posible
- Tamaños relativos (%, em) en lugar de absolutos (px)
- Probar en múltiples resoluciones

---

## 🎓 Créditos

**Desarrollado para:**
- Tesis de Ingeniería Electrónica
- Universidad: [Tu Universidad]
- Año: 2025

**Tecnologías Utilizadas:**
- HTML5, CSS3, SVG 1.1
- JavaScript ES6+
- Sin frameworks ni librerías externas

**Licencia:**
Libre uso para fines académicos y educativos.

---

## 📧 Soporte

Para problemas técnicos o sugerencias:
1. Revisar este README
2. Verificar código fuente (bien comentado)
3. Consultar MDN Web Docs
4. Editar directamente el HTML (sin dependencias)

---

**¡Listo para capturar y usar en tu tesis!** 🎉
