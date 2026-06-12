-- ==========================================
-- ESQUEMA DE BASE DE DATOS
-- Sistema de Control Semafórico Inteligente
-- ==========================================

-- Tabla: intersecciones
-- Catálogo maestro de intersecciones
CREATE TABLE IF NOT EXISTS intersecciones (
    id VARCHAR(20) PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    latitud DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    num_carriles INTEGER NOT NULL CHECK (num_carriles > 0),
    zona VARCHAR(50) CHECK (zona IN ('norte', 'sur', 'este', 'oeste', 'centro')),
    fecha_instalacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    UNIQUE(latitud, longitud)
);

CREATE INDEX idx_intersecciones_zona ON intersecciones(zona);
CREATE INDEX idx_intersecciones_activo ON intersecciones(activo);


-- Tabla: metricas_trafico
-- Serie temporal de métricas de tráfico por intersección
-- HYPERTABLE en TimescaleDB para optimización
CREATE TABLE IF NOT EXISTS metricas_trafico (
    timestamp TIMESTAMPTZ NOT NULL,
    interseccion_id VARCHAR(20) NOT NULL,
    num_vehiculos INTEGER DEFAULT 0,
    flujo_vehicular DOUBLE PRECISION DEFAULT 0.0 CHECK (flujo_vehicular >= 0),
    velocidad_promedio DOUBLE PRECISION DEFAULT 0.0 CHECK (velocidad_promedio >= 0),
    longitud_cola DOUBLE PRECISION DEFAULT 0.0 CHECK (longitud_cola >= 0),
    icv DOUBLE PRECISION DEFAULT 0.0 CHECK (icv BETWEEN 0 AND 1),
    clasificacion_icv VARCHAR(20) CHECK (clasificacion_icv IN ('fluido', 'moderado', 'congestionado')),
    fuente VARCHAR(20) CHECK (fuente IN ('simulador', 'video', 'sumo')),
    metadata JSONB,
    PRIMARY KEY (timestamp, interseccion_id),
    FOREIGN KEY (interseccion_id) REFERENCES intersecciones(id) ON DELETE CASCADE
);

-- Convertir a TimescaleDB Hypertable (ejecutar después de crear la tabla)
-- SELECT create_hypertable('metricas_trafico', 'timestamp', if_not_exists => TRUE);

-- Índices para consultas rápidas
CREATE INDEX idx_metricas_interseccion ON metricas_trafico(interseccion_id, timestamp DESC);
CREATE INDEX idx_metricas_timestamp ON metricas_trafico(timestamp DESC);
CREATE INDEX idx_metricas_icv ON metricas_trafico(icv);
CREATE INDEX idx_metricas_fuente ON metricas_trafico(fuente);


-- Tabla: olas_verdes
-- Historial de olas verdes de emergencia
CREATE TABLE IF NOT EXISTS olas_verdes (
    id SERIAL PRIMARY KEY,
    vehiculo_id VARCHAR(50) NOT NULL UNIQUE,
    tipo_vehiculo VARCHAR(20) CHECK (tipo_vehiculo IN ('ambulancia', 'bomberos', 'policia')),
    origen_id VARCHAR(20) NOT NULL,
    destino_id VARCHAR(20) NOT NULL,
    velocidad_estimada DOUBLE PRECISION CHECK (velocidad_estimada BETWEEN 20 AND 120),
    prioridad VARCHAR(20) CHECK (prioridad IN ('critica', 'alta', 'media')),
    timestamp_activacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timestamp_desactivacion TIMESTAMPTZ,
    ruta JSONB NOT NULL, -- Array de IDs de intersecciones
    tiempo_total_segundos INTEGER,
    distancia_total_metros DOUBLE PRECISION,
    completado BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    FOREIGN KEY (origen_id) REFERENCES intersecciones(id),
    FOREIGN KEY (destino_id) REFERENCES intersecciones(id),
    CHECK (timestamp_desactivacion IS NULL OR timestamp_desactivacion > timestamp_activacion)
);

CREATE INDEX idx_olas_verdes_timestamp ON olas_verdes(timestamp_activacion DESC);
CREATE INDEX idx_olas_verdes_tipo ON olas_verdes(tipo_vehiculo);
CREATE INDEX idx_olas_verdes_origen ON olas_verdes(origen_id);
CREATE INDEX idx_olas_verdes_destino ON olas_verdes(destino_id);
CREATE INDEX idx_olas_verdes_activas ON olas_verdes(completado) WHERE completado = FALSE;


-- Tabla: detecciones_video
-- Detecciones individuales de vehículos por YOLO
CREATE TABLE IF NOT EXISTS detecciones_video (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    interseccion_id VARCHAR(20),
    frame_numero INTEGER NOT NULL,
    clase_vehiculo VARCHAR(50) NOT NULL,
    confianza DOUBLE PRECISION NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    bbox JSONB NOT NULL, -- {x, y, width, height}
    tracking_id INTEGER,
    video_fuente VARCHAR(200),
    metadata JSONB,
    FOREIGN KEY (interseccion_id) REFERENCES intersecciones(id) ON DELETE SET NULL
);

CREATE INDEX idx_detecciones_timestamp ON detecciones_video(timestamp DESC);
CREATE INDEX idx_detecciones_interseccion ON detecciones_video(interseccion_id, timestamp DESC);
CREATE INDEX idx_detecciones_clase ON detecciones_video(clase_vehiculo);


-- Tabla: simulaciones_sumo
-- Datos exportados desde SUMO para ML
CREATE TABLE IF NOT EXISTS simulaciones_sumo (
    timestamp TIMESTAMPTZ NOT NULL,
    edge_id VARCHAR(100) NOT NULL,
    num_vehiculos INTEGER DEFAULT 0,
    velocidad_promedio DOUBLE PRECISION DEFAULT 0.0,
    ocupacion DOUBLE PRECISION DEFAULT 0.0 CHECK (ocupacion BETWEEN 0 AND 1),
    tiempo_espera DOUBLE PRECISION DEFAULT 0.0,
    metadata JSONB,
    PRIMARY KEY (timestamp, edge_id)
);

-- Convertir a TimescaleDB Hypertable
-- SELECT create_hypertable('simulaciones_sumo', 'timestamp', if_not_exists => TRUE);

CREATE INDEX idx_sumo_edge ON simulaciones_sumo(edge_id, timestamp DESC);
CREATE INDEX idx_sumo_timestamp ON simulaciones_sumo(timestamp DESC);


-- Tabla: decisiones_difusas
-- Log de decisiones del controlador difuso para análisis ML
CREATE TABLE IF NOT EXISTS decisiones_difusas (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    interseccion_id VARCHAR(20) NOT NULL,
    icv_entrada DOUBLE PRECISION NOT NULL,
    flujo_entrada DOUBLE PRECISION NOT NULL,
    tiempo_verde_salida DOUBLE PRECISION NOT NULL,
    reglas_activadas JSONB, -- Array de reglas que se activaron
    metadata JSONB,
    FOREIGN KEY (interseccion_id) REFERENCES intersecciones(id) ON DELETE CASCADE
);

CREATE INDEX idx_decisiones_timestamp ON decisiones_difusas(timestamp DESC);
CREATE INDEX idx_decisiones_interseccion ON decisiones_difusas(interseccion_id, timestamp DESC);


-- Tabla: conexiones_intersecciones
-- Grafo de conectividad entre intersecciones
CREATE TABLE IF NOT EXISTS conexiones_intersecciones (
    id SERIAL PRIMARY KEY,
    origen_id VARCHAR(20) NOT NULL,
    destino_id VARCHAR(20) NOT NULL,
    distancia_metros DOUBLE PRECISION NOT NULL CHECK (distancia_metros > 0),
    tiempo_promedio_segundos INTEGER,
    bidireccional BOOLEAN DEFAULT TRUE,
    activo BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    FOREIGN KEY (origen_id) REFERENCES intersecciones(id) ON DELETE CASCADE,
    FOREIGN KEY (destino_id) REFERENCES intersecciones(id) ON DELETE CASCADE,
    UNIQUE(origen_id, destino_id)
);

CREATE INDEX idx_conexiones_origen ON conexiones_intersecciones(origen_id);
CREATE INDEX idx_conexiones_destino ON conexiones_intersecciones(destino_id);


-- ==========================================
-- VISTAS ÚTILES
-- ==========================================

-- Vista: metricas_ultimas_24h
CREATE OR REPLACE VIEW metricas_ultimas_24h AS
SELECT
    interseccion_id,
    AVG(icv) as icv_promedio,
    MAX(icv) as icv_maximo,
    MIN(icv) as icv_minimo,
    AVG(velocidad_promedio) as velocidad_promedio,
    AVG(flujo_vehicular) as flujo_promedio,
    SUM(num_vehiculos) as total_vehiculos,
    COUNT(CASE WHEN clasificacion_icv = 'congestionado' THEN 1 END) as mediciones_congestionadas
FROM metricas_trafico
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY interseccion_id;


-- Vista: olas_verdes_activas
CREATE OR REPLACE VIEW olas_verdes_activas AS
SELECT
    vehiculo_id,
    tipo_vehiculo,
    origen_id,
    destino_id,
    prioridad,
    timestamp_activacion,
    EXTRACT(EPOCH FROM (NOW() - timestamp_activacion)) as segundos_activa,
    ruta,
    distancia_total_metros
FROM olas_verdes
WHERE completado = FALSE;


-- Vista: estadisticas_intersecciones
CREATE OR REPLACE VIEW estadisticas_intersecciones AS
SELECT
    i.id,
    i.nombre,
    i.zona,
    COUNT(DISTINCT mt.timestamp::date) as dias_con_datos,
    AVG(mt.icv) as icv_promedio_historico,
    AVG(mt.velocidad_promedio) as velocidad_promedio_historica,
    COUNT(*) as total_mediciones
FROM intersecciones i
LEFT JOIN metricas_trafico mt ON i.id = mt.interseccion_id
GROUP BY i.id, i.nombre, i.zona;


-- ==========================================
-- FUNCIONES ÚTILES
-- ==========================================

-- Función: calcular_congestion_promedio
-- Calcula el ICV promedio de una zona en un período
CREATE OR REPLACE FUNCTION calcular_congestion_promedio(
    p_zona VARCHAR,
    p_horas INTEGER DEFAULT 24
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    v_icv_promedio DOUBLE PRECISION;
BEGIN
    SELECT AVG(mt.icv) INTO v_icv_promedio
    FROM metricas_trafico mt
    INNER JOIN intersecciones i ON mt.interseccion_id = i.id
    WHERE i.zona = p_zona
      AND mt.timestamp >= NOW() - (p_horas || ' hours')::INTERVAL;

    RETURN COALESCE(v_icv_promedio, 0.0);
END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- POLÍTICAS DE RETENCIÓN (TimescaleDB)
-- ==========================================

-- Comprimir datos de métricas más antiguos de 7 días
-- SELECT add_compression_policy('metricas_trafico', INTERVAL '7 days');

-- Eliminar automáticamente datos más antiguos de 1 año
-- SELECT add_retention_policy('metricas_trafico', INTERVAL '365 days');

-- Lo mismo para simulaciones SUMO
-- SELECT add_compression_policy('simulaciones_sumo', INTERVAL '7 days');
-- SELECT add_retention_policy('simulaciones_sumo', INTERVAL '180 days');


-- ==========================================
-- DATOS INICIALES
-- ==========================================

-- Insertar las 31 intersecciones de Lima
-- (Se insertan desde el código Python en main.py)
