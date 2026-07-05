# Decisiones arquitectónicas y desviaciones — NSB v2.1

Registro de decisiones (ADR compacto). Cada entrada: contexto → decisión →
justificación. Las desviaciones respecto a la especificación base
(especificación local de diseño, no versionada) están marcadas con **[DESVIACIÓN]**.

---

## D-01 [DESVIACIÓN] CNN-LSTM: solo interfaz, sin implementación

La spec (§21) pedía envolver una "ExistingCnnLstmPredictor". **La auditoría
demostró que la CNN-LSTM no existe en el repositorio** (0 código, 0 modelos,
`datos/modelos-entrenados/` vacío; el único DL es YOLOv8 para visión).
Se implementa `PredictorBackend` (Protocol) + `DisabledPredictor` (default) +
mock exclusivo de tests. No se inventa un predictor ficticio (spec §7.13).
El pipeline registra `predictor_enabled=False` con `fallback_reason`.

## D-02 MQTT no es el data plane del HIL

La spec (§28) ya lo insinuaba; se confirma: el lazo HIL usa **TCP JSON-lines
dedicado** (latencia y orden importan; request-response estricto). MQTT queda
como **plano de telemetría opcional** (paho, lazy). El **command plane
converge en la API FastAPI existente** (JWT+RBAC+validador+auditoría ya
funcionales) — no se duplica autenticación (spec §29).

## D-03 Sockets síncronos stdlib, NO asyncio

traci es bloqueante y monoconexión: dentro de un event loop produce el clásico
"loop bloqueado N segundos". El protocolo step-synchronous es estrictamente
secuencial (request→response): asyncio no aporta concurrencia útil y sí
no-determinismo de scheduling. Sockets con `settimeout()` son triviales de
testear. Nodo monohilo; único hilo extra opcional: render de LEDs (lee
snapshot, jamás decide).

## D-04 Sin `pyproject.toml`; imports por bootstrap

La ruta del workspace (`Diseño Software`, espacio+ñ) hace frágil un install
editable en Windows; el directorio contiene top-levels no empaquetables
(`servidor-backend`, `integracion-sumo`). Mecanismo: `conftest.py` (pytest) +
`nsb/_bootstrap.py` (entry points). Despliegue a Pi por **copia de carpetas**
(`nucleo/ + nsb/ + config/` → `/home/pi/nsb-node/`, ruta ASCII): el layout
relativo se conserva y los imports no cambian.

## D-05 [DESVIACIÓN] Matriz de conflictos por grupos N/S/E/O, no N×N arbitraria

La "matriz de conflictos" real de la tesis es la regla binaria NS/EO
(`verificar_fases_no_conflictivas`). NSB la formaliza como matriz explícita
sobre los 4 grupos de señal (N,S compatibles entre sí; E,O compatibles entre
sí; NS×EO conflictivos), coherente con la intersección de la tesis y los 12
LEDs de la maqueta. No se inventan topologías que la tesis no contempla.

## D-06 La recomendación son TIEMPOS de verde, no saltos de fase

El difuso canónico produce ΔT% sobre tiempos base (spec §19 del repo real).
`RecommendationEnvelope` transporta `PlanSemaforico` (t_verde_ns/eo + ámbar +
todo-rojo) + Δ% + reglas disparadas. Los cambios de fase solo ocurren dentro
de la FSM (transición segura), incluida la preempción EV
(verde→ámbar→todo-rojo→verde compatible, spec §22).

## D-07 Intervalo de control desde configuración (canónico 25 s)

Confirmado en resultados multibaseline (`intervalo_control=25`). NSB lo toma
de `node.yaml`/`gateway.yaml`; jamás hardcodeado (spec §13).

## D-08 `controlador_sumo_completo.py` se ignora

Está roto (método inexistente + KeyError silenciados). El patrón correcto
para el gateway es `comparacion_sumo._mapear_semaforos/_redistribuir_verde`
(setProgramLogic preservando fase). Eliminarlo es decisión del autor.

## D-09 [DESVIACIÓN] Property-based testing sin Hypothesis

Hypothesis no está instalado y la spec (§34) prohíbe añadirla "por moda".
Se implementa fuzz sembrado (`random.Random(seed)`) con miles de secuencias
válidas/inválidas verificando las mismas invariantes. Anotada como mejora
opcional futura.

## D-10 Backend: alcance reducido a integración

JWT/RBAC/auditoría ya existen y funcionan → P2 se limita a: telemetría NSB
hacia el endpoint existente + broker MQTT TLS. Riesgos preexistentes del
backend (SECRET_KEY default, WS sin auth, sin rate limiting) documentados en
`limitations.md`; su corrección es opcional y separada de NSB.

## D-11 Honestidad de plataforma: Pi 4B ausente durante el desarrollo

Todo criterio que exige hardware queda **IMPLEMENTED / REQUIRES HARDWARE**,
nunca VERIFIED. El benchmark corre hoy en Windows y sus números se etiquetan
como Windows; en la Pi se re-ejecuta cuando exista (spec §4, §31, §50).

## D-12 Escenario SUMO mínimo dedicado (`nsb-cruz`)

Los escenarios lima-* tienen decenas de TLS con estructuras de fase OSM
arbitrarias; mapearlos al modelo NS/EO por heurística es frágil. Se genera un
cruce único reproducible (netgenerate + randomTrips con seed) y el mapeo de
fases va **explícito en `gateway.yaml`** (índices declarados, no inferidos).
Los escenarios lima-* siguen disponibles para el flujo multibaseline existente.

## D-A HIL = 1 gateway ↔ 1 nodo (una intersección)

El protocolo transporta `intersection_id` para multi-nodo futuro, pero v2.1
controla la intersección del nodo. Coincide con la maqueta de 12 LEDs.

## D-B El reloj de simulación vive en el gateway

SUMO es la única fuente de `sim_time`. La FSM usa `Clock` inyectable:
`SimClock` (HIL), `WallClock` (demos LEDs), `ManualClock` (tests).
Con `tick_mode: control_only` (default) los LEDs no espejan la simulación
segundo a segundo — documentado honestamente; `tick_mode: per_step` disponible
para demos de espejo.

## D-C Política de timeout dual

`fallback` (mantiene plan vigente / CONFIG_SEGURA tras N timeouts — demos) vs
`fail_fast` (aborta la corrida — campañas de métricas, donde un timeout
contamina el determinismo y no debe mezclarse en resultados publicables).

## D-D PI del nodo = el PI que produjo los resultados de la tesis

Existen TRES variantes de PI en el repo:
1. Canónica cruda del Cap. 6 (`indice_congestion.calcular_parametro_intensidad`,
   PI = Vavg/(SC+δ)) — **no acotada** (puede valer cientos), mientras el difuso
   define sus conjuntos de PI en el universo [0,1].
2. Normalización de `estado_local.calcular_parametro_intensidad` (divide por
   V_MAX/δ con δ=1e-6) — colapsa a ≈0 en cuanto SC≥1: comportamiento casi
   binario que NO alimentó los resultados versionados.
3. La de `comparacion_sumo._demanda_fase`: PI = 0.5·frac_movimiento +
   0.5·min(1, v/50) — acotada [0,1], y es **la que alimentó al difuso en las
   corridas multibaseline** cuyos resultados están versionados en
   `integracion-sumo/resultados/`.

NSB usa la variante 3 (misma referencia de 50 km/h), porque preserva el
comportamiento del sistema que generó la evidencia experimental de la tesis y
respeta el universo [0,1] del difuso. No se inventa una normalización nueva.
El golden master usa la misma, de modo que la equivalencia queda bien definida.

## D-E Piso de sintaxis Python 3.11

Pi OS Bookworm trae 3.11; desarrollo en 3.12.5. Prohibida sintaxis 3.12-only.

## D-F Telemetría en capas

JSONL local **siempre** (fuente de verdad) → HTTP al backend existente
(mapper al contrato de `obtener_paquete_telemetria()`) → MQTT opcional (P2).
Los campos NSB extra (verdicts, seq) viven en JSONL/MQTT, sin tocar el backend.

## D-G Contratos estrictos con `allow_inf_nan=False`

Pydantic v2 acepta NaN/inf por defecto; sin este ajuste la validación de
entradas no finitas exigida por la spec (§11) sería inefectiva. Payloads
científicos con `extra="forbid"`; envelope de transporte con `extra="ignore"`
(forward-compat).

## D-I Telemetría MQTT: QoS 0 + esperas acotadas fuera del lazo de control

El sink MQTT publica QoS 0 best-effort (sin broker: descarta y cuenta, jamás
encola ni espera — el JSONL local es la fuente de verdad, D-F). Las únicas
esperas son acotadas y están FUERA del lazo de control: 2 s de conexión
inicial al construir el nodo y 2 s de drenado al cerrar (sin ellas, las
corridas cortas pierden los primeros/últimos eventos — verificado
empíricamente con broker real). Identidad por nodo vía mTLS: CN del cert =
node_id = usuario de la ACL (`pattern write nsb/%u/#`); el sink no suscribe
ningún tópico (coherente con D-H: MQTT no puede elevar el modo).

## D-H El modo de autoridad solo puede degradarse en runtime

El modo se fija al construir el proceso (config+CLI+env) y únicamente puede
bajar (direct-lab→tsc→advisory). Ninguna vía remota (MQTT/HTTP) puede elevarlo,
ni siquiera si un endpoint futuro lo intentara por error (spec §10.3, §29).
