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
