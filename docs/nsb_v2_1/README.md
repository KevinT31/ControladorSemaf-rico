# NSB v2.1 — Nodo Semafórico de Borde

Extensión experimental de la tesis de control semafórico adaptativo:
**HIL distribuido + Edge AI + actuación física de laboratorio**, reutilizando
el núcleo científico canónico (`Diseño Software/nucleo/`) sin duplicarlo.

> ⚠ PROTOTIPO DE LABORATORIO. LEDs de baja potencia. NO es un controlador
> vial certificado ni ha sido validado en campo. Ver `limitations.md`.

## Qué es

```
FUENTE (SUMO HIL | video | replay | manual)
   ▼
TrafficState ──► ICV + PI + EV (núcleo canónico) ──► Difuso Cap. 6 ──► Recommendation
   ▼
AUTORIDAD:  ADVISORY (solo registra) | TSC_EMULATED (emulador decide) |
            AUTOMATED_DIRECT_LAB (nodo decide, experimental, triple compuerta)
   ▼
Safety Kernel (límites de la tesis + FSM + matriz de conflictos + SafetyGate)
   ▼
ActuatorBackend (Simulated en Windows | GPIO 12 LEDs en Raspberry Pi 4B)
```

## Documentos

| Doc | Contenido |
|---|---|
| `repo_audit.md` | Auditoría del repositorio previa al desarrollo |
| `decisions.md` | Decisiones arquitectónicas y desviaciones de la spec |
| `architecture.md` | Arquitectura detallada de NSB |
| `modes.md` | Los tres modos de autoridad y sus garantías |
| `hil_protocol.md` | Protocolo HIL versionado (TCP JSON-lines) |
| `replay.md` | Grabación/replay determinista |
| `fault_injection.md` | Inyección de fallos (12 escenarios) |
| `experiments.md` | Procedimientos experimentales y demos |
| `raspberry_pi_deployment.md` | Despliegue en Pi 4B |
| `gpio_wiring.md` | Cableado de los 12 LEDs (leer ANTES de conectar) |
| `mqtt_tls.md` | Broker Mosquitto + TLS de laboratorio |
| `drone_video_validation.md` | Validación con video real de dron |
| `limitations.md` | Limitaciones honestas del prototipo |

## Inicio rápido (Windows, sin hardware)

```powershell
cd "C:\ControladorSemafrico\Diseño Software"
python -m pytest tests -q          # suite completa
python -m nsb --help               # CLI del nodo
```

Los comandos completos de cada demo están en `experiments.md`.
