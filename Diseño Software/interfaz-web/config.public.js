/**
 * Configuración pública del frontend.
 *
 * Un token de Mapbox puede definirse antes de cargar este archivo mediante
 * `window.MAPBOX_TOKEN`. Si no se configura, el ruteo usa OSRM como respaldo.
 */
(function (global) {
    'use strict';

    const tokenMapbox = typeof global.MAPBOX_TOKEN === 'string' && global.MAPBOX_TOKEN.trim()
        ? global.MAPBOX_TOKEN.trim()
        : 'TU_TOKEN_MAPBOX_AQUI';

    global.CONFIG = Object.freeze({
        MAPBOX_TOKEN: tokenMapbox,
        MAPBOX_DIRECTIONS_API: 'https://api.mapbox.com/directions/v5/mapbox',
        DRIVING_PROFILE: 'driving',
        UMBRALES_ICV: Object.freeze({
            FLUIDO: 0.30,
            MODERADO: 0.60
        }),
        COLORES_CONGESTION: Object.freeze({
            verde: '#10b981',
            amarillo: '#f59e0b',
            rojo: '#ef4444'
        })
    });
})(window);
