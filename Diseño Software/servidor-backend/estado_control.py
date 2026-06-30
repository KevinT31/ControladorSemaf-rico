"""
Configuración de control vigente (compartida entre rutas)
=========================================================

Parámetros base del controlador semafórico que la "nube"/operador puede
actualizar (con validación de seguridad). Mantenerlos en un módulo aparte evita
importaciones circulares entre las rutas y permite que la trazabilidad lea la
configuración activa.
"""

# Parámetros base vigentes (segundos). Se actualizan solo vía endpoint protegido
# y validado /api/control/parametros.
config_control = {
    "t_verde_ns": 30.0,
    "t_verde_eo": 30.0,
    "t_ambar": 3.0,
    "t_todo_rojo": 2.0,
    "t_ciclo": 90.0,
    "t_verde_min": 10.0,
    "t_verde_max": 120.0,
}
