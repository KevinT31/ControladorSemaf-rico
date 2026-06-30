"""
Subsistema de Ciberseguridad del módulo local
=============================================

Implementación demostrable y local de la capa de ciberseguridad descrita en la
tesis (autenticación, control de acceso por roles, validación/rechazo de
comandos peligrosos y registro de auditoría). Mapea a la arquitectura de nube
(Azure IoT Hub + RBAC + firmas) pero se ejecuta enteramente en el módulo local
para la sustentación, sin dependencias externas frágiles.

Componentes:
    jwt_simple        - tokens JWT HS256 firmados con HMAC-SHA256 (stdlib)
    passwords         - hashing de contraseñas con PBKDF2-HMAC-SHA256 (stdlib)
    usuarios          - almacén de usuarios + roles (operador/tecnico/admin)
    dependencias      - dependencias FastAPI: autenticación + RBAC
    middleware        - exige token válido en /api/* (telemetría y comandos)
    validador_comandos- rechaza parámetros peligrosos antes de aplicarlos
    auditoria         - bitácora append-only (BD + archivo)
"""
