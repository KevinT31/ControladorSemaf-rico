# Guia de Uso del Modo SUMO

## Que es el Modo SUMO

El modo SUMO permite visualizar en tiempo real el trafico de las calles de Lima Centro usando datos de la simulacion SUMO (Simulation of Urban MObility).

## Caracteristicas

### Visualizacion de Calles
- **500 calles** del centro de Lima extraidas de OpenStreetMap
- **Colores dinamicos** segun nivel de congestion:
  - 🟢 **Verde**: Trafico fluido (congestion < 30%)
  - 🟡 **Amarillo**: Trafico moderado (30-60%)
  - 🔴 **Rojo**: Trafico congestionado (> 60%)

### Informacion Detallada
Al hacer clic en una calle, se muestra:
- ID de la calle
- Nombre (si esta disponible)
- Longitud en metros
- Velocidad maxima permitida
- Numero de carriles

### Actualizacion en Tiempo Real
- El estado del trafico se actualiza cada **2 segundos**
- Los colores de las calles cambian dinamicamente segun el flujo vehicular

## Como Usar

### Preparacion (Solo una vez)

1. **Extraer calles de la red SUMO**:
   ```bash
   cd integracion-sumo
   python extraer_calles.py
   ```

   Esto genera el archivo `escenarios/lima-centro/calles.geojson` con las 500 calles principales.

### Usar el Modo SUMO

1. **Iniciar el sistema**:
   ```bash
   python ejecutar.py
   ```

2. **Abrir el navegador**:
   ```
   http://localhost:8000
   ```

3. **Cambiar al modo SUMO**:
   - En el selector superior derecho, selecciona **🎯 SUMO**
   - El mapa cargara automaticamente las calles de Lima Centro

4. **Ver el trafico en tiempo real**:
   - Las calles se mostraran con colores segun el nivel de congestion
   - Haz clic en cualquier calle para ver detalles
   - Los colores se actualizan cada 2 segundos

### Conectar con SUMO en Vivo

Si tienes SUMO instalado y quieres conectar una simulacion en vivo:

1. **Instalar SUMO**:
   - Descargar desde: https://sumo.dlr.de/docs/Downloads.php
   - Agregar `<SUMO_HOME>/tools` al PYTHONPATH

2. **Instalar dependencias**:
   ```bash
   pip install traci
   ```

3. **Iniciar simulacion SUMO**:
   ```bash
   cd integracion-sumo/escenarios/lima-centro
   sumo-gui -c osm.sumocfg
   ```

4. **Conectar el sistema**:
   - El sistema detectara automaticamente SUMO
   - Los datos de trafico se obtendran de la simulacion en vivo

## Archivos Importantes

```
integracion-sumo/
├── conector_sumo.py              # Conector con SUMO via TraCI
├── extraer_calles.py             # Script para extraer calles
└── escenarios/
    └── lima-centro/
        ├── osm.net.xml           # Red de calles (11 MB)
        ├── osm.sumocfg           # Configuracion de SUMO
        ├── osm.passenger.trips.xml  # Viajes vehiculares
        └── calles.geojson        # Calles en formato GeoJSON (generado)
```

## Metricas Visualizadas

El sistema calcula la **congestion** de cada calle usando:

1. **Velocidad promedio**: Velocidad actual vs velocidad maxima
2. **Ocupacion**: Porcentaje de la calle ocupada por vehiculos

Formula:
```
congestion = (1 - velocidad/vel_max) * 0.6 + ocupacion * 0.4
```

Resultado: Valor entre 0 (fluido) y 1 (congestionado)

## Semaforos en la Red

La red de Lima Centro incluye **25 semaforos**:

- IDs basados en OpenStreetMap
- Control adaptativo disponible
- Integracion con el controlador difuso

Lista de IDs de semaforos:
- `10719952849`
- `2114005516`
- `2489391988`
- `4108194472`
- Y 21 mas...

## Solucion de Problemas

### Error: "Archivo de calles no encontrado"
- **Causa**: No se ha generado el archivo `calles.geojson`
- **Solucion**: Ejecutar `python extraer_calles.py` en la carpeta `integracion-sumo`

### Las calles no se ven en el mapa
- **Causa**: El modo SUMO no esta seleccionado
- **Solucion**: Cambiar a modo SUMO en el selector superior

### Los colores no cambian
- **Causa**: SUMO no esta conectado o no hay simulacion activa
- **Solucion**:
  - Verificar que el modo sea SUMO
  - Si quieres trafico real, conectar con SUMO en vivo

### Error: "TraCI no disponible"
- **Causa**: SUMO no esta instalado o no esta en el PATH
- **Solucion**:
  - Instalar SUMO desde https://sumo.dlr.de/docs/Downloads.php
  - Agregar `<SUMO_HOME>/tools` al PYTHONPATH
  - Ejecutar: `pip install traci`

## Proximos Pasos

Una vez que tengas el modo SUMO funcionando:

1. **Conectar con simulacion real**: Iniciar SUMO y ver trafico en vivo
2. **Activar control adaptativo**: Los semaforos se ajustaran al trafico real
3. **Coordinar olas verdes**: Activar emergencias y ver la ruta en el mapa

## Referencias

- **Documentacion SUMO**: https://sumo.dlr.de/docs/
- **TraCI API**: https://sumo.dlr.de/docs/TraCI.html
- **Leaflet (Mapas)**: https://leafletjs.com/
- **GeoJSON**: https://geojson.org/

---

**Nota**: El archivo `calles.geojson` contiene solo las primeras 500 calles para optimizar el rendimiento. Si necesitas mas, modifica el parametro `limite` en `extraer_calles.py`.
