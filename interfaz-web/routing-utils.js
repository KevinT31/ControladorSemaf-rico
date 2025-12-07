/**
 * Utilidades para Ruteo con Mapbox Directions API
 * Dibuja rutas que siguen las calles reales del mapa
 */

// Caché de rutas para evitar solicitudes duplicadas a Mapbox
const cacheRutas = new Map();

// Control de solicitudes concurrentes
let solicitudesActivas = 0;
const MAX_SOLICITUDES_CONCURRENTES = 5;

/**
 * Genera una clave única para una ruta
 * @param {Array} inicio - [latitud, longitud]
 * @param {Array} fin - [latitud, longitud]
 * @param {string} profile - Perfil de ruta
 * @returns {string} Clave única
 */
function generarClaveRuta(inicio, fin, profile) {
    return `${inicio[0].toFixed(5)},${inicio[1].toFixed(5)}-${fin[0].toFixed(5)},${fin[1].toFixed(5)}-${profile}`;
}

/**
 * Obtiene una ruta real entre dos puntos usando Mapbox Directions API
 * Incluye sistema de caché para evitar solicitudes duplicadas
 * @param {Array} inicio - [latitud, longitud] del punto de inicio
 * @param {Array} fin - [latitud, longitud] del punto de destino
 * @param {string} profile - Perfil de ruta: 'driving', 'walking', 'cycling'
 * @returns {Promise<Object>} Ruta con geometría GeoJSON
 */
async function obtenerRutaMapbox(inicio, fin, profile = 'driving') {
    // Verificar si el token está configurado
    if (CONFIG.MAPBOX_TOKEN === 'TU_TOKEN_MAPBOX_AQUI') {
        return null;
    }

    // Verificar caché primero
    const claveCache = generarClaveRuta(inicio, fin, profile);
    if (cacheRutas.has(claveCache)) {
        console.log('✓ Ruta obtenida del caché');
        return cacheRutas.get(claveCache);
    }

    try {
        // Esperar si hay demasiadas solicitudes concurrentes
        while (solicitudesActivas >= MAX_SOLICITUDES_CONCURRENTES) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        solicitudesActivas++;

        // Convertir de [lat, lng] a [lng, lat] (formato Mapbox)
        const coordsInicio = `${inicio[1]},${inicio[0]}`;
        const coordsFin = `${fin[1]},${fin[0]}`;

        // Construir URL de la API con annotations para obtener más datos
        const url = `${CONFIG.MAPBOX_DIRECTIONS_API}/${profile}/${coordsInicio};${coordsFin}` +
                    `?geometries=geojson` +
                    `&overview=full` +
                    `&steps=true` +
                    `&annotations=duration,distance,speed` +
                    `&access_token=${CONFIG.MAPBOX_TOKEN}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Error de Mapbox API: ${response.status}`);
        }

        const data = await response.json();

        if (!data.routes || data.routes.length === 0) {
            console.error('No se encontró una ruta');
            return null;
        }

        const route = data.routes[0];

        // Extraer datos adicionales de annotations si están disponibles
        const leg = route.legs[0];
        const annotations = leg.annotation || {};
        
        // Calcular velocidad promedio si hay datos de speed
        let velocidadPromedio = null;
        if (annotations.speed && annotations.speed.length > 0) {
            const sumSpeed = annotations.speed.reduce((a, b) => a + b, 0);
            velocidadPromedio = sumSpeed / annotations.speed.length; // m/s
        }

        const resultado = {
            geometry: route.geometry,
            distance: route.distance,  // en metros
            duration: route.duration,  // en segundos
            weight: route.weight,      // peso del algoritmo
            weight_name: route.weight_name,
            steps: leg.steps,
            // Datos adicionales de annotations
            annotations: {
                distance: annotations.distance || [],
                duration: annotations.duration || [],
                speed: annotations.speed || [],
                velocidad_promedio_ms: velocidadPromedio
            }
        };

        // Guardar en caché para futuras solicitudes
        cacheRutas.set(claveCache, resultado);

        solicitudesActivas--;
        return resultado;

    } catch (error) {
        console.error('Error obteniendo ruta de Mapbox:', error);
        solicitudesActivas--;
        return null;
    }
}

/**
 * Obtiene una ruta real entre múltiples waypoints usando Mapbox Directions API
 * Acepta hasta 25 waypoints para rutas complejas
 * @param {Array<Array>} waypoints - Array de [latitud, longitud] de cada waypoint
 * @param {string} profile - Perfil de ruta: 'driving', 'walking', 'cycling'
 * @returns {Promise<Object>} Ruta con geometría GeoJSON o null si falla
 */
async function obtenerRutaMapboxMultiple(waypoints, profile = 'driving') {
    // Verificar si el token está configurado
    if (CONFIG.MAPBOX_TOKEN === 'TU_TOKEN_MAPBOX_AQUI') {
        console.warn('Sin token Mapbox - no se puede calcular ruta múltiple');
        return null;
    }

    if (!waypoints || waypoints.length < 2) {
        console.error('Se requieren al menos 2 waypoints');
        return null;
    }

    if (waypoints.length > 25) {
        console.warn('Mapbox soporta máximo 25 waypoints, tomando primeros 25');
        waypoints = waypoints.slice(0, 25);
    }

    try {
        // Esperar si hay demasiadas solicitudes concurrentes
        while (solicitudesActivas >= MAX_SOLICITUDES_CONCURRENTES) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        solicitudesActivas++;

        // Convertir waypoints de [lat, lng] a [lng, lat] y unirlos con ';'
        const coordsString = waypoints.map(w => `${w[1]},${w[0]}`).join(';');

        // Construir URL de la API con annotations
        const url = `${CONFIG.MAPBOX_DIRECTIONS_API}/${profile}/${coordsString}` +
                    `?geometries=geojson` +
                    `&overview=full` +
                    `&steps=true` +
                    `&annotations=duration,distance,speed` +
                    `&access_token=${CONFIG.MAPBOX_TOKEN}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Error de Mapbox API: ${response.status}`);
        }

        const data = await response.json();

        if (!data.routes || data.routes.length === 0) {
            console.error('No se encontró una ruta para los waypoints dados');
            solicitudesActivas--;
            return null;
        }

        const route = data.routes[0];

        const resultado = {
            geometry: route.geometry,
            distance: route.distance,  // en metros
            duration: route.duration,  // en segundos
            weight: route.weight,
            weight_name: route.weight_name,
            legs: route.legs
        };

        solicitudesActivas--;
        console.log(`✓ Ruta múltiple calculada: ${waypoints.length} waypoints, ${route.distance.toFixed(0)}m`);
        return resultado;

    } catch (error) {
        console.error('Error obteniendo ruta múltiple de Mapbox:', error);
        solicitudesActivas--;
        return null;
    }
}

/**
 * Obtiene una ruta que pasa por múltiples intersecciones
 * @param {Array<string>} interseccionesIds - Array de IDs de intersecciones
 * @param {Object} interseccionesData - Datos de todas las intersecciones
 * @returns {Promise<Array>} Array de coordenadas [lat, lng] que siguen las calles
 */
async function obtenerRutaMultipuntos(interseccionesIds, interseccionesData) {
    if (!interseccionesIds || interseccionesIds.length < 2) {
        return [];
    }

    const coordenadasFinales = [];

    // Si no hay token de Mapbox, devolver línea recta
    if (CONFIG.MAPBOX_TOKEN === 'TU_TOKEN_MAPBOX_AQUI') {
        console.warn('Sin token Mapbox - usando línea recta');
        return interseccionesIds.map(id => {
            const inter = interseccionesData.find(i => i.id === id);
            return inter ? [inter.latitud, inter.longitud] : null;
        }).filter(c => c !== null);
    }

    // Obtener ruta real entre cada par de intersecciones consecutivas
    for (let i = 0; i < interseccionesIds.length - 1; i++) {
        const origenId = interseccionesIds[i];
        const destinoId = interseccionesIds[i + 1];

        const interOrigen = interseccionesData.find(int => int.id === origenId);
        const interDestino = interseccionesData.find(int => int.id === destinoId);

        if (!interOrigen || !interDestino) {
            console.warn(`No se encontró intersección: ${origenId} o ${destinoId}`);
            continue;
        }

        const inicio = [interOrigen.latitud, interOrigen.longitud];
        const fin = [interDestino.latitud, interDestino.longitud];

        // Obtener ruta entre estos dos puntos
        const ruta = await obtenerRutaMapbox(inicio, fin, CONFIG.DRIVING_PROFILE);

        if (ruta && ruta.geometry && ruta.geometry.coordinates) {
            // Convertir de [lng, lat] (GeoJSON) a [lat, lng] (Leaflet)
            const coordsSegmento = ruta.geometry.coordinates.map(
                coord => [coord[1], coord[0]]
            );

            // Agregar estas coordenadas (evitar duplicados en puntos de conexión)
            if (coordenadasFinales.length === 0) {
                coordenadasFinales.push(...coordsSegmento);
            } else {
                // Saltar el primer punto si es igual al último agregado
                coordenadasFinales.push(...coordsSegmento.slice(1));
            }
        } else {
            // Fallback: agregar línea recta si falla Mapbox
            if (coordenadasFinales.length === 0) {
                coordenadasFinales.push(inicio);
            }
            coordenadasFinales.push(fin);
        }
    }

    console.log(`✓ Ruta completa generada: ${coordenadasFinales.length} puntos`);
    return coordenadasFinales;
}

/**
 * Dibuja una ruta en el mapa siguiendo las calles reales
 * @param {Object} mapa - Instancia de Leaflet map
 * @param {Array<string>} rutaIds - IDs de intersecciones que forman la ruta
 * @param {Object} interseccionesData - Datos de intersecciones
 * @param {Object} opciones - Opciones de estilo para la polilínea
 * @returns {Promise<Object>} Objeto con la capa de la ruta y sus datos
 */
async function dibujarRutaEnMapa(mapa, rutaIds, interseccionesData, opciones = {}) {
    console.log('Dibujando ruta con', rutaIds.length, 'intersecciones');

    // Obtener coordenadas reales que siguen las calles
    const coordenadas = await obtenerRutaMultipuntos(rutaIds, interseccionesData);

    if (coordenadas.length < 2) {
        console.error('No se pudieron obtener coordenadas válidas para la ruta');
        return null;
    }

    // Opciones por defecto
    const opcionesDefecto = {
        color: '#10b981',
        weight: 8,
        opacity: 0.9,
        dashArray: '15, 10',
        lineCap: 'round',
        lineJoin: 'round',
        className: 'ruta-animada'
    };

    // Combinar con opciones proporcionadas
    const opcionesFinales = { ...opcionesDefecto, ...opciones };

    // Dibujar la ruta principal
    const rutaPrincipal = L.polyline(coordenadas, opcionesFinales).addTo(mapa);

    // Dibujar sombra para mejor visibilidad
    const sombra = L.polyline(coordenadas, {
        color: '#000000',
        weight: opcionesFinales.weight + 2,
        opacity: 0.3,
        dashArray: opcionesFinales.dashArray,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(mapa);

    // Ajustar vista del mapa a la ruta
    mapa.fitBounds(coordenadas);

    return {
        rutaPrincipal: rutaPrincipal,
        sombra: sombra,
        coordenadas: coordenadas,
        distancia: calcularDistanciaRuta(coordenadas)
    };
}

/**
 * Calcula la distancia total de una ruta
 * @param {Array<Array>} coordenadas - Array de [lat, lng]
 * @returns {number} Distancia en metros
 */
function calcularDistanciaRuta(coordenadas) {
    if (!coordenadas || coordenadas.length < 2) {
        return 0;
    }

    let distanciaTotal = 0;
    for (let i = 0; i < coordenadas.length - 1; i++) {
        distanciaTotal += calcularDistanciaHaversine(
            coordenadas[i][0], coordenadas[i][1],
            coordenadas[i + 1][0], coordenadas[i + 1][1]
        );
    }

    return distanciaTotal;
}

/**
 * Calcula distancia entre dos puntos usando la fórmula de Haversine
 * @param {number} lat1 - Latitud del punto 1
 * @param {number} lon1 - Longitud del punto 1
 * @param {number} lat2 - Latitud del punto 2
 * @param {number} lon2 - Longitud del punto 2
 * @returns {number} Distancia en metros
 */
function calcularDistanciaHaversine(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Radio de la Tierra en metros
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
}

/**
 * Obtiene el color basado en el nivel de congestión (ICV)
 * @param {number} icv - Índice de Congestión Vehicular (0-1)
 * @returns {string} Color hexadecimal
 */
function obtenerColorPorCongestion(icv) {
    if (icv < CONFIG.UMBRALES_ICV.FLUIDO) {
        return CONFIG.COLORES_CONGESTION.verde;
    } else if (icv < CONFIG.UMBRALES_ICV.MODERADO) {
        return CONFIG.COLORES_CONGESTION.amarillo;
    } else {
        return CONFIG.COLORES_CONGESTION.rojo;
    }
}

/**
 * Actualiza el color de los caminos según el estado de congestión
 * @param {Object} mapa - Instancia de Leaflet map
 * @param {Array} conexiones - Array de conexiones entre intersecciones
 * @param {Object} estadoIntersecciones - Estado actual de cada intersección con su ICV
 */
function actualizarColoresConexiones(mapa, conexiones, estadoIntersecciones) {
    conexiones.forEach(conexion => {
        if (!conexion.layer) return;

        // Obtener ICV promedio de las dos intersecciones conectadas
        const icvOrigen = estadoIntersecciones[conexion.origen]?.icv || 0;
        const icvDestino = estadoIntersecciones[conexion.destino]?.icv || 0;
        const icvPromedio = (icvOrigen + icvDestino) / 2;

        // Obtener color según congestión
        const color = obtenerColorPorCongestion(icvPromedio);

        // Actualizar color de la línea
        conexion.layer.setStyle({
            color: color,
            opacity: 0.7
        });
    });
}

console.log('✓ Módulo routing-utils.js cargado');

// Verificación de configuración
if (typeof CONFIG !== 'undefined') {
    console.log('✓ CONFIG disponible para routing-utils');
    if (CONFIG.MAPBOX_TOKEN && CONFIG.MAPBOX_TOKEN !== 'TU_TOKEN_MAPBOX_AQUI') {
        console.log('✓ Token de Mapbox configurado - Rutas reales habilitadas');
    } else {
        console.log('⚠️ Token de Mapbox no configurado - Usando modo fallback (líneas rectas)');
    }
} else {
    console.error('❌ CONFIG no está definido - Verifica el orden de carga de scripts');
}
