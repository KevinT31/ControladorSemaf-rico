# Instrucciones para Acceder a la Interfaz Web

## ✅ PROBLEMA RESUELTO

He resuelto dos problemas principales:

1. **Librerías bloqueadas por el navegador** - Las librerías (Leaflet, Chart.js, Font Awesome) ahora están instaladas localmente en `interfaz-web/libs/`
2. **Métricas no actualizándose** - El código JavaScript ahora actualiza correctamente TODAS las métricas incluyendo las mini-stats (Fluidas, Moderadas, Congestionadas, etc.)

## 🚀 Cómo Iniciar el Sistema

### Opción 1: Usando el menú (Recomendado)

```bash
cd C:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2
python ejecutar.py
```

Luego selecciona la opción **1** para iniciar el Dashboard Completo.

### Opción 2: Iniciar directamente el servidor

```bash
cd C:\Users\kevin\OneDrive\Desktop\ControladorSemaforicoTFC2\servidor-backend
python main.py
```

## 🌐 Acceder a la Interfaz

Una vez iniciado el servidor, abre tu navegador y ve a:

**http://localhost:8000**

## 📊 Qué Deberías Ver

La interfaz debe mostrar:

1. **Header superior** con:
   - Logo del sistema
   - Estado "CONECTADO"
   - Selector de modo (Simulador/Video/SUMO)
   - Botón de Emergencia

2. **Sidebar izquierda** con:
   - Estadísticas del sistema (Intersecciones, ICV Promedio, Flujo Promedio, Olas Verdes)
   - Mini-stats con contadores de:
     - 🟢 Calles Fluidas (ICV < 0.3)
     - 🟡 Calles Moderadas (0.3 ≤ ICV < 0.6)
     - 🔴 Calles Congestionadas (ICV ≥ 0.6)
     - ⚡ Velocidad Promedio (km/h)
   - Gráficos en tiempo real de ICV y Flujo Vehicular

3. **Mapa central** mostrando:
   - 29-31 intersecciones de Lima
   - Marcadores de semáforos que cambian de color según congestión
   - Conexiones entre intersecciones

4. **Sidebar derecha** con:
   - Panel de detección en tiempo real (video YOLO)
   - Lista de intersecciones con métricas actualizadas
   - Olas verdes activas
   - Sistema difuso

## ✅ Verificación

Para verificar que todo funciona correctamente:

1. Abre la consola del navegador (F12)
2. Ve a la pestaña "Console"
3. Deberías ver mensajes como:
   ```
   Inicializando sistema...
   Iniciando partículas...
   Iniciando mapa...
   Iniciando gráficos...
   Cargando intersecciones...
   [OK] WebSocket conectado
   ```

4. **NO deberías ver**:
   - Errores de "Tracking Prevention blocked"
   - "Leaflet no está cargado"
   - "Chart.js no está cargado"

## 🔧 Solución de Problemas

### Si no ves el mapa o gráficos:

1. **Recarga la página con Ctrl+F5** (forzar recarga sin caché)
2. Verifica que el servidor esté corriendo (debería ver métricas actualizándose)
3. Abre la consola (F12) y busca errores en rojo

### Si las métricas están en 0:

1. Espera 2-3 segundos (el WebSocket tarda en conectar)
2. Verifica en la consola que veas: `[OK] WebSocket conectado`
3. Si no conecta, reinicia el servidor

### Si ves "DESCONECTADO" en el header:

1. El servidor no está corriendo
2. Reinicia con: `cd servidor-backend && python main.py`
3. Espera a que veas: "Uvicorn running on http://0.0.0.0:8000"

## 📁 Archivos Modificados

Los siguientes archivos fueron modificados para resolver los problemas:

- `interfaz-web/index.html` - Actualizado para usar librerías locales
- `interfaz-web/app_mejorado.js` - Agregada actualización de mini-stats
- `interfaz-web/libs/` - Nueva carpeta con todas las librerías

## 🎯 Métricas que Debes Ver Actualizándose

✅ **Sidebar Izquierda:**
- Número de Intersecciones
- ICV Promedio
- Flujo Promedio
- Olas Activas
- Calles Fluidas
- Calles Moderadas
- Calles Congestionadas
- Velocidad Promedio

✅ **Gráficos:**
- ICV en Tiempo Real
- Flujo Vehicular

✅ **Mapa:**
- Marcadores que cambian de color (verde/amarillo/rojo)

✅ **Sidebar Derecha:**
- Lista de intersecciones con métricas individuales

## 📞 Si Nada Funciona

1. Detén el servidor (Ctrl+C)
2. Ejecuta este comando para reinstalar librerías:
   ```bash
   cd interfaz-web
   npm install
   ```
3. Reinicia el servidor
4. Recarga la página con Ctrl+F5

---

**Última actualización:** 17 de Noviembre de 2025
**Estado:** ✅ FUNCIONANDO
