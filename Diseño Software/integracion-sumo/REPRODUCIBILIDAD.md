# Reproducibilidad de la campaña SUMO

Este documento explica cómo repetir, desde una copia limpia del repositorio, la
campaña que compara el plan fijo, el control actuado de SUMO, Webster, Webster
modificado, Max-Pressure y el controlador difuso (con los parámetros del
Capítulo 6 y con los parámetros calibrados).

Todas las entradas de simulación están versionadas; no hace falta descargar
mapas ni generar rutas.

## Entradas versionadas (`escenarios/lima-centro/`)

| Archivo | Contenido | SHA-256 |
|---|---|---|
| `lima_centro.net.xml.gz` | Red vial generada con `netconvert` desde OpenStreetMap | `58db74c0a3d4157b40c7256e9f3ffbcb39b14555916a03d2d50757c1e29e8890` |
| `osm_bbox.osm.xml.gz` | Extracto de OpenStreetMap del que se generó la red | `c45fcfccdc7b46a711373e7cba3ce39ef62f403be42fc6fa00d269a2960e6ca3` |
| `lima_centro_alta.rou.xml.gz` | Demanda alta (densidad de inserción 60) | `5af327ae051486322acbb740a691b33f35ad5e95a20ed4e1429539e4529082e2` |
| `lima_centro_media.rou.xml.gz` | Demanda media (densidad de inserción 24) | `aac2d1d5e576a762434a2067ddf23638dc780a347a9b2346226c7f055017635e` |
| `comparacion.sumocfg` | Configuración, demanda alta | `8e3df460d2744750da0a6f6cdab6659f7d8252177d88086779d85d7792c90dda` |
| `comparacion_media.sumocfg` | Configuración, demanda media | `0375a98151751faa2cbe909da44ef3b231a46f8baa853b0744df5d35c2c6d98c` |

Verificación: `sha256sum` (Linux/macOS/Git Bash) o `Get-FileHash -Algorithm SHA256`
(PowerShell) deben dar los valores de la tabla. Cada JSON de resultados también
guarda las huellas de las entradas con las que se generó (`huellas_sha256`).

Los datos del mapa son © colaboradores de OpenStreetMap, disponibles bajo la
licencia ODbL (<https://www.openstreetmap.org/copyright>).

Las rutas se generaron con `escenarios/lima-centro/generar_demanda.py`
(`randomTrips.py`, semilla 42). Ese script permite regenerarlas, pero basta con
usar los archivos versionados.

## Entorno

- SUMO **1.24.0** (la campaña se ejecutó con `Eclipse SUMO sumo Version 1.24.0`).
  Defina `SUMO_HOME` y deje `sumo` en el `PATH`.
- Python 3.12 y las dependencias de `requirements.txt` (`numpy`, `scipy`,
  `sumolib`, `traci`). Los resultados archivados se obtuvieron con `sumolib`
  1.24.0 y `traci` 1.19.0.
- La campaña usa el cliente TraCI por sockets. Cada simulación de demanda alta
  tarda del orden de un minuto en un equipo de escritorio.

## Repetir la campaña

Desde `Diseño Software/integracion-sumo/`:

```powershell
# Demanda alta: 6 líneas base y controladores difusos, semillas 1-30
python campana_paralela.py --cfg escenarios/lima-centro/comparacion.sumocfg `
    --semillas 1-30 --workers 8 --salida resultados/multibaseline_ALTA30.json

# Controlador difuso con los parámetros calibrados
python campana_paralela.py --cfg escenarios/lima-centro/comparacion.sumocfg `
    --semillas 1-30 --estrategias difuso_opt --workers 8 `
    --anexar resultados/multibaseline_ALTA30.json --salida resultados/multibaseline_ALTA30.json

# Demanda media, semillas 1-10 (mismos dos pasos con comparacion_media.sumocfg)

# Análisis estadístico
python analizar_resultados.py resultados/multibaseline_ALTA30.json --salida resultados/analisis_ALTA30.json
```

`--semillas` admite rangos (`1-30`) o listas (`1,5,9`). Con las mismas entradas
y la misma versión de SUMO, cada par estrategia-semilla produce exactamente el
mismo resultado.

## Calibración del controlador difuso

`calibrar_difuso.py` ajusta los vértices de las funciones de pertenencia de ICV
y PI, el suavizado `alpha` y la agresividad `gamma`. Las 12 reglas no se
modifican. El protocolo usa semillas disjuntas:

| Fase | Semillas (demanda alta / media) |
|---|---|
| Entrenamiento | 101-104 / 101-103 |
| Validación | 201-204 / 201-203 |
| Prueba (resultados reportados) | 1-30 / 1-10 |

La función objetivo (menor es mejor) es
`J = 0.5 * T_viaje / T_viaje_fijo + 0.5 * D_stop / D_stop_fijo`, promediada sobre
los pares escenario-semilla. Se evalúan 40 candidatos aleatorios y 20
perturbaciones del mejor; entre los 3 mejores del entrenamiento se elige el de
menor `J` en validación. El resultado queda en
`resultados/parametros_difuso_calibrados.json`, que incluye el registro completo
de candidatos.

```powershell
python calibrar_difuso.py --workers 8 --salida resultados/parametros_difuso_calibrados.json
```

## Limitaciones conocidas

- La demanda es sintética (`randomTrips`) y no está calibrada con aforos de
  campo; los niveles "media" y "alta" son relativos a esta red.
- Todas las estrategias reciben observación ideal de los carriles vía TraCI.
- `demora_media_s` (denominada `D_stop` en la tesis) es la carga acumulada de
  detención dividida entre los vehículos que completan su viaje; incluye
  vehículos que siguen en la red al terminar el horizonte de 700 s.
- Webster y Max-Pressure son reimplementaciones propias de los algoritmos
  publicados, no el código de terceros.
