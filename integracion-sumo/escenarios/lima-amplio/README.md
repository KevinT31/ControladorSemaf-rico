# 📍 Mapa Amplio de Lima para SUMO

Este directorio contiene los archivos del mapa amplio de Lima.

## 📂 Archivos necesarios:

- `lima_amplio.osm` - Mapa descargado de OpenStreetMap
- `lima_amplio.net.xml` - Red de calles convertida para SUMO
- `lima_amplio.rou.xml` - Rutas de tráfico vehicular
- `lima_amplio.sumocfg` - Configuración de SUMO ✅ (YA CREADO)
- `calles.geojson` - Calles para visualización web

## 🗺️ Área cubierta:

**Coordenadas bbox:**
```
Oeste (Left):   -77.0700
Sur (Bottom):   -12.1200
Este (Right):   -77.0100
Norte (Top):    -12.0400
```

**Distritos incluidos:**
- Centro de Lima (Cercado)
- Miraflores
- San Isidro
- Lince
- Jesús María
- Magdalena del Mar
- Pueblo Libre (parcial)
- Surquillo (parcial)

## 🚀 Cómo completar la instalación:

### Opción A: Descarga manual (MÁS FÁCIL)

1. **Ir a:** https://www.openstreetmap.org/export

2. **Ingresar coordenadas:**
   - Left: -77.0700
   - Bottom: -12.1200
   - Right: -77.0100
   - Top: -12.0400

3. **Hacer clic en "Export"** (si dice área muy grande, usar Overpass API)

4. **Guardar como:** `lima_amplio.osm` en este directorio

5. **Convertir a red SUMO:**
   ```powershell
   netconvert --osm-files lima_amplio.osm --output-file lima_amplio.net.xml --geometry.remove --ramps.guess --junctions.join --tls.guess-signals --tls.default-type actuated --remove-edges.isolated --keep-edges.by-vclass passenger
   ```

6. **Generar tráfico:**
   ```powershell
   python "C:\Program Files\Eclipse\Sumo\tools\randomTrips.py" -n lima_amplio.net.xml -o lima_amplio.rou.xml -e 3600 -p 2.4 --fringe-factor 5
   ```

7. **Probar:**
   ```powershell
   sumo-gui -c lima_amplio.sumocfg
   ```

### Opción B: Link directo

Si el área es muy grande para exportar directamente:

```
https://overpass-api.de/api/map?bbox=-77.0700,-12.1200,-77.0100,-12.0400
```

Esto descarga el OSM directamente, luego sigue los pasos 5-7.

## 📊 Estadísticas esperadas:

- **Calles (edges):** ~1000-2000
- **Intersecciones:** ~500-800
- **Semáforos:** ~50-100
- **Tamaño archivo .net.xml:** ~15-25 MB

## ✅ Verificar instalación:

```powershell
# Ver si existen los archivos:
ls lima_amplio.*

# Deberías ver:
# - lima_amplio.osm (si descargaste)
# - lima_amplio.net.xml (después de netconvert)
# - lima_amplio.rou.xml (después de randomTrips)
# - lima_amplio.sumocfg (ya existe)
```

## 🌐 Integración con sistema web:

El backend ya está configurado para detectar automáticamente este mapa.

Una vez que tengas `lima_amplio.net.xml`, ejecuta:

```powershell
cd ..\..\
python extraer_calles.py
```

(Primero edita `extraer_calles.py` para que apunte a `lima-amplio`)

## 📝 Notas:

- El área cubre aproximadamente 6 km x 8 km
- Es ~3 veces más grande que el mapa actual de lima-centro
- Recomendado: empezar con área más pequeña si tu PC es lento

---

**Estado:** ⚠️ Pendiente descarga de archivos OSM y conversión
