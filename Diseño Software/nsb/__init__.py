"""NSB v2.1 — Nodo Semafórico de Borde.

Extensión experimental de la tesis de control semafórico adaptativo:
HIL distribuido con SUMO, tres modos de autoridad (ADVISORY, TSC_EMULATED,
AUTOMATED_DIRECT_LAB), Safety Kernel obligatorio, actuación simulada/GPIO,
replay reproducible y telemetría correlacionable.

Reutiliza el núcleo científico canónico (`nucleo/`) vía adaptadores;
NUNCA lo duplica ni lo modifica.

Este paquete no importa dependencias pesadas a nivel de módulo: los imports
de GPIO, MQTT, visión y traci son perezosos y viven en sus módulos
específicos.
"""

__version__ = "2.1.0"
