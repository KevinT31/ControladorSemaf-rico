# Guion de Sustentación — Sistema de Control Semafórico Adaptativo (PUCP)

Guía para demostrar la **viabilidad funcional** del prototipo ante el jurado. Mapea cada
requisito esperado a una acción concreta y nombra los "kill shots" que más sostienen la tesis.

---

## 0) Arranque (antes de entrar)

```
python ejecutar.py        ->  opción 1  (Iniciar Dashboard)
```
Abre `http://localhost:8000`. Para la comparación adaptativo vs ciclo fijo (en vivo, SUMO):
```
python ejecutar.py        ->  opción 4  (Comparar Adaptativo vs Tiempo Fijo)
```
Verificación rápida de que todo está operativo (con el dashboard corriendo):
```
python verificar_demo.py
```

### Credenciales de demostración (RBAC)
| Usuario   | Contraseña    | Rol      | Puede |
|-----------|---------------|----------|-------|
| `operador`| `operador123` | operador | Solo monitoreo (lectura) |
| `tecnico` | `tecnico123`  | tecnico  | + ajustar parámetros, emergencias |
| `admin`   | `admin123`    | admin    | + gestión total |

---

## 1) Recibe datos de tráfico
- **Dashboard en modo SUMO**: el banner superior muestra **"🟢 SUMO en vivo — tráfico real (TraCI)"**.
  El panel "SUMO en Tiempo Real" muestra vehículos, velocidad y congestión reales de la simulación.
- *Defensa*: "Los datos provienen de SUMO vía TraCI, no son aleatorios. El banner etiqueta
  siempre la fuente; si fuera el simulador determinístico, lo diría explícitamente."

## 2) Calcula un estado de congestión (ICV)
- Abre **🔎 Trazabilidad** (cabecera). Con cola=28, vel=12, flujo=22 → **ICV ≈ 0.53 (medio)**, PI mostrado.
- *Defensa*: ICV con la fórmula exacta del Cap. 6.2.3 (pesos 0.35/0.25/0.25/0.15), en `nucleo/indice_congestion.py`.

## 3) Toma decisiones adaptativas
- En **🔎 Trazabilidad**, cambia los valores y pulsa **Recalcular**:
  - Congestión alta (cola=28, vel=12) → verde ≈ **32–33 s** (ΔT positivo).
  - Congestión baja (cola=4, vel=45) → verde ≈ **23 s** (ΔT negativo).
- *Defensa*: "El verde cambia con el tráfico; es control difuso Mamdani de 12 reglas, no un temporizador fijo."

## 4) Respeta la seguridad semafórica
- Abre **🛡️ Seguridad**. Muestra en vivo:
  - Verde de 200 s → **recortado a 120 s**.
  - Datos inválidos (NaN / SUMO caído) → **MODO SEGURO (ciclo fijo)**.
  - Amarillo/todo-rojo en 0 → **forzados a 3 s / 2 s**.
  - Intento de NS y EO en verde a la vez → **BLOQUEADO**.
- *Defensa*: "El módulo optimiza la temporización, pero el controlador mantiene la **autoridad final**
  de seguridad funcional (`nucleo/seguridad_semaforica.py`). Nunca produce un estado peligroso."

## 5) Se comunica con la nube
- El backend (FastAPI + WebSocket) es el plano de nube local: telemetría en vivo (WebSocket),
  recepción de parámetros (`PUT /api/control/parametros`), histórico/auditoría en BD (SQLite).
- *Defensa*: "Es la arquitectura de la tesis (Azure IoT Hub / MQGT-TLS) ejecutada localmente para la demo;
  el flujo telemetría↑ / parámetros↓ es el mismo."

## 6) Incorpora ciberseguridad  ★ (está en el título de la tesis)
- **Login obligatorio** al abrir el dashboard. Entra como `tecnico`.
- **KILL SHOT**: intenta subir un parámetro peligroso. Vía panel o consola:
  ```
  PUT /api/control/parametros   {"t_verde_ns": 200}   ->  422 RECHAZADO
  ```
  Luego abre **🛡️ Auditoría**: el intento aparece como **RECHAZADO** con su motivo.
- **RBAC**: cierra sesión, entra como `operador`. Los controles de escritura están deshabilitados;
  un intento de comando responde **403**.
- *Defensa*: "Ciberseguridad no es solo contraseña: es **proteger la operación**. Hay login JWT
  (HS256), roles, rechazo de comandos peligrosos y bitácora de auditoría inmutable."

## 7) Se valida contra un sistema tradicional
- `python ejecutar.py` → **opción 4**: corre **dos simulaciones SUMO reales** (misma demanda):
  ciclo fijo vs adaptativo, y reporta mejora en ICV, velocidad, demora y throughput.
- *Defensa*: "Comparación cuantitativa real, sin números inventados (`integracion-sumo/comparacion_sumo.py`)."

## 8) La demo es trazable
- **🔎 Trazabilidad** muestra la cadena completa por intersección:
  **Entrada → ICV (nivel) → reglas difusas disparadas (con α) → ΔT → verde final → corrección de seguridad**.
- *Defensa*: "Cada decisión es auditable de principio a fin; el jurado ve de dónde sale cada segundo de verde."

## 9) El sistema es modular
- Arquitectura por capas: adquisición (SUMO/visión) → ICV (`nucleo/indice_congestion.py`) →
  control difuso (`nucleo/controlador_difuso_capitulo6.py`) → **seguridad funcional**
  (`nucleo/seguridad_semaforica.py`) → **ciberseguridad** (`servidor-backend/seguridad/`) →
  nube/API (`servidor-backend/`) → dashboard (`interfaz-web/`) → histórico/auditoría (BD).

---

## Kill shots (los 4 momentos que más convencen)
1. **Rechazo del verde de 200 s** con entrada en la bitácora de auditoría (punto 6).
2. **Modo seguro** ante datos inválidos / caída de SUMO (punto 4).
3. **Comparación adaptativo vs ciclo fijo en vivo** con mejora medible (punto 7).
4. **Operador sin permiso de escritura** (separación monitoreo vs mando, punto 6).

## Pruebas rápidas (por si preguntan "¿cómo sé que funciona?")
- Offline: `python ejecutar.py` → 5 → 6 (Prueba de Seguridad y Ciberseguridad).
- En vivo: `python verificar_demo.py` (con el dashboard arriba).

## Preguntas probables del jurado y respuesta
- **"¿Y si alguien manda un comando peligroso?"** → Se rechaza y se audita (demo del verde 200 s).
- **"¿Podría poner dos vías en verde a la vez?"** → No; la capa de seguridad lo bloquea (panel 🛡️).
- **"¿Si se cae la nube/SUMO?"** → Cae a modo seguro (ciclo fijo) localmente; el control no depende de la nube.
- **"¿La ciberseguridad es real o teórica?"** → Real y demostrable: login JWT, RBAC, validación, auditoría.
- **"¿Por qué no Azure real?"** → Está fuera del alcance del prototipo; la historia local mapea 1:1 a esa
  arquitectura (IoT Hub ↔ login/token, RBAC ↔ roles, firmas SHA-256 ↔ HMAC del JWT).

## Límites honestos (declararlos tú mismo da credibilidad)
- Validación en simulación (SUMO), no en campo. Sin Azure/MQTT real ni certificación IEC 62443.
- El detector de emergencias por visión requiere un modelo YOLO entrenado; la **ola verde** se
  demuestra por su lógica de enrutamiento y activación.
