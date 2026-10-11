# Auditoría del repositorio — NSB v2.1

Fecha: 2026-07-05 · Alcance: núcleo/SUMO, backend/comms/seguridad y
visión/datos/experimentos.
Clasificación de evidencia según spec §50: todo lo listado aquí es **OBSERVADO**
directamente en el repositorio, salvo indicación.

## 1. Estructura relevante

```
C:\ControladorSemafrico\
├── server.js + package.json + public/ + tools/   # "OverLeaf Local": editor LaTeX
│                                                  # de la tesis. NO es el backend.
├── workspace/                                     # fuentes LaTeX de la tesis
├── (especificación local NSB v2.1, no versionada)
├── docs/nsb_v2_1/                                 # (NUEVO) documentación NSB
└── Diseño Software\                               # ★ PROYECTO REAL
    ├── ejecutar.py                # menú principal (entry point integral)
    ├── nucleo/                    # núcleo científico (Python puro, solo numpy)
    ├── integracion-sumo/          # TraCI/libsumo + escenarios + resultados
    ├── servidor-backend/          # FastAPI + SQLite + auth JWT/RBAC
    ├── interfaz-web/              # frontend vanilla JS (Leaflet, Chart.js)
    ├── vision_computadora/        # YOLO + tracking + métricas de video
    ├── simulador_trafico/         # simulador determinista sin SUMO
    ├── base-datos/                # schema.sql (7 tablas)
    ├── datos/                     # modelos (vacío), videos (vacío), resultados
    ├── Calculo-Matlab/            # análisis offline espejo (tesis)
    ├── requirements.txt           # único manifiesto de dependencias
    └── nsb/ + tests/ + config/    # (NUEVO) extensión NSB v2.1
```

## 2. Entry points

| Comando | Qué hace |
|---|---|
| `python ejecutar.py` | Menú: dashboard, video, SUMO, comparación, pruebas |
| `python servidor-backend/main.py` | Backend FastAPI puerto 8000 |
| `python servidor-backend/main_capitulo6.py` | Backend alterno con lazo Cap. 6 |
| `python integracion-sumo/comparacion_multibaseline.py --seeds 10 --pasos 700 --intervalo 25` | ★ Resultados de tesis (6 estrategias) |
| `python integracion-sumo/comparacion_sumo.py` | Comparación fijo vs adaptativo |
| `python vision_computadora/procesador_modular.py --modo ... --video ...` | Pipeline de visión offline |

## 3. Núcleo científico canónico (fuente de verdad)

| Concepto | Archivo canónico | Símbolos clave |
|---|---|---|
| ICV + PI | `nucleo/indice_congestion.py` | `CalculadorICV`, `ParametrosInterseccion`, `calcular()`, `calcular_icv_cap6()`, `calcular_parametro_intensidad()` |
| Controlador difuso | `nucleo/controlador_difuso_capitulo6.py` | `ControladorDifusoCapitulo6` — Mamdani, 3 entradas (ICV, PI, EV) → ΔT% [−30,+30], 12 reglas (R1-R3 = prioridad EV), `calcular_ajuste_verde()`, `calcular_control_completo()` |
| Seguridad funcional | `nucleo/seguridad_semaforica.py` | `LimitesSeguridad` (frozen: verde 10–120 s, ámbar ≥3 s, todo-rojo ≥2 s, ciclo 20–240 s), `LIMITES`, `CONFIG_SEGURA`, `ValidadorSeguridadSemaforica` (`validar_parametros_control`, `clamp_tiempos`, `verificar_fases_no_conflictivas`, `modo_seguro`, `aplicar_con_seguridad`), instancia `validador_seguridad` |
| Estado local por dirección | `nucleo/estado_local.py` | `EstadoLocalInterseccion` (SC/Vavg/q/k/ICV/PI/EV por N-S-E-O, `actualizar_desde_tracks`, `obtener_paquete_telemetria`) |
| Agregación de red | `nucleo/metricas_red.py` | `AgregadorMetricasRed` (ICV_red = Σ ωi·ICVi) |

**Intervalo de control canónico: 25 s** (paso de simulación 1 s) — confirmado en
`integracion-sumo/resultados/comparacion_multibaseline.json` (metadata:
`pasos=700, intervalo_control=25, semillas=[1..10], limites_verde=[10,120]`).

## 4–7. ICV / PI / EV / difuso — implementaciones y duplicaciones

- ICV: **≥4 variantes** con pesos distintos —
  `indice_congestion.py` (0.35/0.25/0.25/0.15, canónica),
  `estado_local.py:336` (0.30/0.25/0.25/0.20),
  `comparacion_sumo._metricas_instante` (ICV_red 0.5/0.5, métrica de red),
  `controlador_sumo_completo.py:492` (0.4/0.3/0.2/0.1, código muerto).
- PI: **2 fórmulas** — canónica Cap. 6 `Vavg/(SC+δ)` en `indice_congestion.py:303`
  y variante ad-hoc `0.5·frac_mov + 0.5·vel_norm` en `comparacion_sumo._demanda_fase`.
- Difuso: **2 controladores** — `controlador_difuso_capitulo6.py` (canónico, usado
  en resultados) y `controlador_difuso.py` (legacy 2-entradas, solo lo usa
  `conector_sumo.py`).
- EV: reglas R1-R3 del difuso canónico + conteo/tracking en `estado_local.py`
  + detección visual en `vision_computadora/detector_emergencia.py` (modelo
  custom INEXISTENTE; fallback por color declarado "no confiable").

**Decisión NSB**: consumir SOLO `indice_congestion.CalculadorICV` +
`controlador_difuso_capitulo6.ControladorDifusoCapitulo6` +
`seguridad_semaforica.validador_seguridad` vía adaptadores.

## 8. Seguridad existente

- Funcional: `seguridad_semaforica.py` (límites, clamp con trazabilidad, modo
  seguro, no-conflicto NS/EO **binario** — no hay matriz N×N ni FSM temporal).
- Ciberseguridad backend: `servidor-backend/seguridad/` — JWT HS256 propio
  (stdlib, comparación tiempo constante), PBKDF2 200k iteraciones, RBAC 3 roles
  (operador<tecnico<admin), middleware Bearer, validador de comandos (delega en
  `LIMITES` — patrón correcto), auditoría dual BD+archivo.
- Riesgos preexistentes (no bloqueantes, documentados en limitations.md):
  `SECRET_KEY` default commiteada (`config.py:39`), credenciales demo
  hardcodeadas, WebSocket `/ws` sin auth, sin rate limiting en login, CORS laxo,
  backend HTTP sin TLS en `0.0.0.0`.

## 9. CNN-LSTM

**NO EXISTE**: 0 código (grep de CNN/LSTM/keras/tensorflow/nn.Module = 0 hits
fuera de docs), 0 modelos (`datos/modelos-entrenados/` = solo `.gitkeep`).
El único deep learning del repo es YOLOv8 (ultralytics/PyTorch) para detección
visual. → NSB implementa solo la interfaz `PredictorBackend` + `DisabledPredictor`.

## 10. Pipeline de visión

- `procesador_video.py`: `ProcesadorVideo` — YOLO con auto-upgrade yolo11→yolov8,
  clases COCO [2,3,5,7], NMS por clase, parche torch.load para PyTorch 2.6+.
- `tracking_vehicular.py`: `TrackerVehicular` — ByteTrack (boxmot) → DeepSORT →
  Centroid; velocidad real por desplazamiento de centroides × calibración px/m.
- Produce por frame: NumVehiculos, Flujo, Velocidad, LongitudCola, ICV (vía núcleo).
- **Faltantes**: conteo por acceso N/S/E/O (ROI = recorte rectangular único),
  homografía/compensación de dron, ground truth y evaluación (mAP/MAE/RMSE),
  pesos y videos versionados (gitignored). Evidencia real de ejecución:
  `datos/videos-procesados/analisis_VideoPuenteNochePUCP.csv` (1968 frames).
- Emergencia: solo visual; sin audio/sirenas; dataset de entrenamiento VACÍO.

## 11–12. Integración SUMO / TraCI

- `conector_sumo.py`: abstracción libsumo-preferido/traci-fallback (en esta
  máquina: **traci**, libsumo no instalado). SUMO 1.24.0, SUMO_HOME configurado.
- `comparacion_sumo.py` ★: patrón glue real — `_mapear_semaforos()` (fases
  verdes + lanes + presupuesto), `_demanda_fase()`, `_redistribuir_verde()`
  (reparto de presupuesto de verde con clamp duro a LIMITES, aplicado con
  `setProgramLogic` preservando fase en curso). Lazo step-synchronous.
- `comparacion_multibaseline.py` ★: 6 estrategias, seeds reproducibles
  (`--seed` SUMO + `random.seed`), resultados versionados.
- `controlador_sumo_completo.py`: **ROTO/MUERTO** — llama
  `estado_local.actualizar_vehiculo_emergencia()` (método inexistente) y lee
  `resultado['T_verde_NS']` (KeyError: la clave real es `resultado['NS']['T_verde']`),
  errores silenciados por try/except. NO usar como base.
- `simulador_trafico/simulador_lima.py:299`: clampa ICV artificialmente a
  [0.50, 0.60] en modo demo — NO reutilizable para HIL.

## 13–15. Backend / comunicaciones / autenticación

- FastAPI + SQLite (SQLAlchemy), puerto 8000. Telemetría entrante:
  `POST /api/estado-local/ingresar` (consume el paquete de
  `estado_local.obtener_paquete_telemetria()`); `WebSocket /ws` para tiempo real;
  comandos validados en `PUT /api/control/parametros` (tecnico/admin + LIMITES +
  auditoría).
- **MQTT: NO existe en código** (ni paho ni broker; solo menciones en tesis y
  la especificación local). paho-mqtt SÍ está instalado en el entorno Python.
- Azure: `exportador_azure.py` opcional y desconectado (dependencia comentada).

## 16. Tests

Antes de NSB: **cero tests automatizados** (solo 2 smoke scripts manuales de
visión). pytest 7.4.4 declarado pero sin uso. Sin CI, sin Docker.

## 17. Configuración

`servidor-backend/config.py` (pydantic-settings + .env; .env y .env.example
ausentes — .env.example creado por NSB). Parámetros del núcleo científico:
hardcoded como defaults de dataclasses (sin capa de config externa).
Topología de 31 intersecciones de Lima embebida en `main.py:126-309`.

## 18. Elementos reutilizables por NSB

1. Cadena científica completa (ICV+PI+difuso+seguridad) — importable pura.
2. Patrón de lazo SUMO (`comparacion_sumo`) para el HIL Gateway.
3. Auth JWT/RBAC/auditoría del backend para el command plane.
4. Endpoint de telemetría existente para el http_sink.
5. Pipeline de visión offline para `VideoStateSource` (ADVISORY).
6. Contrato de telemetría de `estado_local.obtener_paquete_telemetria()`.

## 19. Elementos faltantes (los construye NSB)

FSM temporal de fases con preempción EV segura; matriz de conflictos explícita;
guard de mensajes (stale/dup/orden/NaN); TSC Emulator con veredictos; modos de
autoridad; actuación (simulada/GPIO); protocolo HIL versionado step-synchronous;
replay determinista; golden master; fault injection; telemetría correlacionable;
MQTT TLS; benchmark; tests; escenario SUMO mínimo controlado; tooling de ground
truth de visión.

## 20–23. Riesgos

- **Duplicación**: 4 ICV / 2 difusos / 2 `ParametrosInterseccion` distintos con
  el mismo nombre (`indice_congestion` vs `estado_local`) → NSB importa con alias
  explícito y consume solo el canónico.
- **Científicos**: resultado multibaseline honesto = difuso (ICV_red≈0.334) por
  detrás de actuated (0.223) y maxpressure (0.220); NSB no altera algoritmos ni
  parámetros; golden master doble protege contra modificación silenciosa.
- **Integración**: imports frágiles (`sys.path.insert`, `from metricas_red
  import ...` plano en `sistema_comparacion.py`) → NSB usa bootstrap propio y
  NO importa `sistema_comparacion`; consola Windows cp1252 vs emojis del núcleo
  en logs → handlers UTF-8 propios; Python dev 3.12.5 vs Pi Bookworm 3.11 →
  piso de sintaxis 3.11.
- **Deuda relevante**: `controlador_sumo_completo.py` roto (candidato a eliminar
  — decisión del autor de la tesis); ruta OneDrive obsoleta en
  `datos/entrenamiento-emergencia/dataset.yaml`; clamp artificial de ICV en el
  simulador demo.

## 24. Plan de integración concreto

Ver `architecture.md` y `decisions.md`. Resumen: paquete aditivo `nsb/` que
adapta el núcleo canónico; HIL TCP JSON-lines step-synchronous PC↔nodo; tres
modos de autoridad con Safety Kernel envolviendo `validador_seguridad`; replay
JSONL; telemetría JSONL/HTTP/MQTT; despliegue a Pi por copia de carpetas.

## 25. Desviaciones respecto a la especificación (especificación local)

Registradas y justificadas una a una en `decisions.md`.
