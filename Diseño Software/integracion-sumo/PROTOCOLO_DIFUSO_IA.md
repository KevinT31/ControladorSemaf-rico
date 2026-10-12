# Protocolo fijado antes de ejecutar las estrategias nuevas

Fecha: 2026-10-11. Red, demanda, horizonte de 700 s, métricas y siete rivales:
los de `REPRODUCIBILIDAD.md` y `difuso_opt`. SUMO 1.24.0.

| Uso | Alta | Media |
|---|---|---|
| Entrenamiento y recolección de series | 101-104 | 101-103 |
| Validación y elección | 201-204 | 201-203 |
| Prueba final, una sola vez tras elegir | 1-30 | 1-10 |

Las series para CNN-LSTM se recolectan con `difuso_fase`, con una serie por
semilla, cruce y fase. Horizonte de predicción: 15 s; ventana: 8 muestras cada
15 s. La optimización del predictor utiliza solo entrenamiento; la parada
temprana usa validación. Se compara su MAE con persistencia en validación.

Configuraciones candidatas, definidas antes de medir resultados:

1. `difuso_fase`: controlador de fase con Mamdani y gap-out, parámetros por
   defecto del módulo, sin predictor.
2. `difuso_ia`: mismo controlador con predictor en modo `guardia`, que puede
   vetar el salto de una fase vacía si se prevé cola; parámetros por defecto.

Se comparan en validación por el objetivo J del protocolo existente, usando
las mismas réplicas de `fijo` para el denominador. No se ajustan parámetros
tras ver prueba. Si el predictor no supera persistencia en MAE de validación,
se reporta la ablación IA, pero no se afirma beneficio predictivo. Se informa
la comparación de ambas estrategias contra las siete previas, con t pareada
y Holm, Friedman y Wilcoxon, usando `analizar_resultados.py`.

Una réplica `fijo` de alta, semilla 1, se verificó con SUMO 1.24.0 antes de
las campañas: todas las métricas coincidieron exactamente con
`resultados/multibaseline_ALTA30.json`. Las entradas permanecen sin cambios.

## Incidencia de validación, antes de consultar prueba

La configuración IA predeterminada heredada del PR produjo cero inferencias
en las siete réplicas de validación: la compuerta de densidad cerró siempre.
Se registra esa configuración como resultado nulo. Para medir si el predictor
puede influir, se añade una ablación exploratoria con compuertas abiertas
(`resultados/params_ia_abierta.json`), sin alterar el resto de la política.
La decisión para prueba se tomará exclusivamente con la validación de esa
ablación y `difuso_fase`. Esta enmienda se hizo después de ver validación;
por ello las conclusiones sobre IA se etiquetarán exploratorias.

## Selección cerrada antes de ejecutar prueba

El J medio de validación (cuatro semillas altas y tres medias) fue 0.80782
para `difuso_fase` y 0.82776 para la IA con compuerta abierta. Se selecciona
`difuso_fase` como propuesta principal. La IA abierta se ejecutará una vez
en prueba como ablación exploratoria fijada en este punto, para mostrar el
efecto real del predictor; no se modificarán parámetros a partir de prueba.
El predictor de esta implementación predice cola normalizada por fase, usada
como indicador anticipado de congestión, y no el ICV numérico del núcleo;
esta desviación de la línea A original se declara como limitación.

## Corrección de seguridad antes de la campaña final

La revisión encontró que varias renovaciones de una misma fase podían sumar
más de 120 s de verde continuo. Se corrigió el contador continuo y se
repitieron recolección, entrenamiento y validación antes de ejecutar prueba.
Con el código final, J de validación fue 0.80710 para `difuso_fase` y 0.82588
para IA abierta. El mayor verde continuo observado en desarrollo fue 119 s.
La selección principal y la ablación se mantienen.

Una inspección adicional de los 25 programas semafóricos de la red detectó
varios sin fase explícita de todo rojo. Antes de completar prueba se corrigió
la transición para insertar 2 s de despeje sintético tras el ámbar cuando
falta; las corridas parciales anteriores se descartaron. Se repetirán
desarrollo, entrenamiento y validación con esta versión definitiva.

## Versión definitiva y regla de selección (antes de ejecutar prueba)

Se repitieron, con el código definitivo (despeje sintético de 2 s cuando el
programa no define todo rojo y contador de verde continuo corregido), la
recolección de series en semillas de entrenamiento y validación, el
entrenamiento del predictor y la validación. En las 14 réplicas de desarrollo
y validación no hubo errores en el lazo de control, el mayor verde continuo fue
de 119 s y ninguna transición omitió ámbar ni despeje.

Predictor: MAE de validación 0,0211 frente a 0,0228 de persistencia (cola
normalizada); MSE 0,00157 frente a 0,00296.

J medio de validación (4 semillas altas y 3 medias, mismo denominador `fijo`):
`difuso_fase` 0,8273; IA con compuertas abiertas 0,8246; IA con parámetros por
defecto 0 inferencias (compuerta cerrada, resultado nulo). La diferencia entre
`difuso_fase` y la IA abierta es de 0,0027, con la IA mejor en 4 de las 7
réplicas: no es distinguible del ruido.

Regla fijada ahora, antes de consultar prueba: la IA se considera superior
solo si reduce el J de validación en más de 0,01 frente a `difuso_fase` y
supera a persistencia; si no, la propuesta principal es `difuso_fase` por ser
más simple, y la IA se reporta como ablación exploratoria. Con estos datos la
propuesta principal es `difuso_fase`. Ambas estrategias se ejecutan una sola
vez en prueba (semillas 1-30 en demanda alta y 1-10 en media), sin modificar
parámetros a partir de esos resultados. Esta regla se escribió después de ver
la validación definitiva, por lo que las conclusiones sobre la IA siguen
siendo exploratorias.

## Resultados de prueba (ejecutados una sola vez, sin ajustes posteriores)

Archivos: `resultados/prueba_difuso_ALTA30.json`, `prueba_difuso_MEDIA10.json`
(solo las dos estrategias nuevas) y `experimento_ALTA30.json`,
`experimento_MEDIA10.json` (las nueve estrategias, unidas con las siete
archivadas); análisis en `analisis_experimento_*.json`. Todas las réplicas
terminaron sin errores en el lazo de control; el mayor verde continuo fue de
119 s y no hubo fallos de sensor. Latencia del predictor, p95: 2,1 ms en alta.

Demanda alta, 30 semillas (media; D_stop en s/veh, viaje en s):

| Estrategia | D_stop | Tiempo de viaje | Throughput |
|---|---|---|---|
| Plan fijo | 323,7 | 211,0 | 734,1 |
| Actuado | 222,7 | 202,6 | 852,7 |
| Max-Pressure | 234,8 | 190,8 | 836,6 |
| `difuso_fase` (principal) | 257,8 | 187,8 | 802,1 |
| `difuso_ia` (ablación) | 259,5 | 188,3 | 798,3 |

`difuso_fase` frente al plan fijo: D_stop -20,4 %, viaje -11,0 %, throughput
+9,3 %, a favor en 30 de 30 semillas, todos significativos tras Holm. Frente a
las demás estrategias, es el de menor tiempo de viaje (también frente a
Max-Pressure, p de Holm 8e-6) y el tercero en D_stop, tras el actuado y
Max-Pressure. En demanda media (10 semillas): D_stop 154,0 frente a 220,2 del
plan fijo (-30,1 %), viaje 184,9 (segundo, tras Max-Pressure con 177,5).

Ablación del predictor (`difuso_ia` frente a `difuso_fase`): en demanda alta
la IA no mejora (D_stop +0,7 % peor, 11 de 30 semillas a favor, no
significativo); en demanda media, 8 de 10 semillas a favor, tampoco
significativo tras Holm. El beneficio proviene de la estructura del
controlador (selección acíclica, gap-out y duración difusa) y no del
predictor. Conclusión sobre la IA: sin efecto demostrable; exploratoria.

Limitaciones: `difuso_fase` incorpora mecanismos de tipo actuado (salto de
fases vacías y gap-out) además de la duración difusa; todas las estrategias
reciben observación ideal por TraCI; el predictor estima cola normalizada por
fase, no el ICV numérico; demanda sintética sin aforos de campo. El diseño del
controlador de fase se iteró con semillas de desarrollo y validación; las de
prueba se ejecutaron una sola vez.

## Fase 2: calibración del controlador de fase (registrada antes de ejecutarla)

Objetivo: comprobar si una calibración sistemática de `difuso_fase`, y
después una variante con predictor, logra una mejora más contundente. Las
semillas de prueba ya se usaron una vez para `difuso_fase` por defecto; en esta
fase solo se usan entrenamiento y validación, y la configuración elegida se
ejecutará en prueba una única vez. Se declarará que el conjunto de prueba se
consultó dos veces en total (configuración por defecto y configuración
calibrada).

1. Búsqueda sin IA (`calibrar_fase.py`): 40 candidatos aleatorios y 20
   perturbaciones del mejor sobre `seleccion` (rotación o presión), `w_out`,
   `t_base`, `t_verde_max`, `gap_umbral_s`, `gap_considera_mov`, `t_starve`,
   `umbral_skip`, `w_mov` y `k_ext_cola`. El verde mínimo (10 s), el máximo de
   seguridad (120 s), el ámbar y el despeje no son calibrables. Objetivo J
   (el mismo del protocolo), en entrenamiento (101-104 / 101-103); de los tres
   mejores se elige el de menor J en validación (201-204 / 201-203). La
   configuración por defecto se incluye como candidato.
2. Variantes con IA sobre la mejor configuración sin IA: guardia con
   extensión anticipada, guardia con margen de veto 1 y mezcla con beta 0,3 y
   0,5, todas con compuertas abiertas. Se adopta una variante con IA solo si
   reduce el J de validación en más de 0,01 frente a la mejor sin IA.
3. Prueba única de la configuración elegida (y, como ablación, de su variante
   con IA si existe) en semillas 1-30 / 1-10, con las mismas métricas y
   pruebas estadísticas.
4. Robustez, después de la prueba: horizonte de 1800 s (frente a 700 s) en
   demanda alta con semillas 1-10, para las estrategias principales, para
   verificar que la conclusión no depende del transitorio inicial ni de la
   censura de D_stop.

### Resultado de la calibración (fase 2), registrado antes de ejecutar prueba

Sin IA (`resultados/calibracion_fase.json`): J de entrenamiento 0,8381 con los
parámetros por defecto y 0,8200 con el mejor candidato; en validación, 0,8273
frente a 0,8206. Configuración elegida: selección por presión (w_out 0,811),
t_base 33,1 s, t_verde_max 39 s, gap-out a 2,9 s considerando vehículos en
movimiento, t_starve 42,3 s, umbral de demanda 0,53, w_mov 0,88 y extensión
por cola 0,06 s/veh. Mejora en validación: 0,7 puntos de J.

Con IA sobre esa configuración (`resultados/calibracion_fase_ia.json`), J de
validación: guardia con extensión 0,8152; guardia con margen 1 0,8148; mezcla
beta 0,3 0,8139; mezcla beta 0,5 0,8171. La mejor variante mejora 0,0067, por
debajo del margen fijado (0,01): no se adopta la IA. Se ejecuta en prueba como
ablación la variante mezcla beta 0,3. Prueba: semillas 1-30 y 1-10, una vez.

## Métrica adicional sin sesgo de supervivencia (añadida antes de ver sus valores)

El tiempo de viaje medio solo promedia a los vehículos que llegan dentro del
horizonte. En la réplica 1 del plan fijo en demanda alta se insertaron 1860
vehículos y solo 741 llegaron: el promedio puede favorecer a una estrategia
que entrega viajes cortos y retiene los largos. Por eso se añadió
`tiempo_red_por_veh_s` (vehículo-segundos en la red divididos entre vehículos
insertados, que incluye a quienes siguen circulando) junto con los vehículos
que quedan en la red y los que esperan inserción al final. Las métricas
anteriores no cambian (la simulación es determinista; se comprobó en la
réplica 1 del plan fijo). Se re-ejecutan todas las estrategias en las semillas
de prueba solo para obtener esta métrica, y la robustez a 1800 s la incluye.
Si la ventaja en tiempo de viaje no se sostiene con esta métrica, se reportará
así.

## Resultados de la fase 2 y conclusión

Archivos: `completo_ALTA30.json` y `completo_MEDIA10.json` (todas las
estrategias en las semillas de prueba, con la métrica sin sesgo),
`robustez_1800_ALTA10.json` y sus `analisis_*.json`; además
`prueba_fase_cal_*`, `prueba_ia_cal_*` y `experimento2_*`. Ninguna réplica tuvo
errores en el lazo de control; el mayor verde continuo fue de 119 s.

Demanda alta, 700 s, 30 semillas. T_red: tiempo en red por vehículo insertado
(s), incluye a los que no llegan.

| Estrategia | T_red | D_stop | Viaje de los que llegan |
|---|---|---|---|
| Actuado | 232,6 | 222,7 | 202,6 |
| Max-Pressure | 233,0 | 234,8 | 190,8 |
| `difuso_fase` calibrado | 236,4 | 257,7 | 185,9 |
| `difuso_fase` | 237,0 | 257,8 | 187,8 |
| Webster | 244,5 | 280,2 | 218,1 |
| Plan fijo | 249,6 | 323,7 | 211,0 |

Demanda media, 700 s, 10 semillas: T_red 204,5 (actuado), 212,8 (`difuso_fase`
calibrado), 213,5 (`difuso_fase`), 215,1 (Webster), 215,5 (Max-Pressure) y
229,8 (plan fijo).

Robustez, demanda alta, 1800 s, 10 semillas: T_red 490,0 (actuado), 499,9
(Max-Pressure), 500,6 (Webster), 513,6 (`difuso_fase`), 514,8 (calibrado) y
530,7 (plan fijo).

Conclusiones:

1. El controlador de fase supera al plan fijo en todas las métricas, los dos
   niveles de demanda y los dos horizontes, en todas o casi todas las semillas:
   D_stop -20 % y T_red -5 % en alta a 700 s; T_red -3 % a 1800 s.
2. La ventaja en "tiempo de viaje medio" que se observó primero era en buena
   parte sesgo de supervivencia: con T_red el actuado y Max-Pressure son
   mejores en demanda alta (3,8 y 3,4 s menos, 30 de 30 semillas). En demanda
   media el controlador de fase supera a Max-Pressure y a Webster en T_red,
   pero no al actuado. Con saturación sostenida (1800 s) queda cuarto.
3. La calibración aporta poco (-1 % en tiempo de viaje en alta; sin cambio en
   D_stop ni en T_red). El predictor no tiene efecto significativo en ninguna
   de sus variantes.
4. Afirmación defendible: un controlador difuso interpretable con selección de
   fase por demanda y gap-out mejora con claridad al plan fijo y queda cerca de
   las estrategias adaptativas clásicas (a 1,5-2 % del actuado en T_red con
   700 s), sin superarlas.
