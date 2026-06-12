# 🎮 Escenarios de Simulación SUMO

Esta carpeta contiene los escenarios de simulación para integración con SUMO.

## 📁 Estructura

```
escenarios/
├── lima-centro/              # Red completa del centro de Lima
│   ├── lima_centro.net.xml   # Red de calles
│   ├── lima_centro.rou.xml   # Rutas vehiculares
│   ├── lima_centro.sumocfg   # Configuración
│   └── adicional.xml         # Detectores y outputs
│
└── interseccion-critica/     # Intersección individual
    ├── interseccion.net.xml
    ├── interseccion.rou.xml
    └── interseccion.sumocfg
```

## 🚀 Cómo Usar Tu Propia Simulación de SUMO

### Paso 1: Preparar Archivos

Necesitas 3 archivos mínimos:
1. **Red de calles** (`.net.xml`): Topología de la red vial
2. **Rutas vehiculares** (`.rou.xml`): Demanda de tráfico
3. **Configuración** (`.sumocfg`): Archivo de configuración principal

### Paso 2: Copiar a la Carpeta

Copia tus archivos a `lima-centro/` con los nombres:
- `lima_centro.net.xml`
- `lima_centro.rou.xml`
- `lima_centro.sumocfg`

### Paso 3: Verificar IDs de Semáforos

Abre `lima_centro.net.xml` y busca los IDs de semáforos:

```xml
<tlLogic id="INT-001" type="static" programID="0">
    ...
</tlLogic>
```

Los IDs deben coincidir con los usados en el sistema.

### Paso 4: Ejecutar

```bash
python ejecutar.py
# Selecciona opción 3: Conectar con SUMO
```

## 🛠️ Crear Simulación de Lima desde Cero

### Opción 1: Usando OSM (OpenStreetMap)

1. **Descargar mapa de Lima**:
   - Ir a https://www.openstreetmap.org
   - Buscar "Lima, Perú"
   - Exportar área de interés (Tools → Export)
   - Guardar como `lima.osm`

2. **Convertir a red SUMO**:
```bash
netconvert --osm-files lima.osm \
           --output-file lima_centro.net.xml \
           --geometry.remove \
           --ramps.guess \
           --junctions.join \
           --tls.guess-signals
```

3. **Generar tráfico aleatorio**:
```bash
randomTrips.py -n lima_centro.net.xml \
               -r lima_centro.rou.xml \
               -e 3600 \
               -p 2
```

### Opción 2: Usando NETEDIT (GUI)

1. Abrir NETEDIT:
```bash
netedit
```

2. Crear red manualmente:
   - Mode → Network
   - Agregar nodos (intersecciones)
   - Conectar con edges (calles)
   - Agregar semáforos

3. Guardar como `lima_centro.net.xml`

4. Crear rutas con Modo "Demand"

### Opción 3: Importar desde Google Maps

Usar plugin de SUMO para importar desde Google Maps.

## 📝 Ejemplo de Configuración (.sumocfg)

```xml
<configuration>
    <input>
        <net-file value="lima_centro.net.xml"/>
        <route-files value="lima_centro.rou.xml"/>
    </input>

    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1"/>
    </time>

    <processing>
        <time-to-teleport value="-1"/>
    </processing>
</configuration>
```

## 🎯 Intersecciones de Lima Recomendadas

Para tu simulación, considera estas intersecciones críticas:

1. **Av. Arequipa - Av. Angamos** (-12.1063, -77.0315)
2. **Av. Javier Prado - Av. República de Panamá** (-12.1010, -77.0315)
3. **Av. La Marina - Av. Faucett** (-12.0545, -77.0848)
4. **Av. Universitaria - Av. Venezuela** (-12.0585, -77.0843)

## 🔍 Verificar Simulación

Antes de integrar, prueba tu simulación:

```bash
sumo-gui -c lima_centro.sumocfg
```

Verifica:
- ✅ Semáforos funcionan
- ✅ Vehículos circulan correctamente
- ✅ No hay errores en consola

## 🐛 Solución de Problemas

### Error: "No route found"
- Verificar que hay rutas en `.rou.xml`
- Asegurar que edges en rutas existen en `.net.xml`

### Error: "Traffic light not found"
- Verificar IDs en el código del sistema
- Listar semáforos con:
```python
import traci
traci.start(["sumo", "-c", "lima_centro.sumocfg"])
print(traci.trafficlight.getIDList())
```

### Simulación muy lenta
- Reducir número de vehículos en `.rou.xml`
- Usar `sumo` (sin GUI) en lugar de `sumo-gui`

## 📚 Recursos Adicionales

- **Documentación SUMO**: https://sumo.dlr.de/docs/
- **Tutoriales**: https://sumo.dlr.de/docs/Tutorials.html
- **Ejemplos**: `<SUMO_HOME>/docs/examples/`

## 💡 Tips

1. Empieza con una intersección simple antes de hacer toda la red
2. Usa `--tls.guess-signals` para detectar semáforos automáticamente
3. Calibra el tráfico con datos reales de Lima si es posible
4. Exporta outputs de SUMO para análisis posterior

---

**¿Necesitas ayuda?** Revisa `integracion-sumo/guia-integracion.md`
