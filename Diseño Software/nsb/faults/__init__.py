"""Fault injection (spec §32): módulo SEPARADO y EXPLÍCITO.

Nada de este paquete se importa desde el camino de producción (node,
authority, hil): solo lo usan los tests y el subcomando `demo` del CLI.
No existe configuración que lo active accidentalmente.
"""
