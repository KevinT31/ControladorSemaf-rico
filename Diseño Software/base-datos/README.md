# 💾 **Base de Datos del Sistema**

## 🎯 **Propósito de esta Carpeta**

Esta carpeta contiene **TODO lo relacionado con la base de datos persistente** del sistema:

- **Esquema SQL** (`schema.sql`) - Estructura de tablas optimizada para series temporales
- **Base de datos SQLite** (`semaforos.db`) - Para desarrollo local
- **Migraciones** (`migraciones/`) - Versionamiento del esquema con Alembic

---

## 🗄️ **Relación con Otras Carpetas**

```
base-datos/  ←───────── Persistencia estructurada (SQL)
    │
    ├─ ESCRIBE ← servidor-backend/servicios/
    │            (métricas en tiempo real)
    │
    ├─ ESCRIBE ← integracion-sumo/conector_sumo.py
    │            (exportación SUMO)
    │
    ├─ LEE ─────→ servidor-backend/rutas/estadisticas.py
    │            (consultas históricas)
    │
    └─ LEE ─────→ Calculo-Matlab/*.m
                 (análisis offline)

datos/  ←──────────────── Archivos temporales (CSV, Parquet, logs)
```

### **¿Cuándo usar `base-datos/` vs `datos/`?**

| Tipo de Dato | Dónde | Ejemplo |
|--------------|-------|---------|
| **Series temporales estructuradas** | `base-datos/` (SQL) | Métricas de tráfico cada segundo |
| **Archivos temporales** | `datos/` | CSV de análisis de video |
| **Resultados de procesamiento** | `datos/` | Frames anotados de YOLO |
| **Modelos ML entrenados** | `datos/` | `predictor_icv_v1.pkl` |
| **Historial de emergencias** | `base-datos/` (SQL) | Olas verdes activadas |
| **Logs del sistema** | `datos/` | `backend-2025-01-15.log` |

---

## 📊 **Esquema de Base de Datos**

Ver **`schema.sql`** para el esquema completo.

### **Tablas Principales:**

1. **`intersecciones`** - Catálogo de las 31 intersecciones de Lima
2. **`metricas_trafico`** - Series temporales (TimescaleDB hypertable)
3. **`olas_verdes`** - Historial de vehículos de emergencia
4. **`detecciones_video`** - Detecciones YOLO individuales
5. **`simulaciones_sumo`** - Datos exportados desde SUMO
6. **`decisiones_difusas`** - Log del controlador difuso
7. **`conexiones_intersecciones`** - Grafo de red vial

---

## 🚀 **Configuración**

### **Desarrollo (SQLite)**

SQLite se usa automáticamente en desarrollo:

```python
# En servidor-backend/config.py
DATABASE_URL = "sqlite:///./base-datos/semaforos.db"
```

### **Producción (PostgreSQL + TimescaleDB)**

Para producción, cambiar a TimescaleDB:

```python
# En servidor-backend/config.py
DATABASE_URL = "postgresql://user:pass@localhost:5432/semaforos"
```

**Instalar TimescaleDB:**

```bash
# PostgreSQL con TimescaleDB
docker run -d --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  timescale/timescaledb:latest-pg15

# Crear base de datos
psql -U postgres -h localhost
CREATE DATABASE semaforos;
\c semaforos
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Ejecutar schema.sql
psql -U postgres -h localhost -d semaforos -f schema.sql
```

---

## 🔧 **Uso desde Python**

### **1. Insertar Métricas en Tiempo Real**

```python
from servicios.estadisticas_service import EstadisticasService

# Guardar métricas
EstadisticasService.guardar_metricas(
    interseccion_id='LC-001',
    timestamp=datetime.now(),
    num_vehiculos=45,
    icv=0.65,
    flujo=120.5,
    velocidad=35.2,
    longitud_cola=78.5,
    fuente='simulador'
)
```

### **2. Consultar Datos Históricos**

```python
# Obtener métricas de las últimas 24 horas
metricas = EstadisticasService.obtener_metricas_periodo(
    interseccion_id='LC-001',
    horas=24
)

# Calcular estadísticas agregadas
stats = EstadisticasService.calcular_estadisticas(
    interseccion_id='LC-001',
    periodo_inicio=datetime(2025, 1, 1),
    periodo_fin=datetime(2025, 1, 31)
)

print(f"ICV Promedio: {stats['icv_promedio']}")
print(f"Horas de congestión: {stats['horas_congestion']}")
```

### **3. Exportar para Machine Learning**

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('sqlite:///./base-datos/semaforos.db')

# Extraer datos de entrenamiento
query = """
SELECT timestamp, interseccion_id, icv, flujo_vehicular,
       velocidad_promedio, longitud_cola
FROM metricas_trafico
WHERE timestamp >= datetime('now', '-30 days')
"""

df = pd.read_sql(query, engine)

# Entrenar modelo
from sklearn.ensemble import RandomForestRegressor
X = df[['flujo_vehicular', 'velocidad_promedio', 'longitud_cola']]
y = df['icv']

modelo = RandomForestRegressor()
modelo.fit(X, y)

# Guardar
import joblib
joblib.dump(modelo, 'datos/modelos-entrenados/predictor_icv_v2.pkl')
```

---

## 📈 **Migraciones (Alembic)**

### **Inicializar Alembic**

```bash
cd servidor-backend
pip install alembic
alembic init ../base-datos/migraciones
```

### **Crear Nueva Migración**

```bash
alembic revision -m "Agregar columna metadata a intersecciones"
```

### **Aplicar Migraciones**

```bash
alembic upgrade head
```

### **Revertir Migración**

```bash
alembic downgrade -1
```

---

## 🔍 **Consultas Útiles**

### **ICV Promedio por Zona**

```sql
SELECT i.zona, AVG(mt.icv) as icv_promedio
FROM metricas_trafico mt
INNER JOIN intersecciones i ON mt.interseccion_id = i.id
WHERE mt.timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY i.zona
ORDER BY icv_promedio DESC;
```

### **Intersecciones Más Congestionadas**

```sql
SELECT interseccion_id, AVG(icv) as icv_promedio
FROM metricas_trafico
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY interseccion_id
ORDER BY icv_promedio DESC
LIMIT 10;
```

### **Olas Verdes Activas**

```sql
SELECT * FROM olas_verdes_activas;  -- Vista
```

### **Estadísticas de Emergencias**

```sql
SELECT tipo_vehiculo, COUNT(*) as total,
       AVG(tiempo_total_segundos) as tiempo_promedio
FROM olas_verdes
WHERE completado = TRUE
GROUP BY tipo_vehiculo;
```

---

## 🧪 **Testing**

```python
# tests/test_database.py
import pytest
from sqlalchemy import create_engine
from datetime import datetime

def test_insertar_metrica():
    engine = create_engine('sqlite:///:memory:')
    # ... crear tablas con schema.sql

    # Insertar métrica
    conn = engine.connect()
    conn.execute("""
        INSERT INTO metricas_trafico
        (timestamp, interseccion_id, icv, fuente)
        VALUES (?, ?, ?, ?)
    """, (datetime.now(), 'LC-001', 0.65, 'test'))

    # Verificar
    result = conn.execute(
        "SELECT COUNT(*) FROM metricas_trafico"
    ).scalar()

    assert result == 1
```

---

## 📚 **Recursos**

- **PostgreSQL**: https://www.postgresql.org/docs/
- **TimescaleDB**: https://docs.timescale.com/
- **Alembic**: https://alembic.sqlalchemy.org/
- **SQLAlchemy**: https://docs.sqlalchemy.org/

---

## 🔐 **Seguridad**

### **Desarrollo**

```python
# ✅ OK para desarrollo
DATABASE_URL = "sqlite:///./base-datos/semaforos.db"
```

### **Producción**

```python
# ❌ MAL - Nunca hardcodear credenciales
DATABASE_URL = "postgresql://admin:1234@localhost/semaforos"

# ✅ BIEN - Usar variables de entorno
import os
DATABASE_URL = os.getenv('DATABASE_URL')
```

**.env:**
```
DATABASE_URL=postgresql://admin:password@localhost:5432/semaforos
```

---

## 📊 **Monitoreo**

### **Tamaño de la Base de Datos**

```sql
-- PostgreSQL
SELECT pg_size_pretty(pg_database_size('semaforos'));

-- SQLite
SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();
```

### **Tablas Más Grandes**

```sql
-- PostgreSQL
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🎯 **Roadmap**

- [ ] Implementar SQLAlchemy ORM en `servidor-backend/modelos_bd/`
- [ ] Crear script `poblar_intersecciones.py`
- [ ] Configurar Alembic para migraciones
- [ ] Implementar exportación automática SUMO → BD
- [ ] Agregar índices adicionales para consultas ML
- [ ] Configurar backup automático
- [ ] Implementar política de retención (1 año)
- [ ] Agregar métricas de monitoreo (Prometheus)

---

**🔗 Ver también:** `ARQUITECTURA_COMPLETA.md` en la raíz del proyecto
