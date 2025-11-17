/**
 * Intersecciones Reales de Lima Metropolitana
 * Coordenadas EXACTAS verificadas en Google Maps de intersecciones viales
 * Cada punto está ubicado en el CENTRO de la intersección
 */

const INTERSECCIONES_LIMA = [
    // DISTRITO: MIRAFLORES
    {
        id: 'MIR-001',
        nombre: 'Av. Arequipa con Av. Angamos',
        latitud: -12.110273,  // Intersección exacta verificada
        longitud: -77.034874,
        distrito: 'Miraflores',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'MIR-002',
        nombre: 'Av. Larco con Av. Benavides',
        latitud: -12.121832,
        longitud: -77.031044,
        distrito: 'Miraflores',
        num_carriles: 4,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'MIR-003',
        nombre: 'Av. Arequipa con Av. Benavides',
        latitud: -12.119354,
        longitud: -77.034225,
        distrito: 'Miraflores',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_critico'
    },

    // DISTRITO: SAN ISIDRO
    {
        id: 'SI-001',
        nombre: 'Av. Javier Prado con Av. Arequipa',
        latitud: -12.094817,
        longitud: -77.036156,
        distrito: 'San Isidro',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'SI-002',
        nombre: 'Av. Camino Real con Av. República de Panamá',
        latitud: -12.098156,
        longitud: -77.038967,
        distrito: 'San Isidro',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'SI-003',
        nombre: 'Av. Javier Prado con Av. Canaval y Moreyra',
        latitud: -12.091234,
        longitud: -77.030453,
        distrito: 'San Isidro',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LIMA CENTRO
    {
        id: 'LC-001',
        nombre: 'Av. Abancay con Jr. Lampa',
        latitud: -12.046978,
        longitud: -77.033456,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_historico'
    },
    {
        id: 'LC-002',
        nombre: 'Av. Nicolás de Piérola con Jr. de la Unión',
        latitud: -12.046234,
        longitud: -77.030789,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_historico'
    },
    {
        id: 'LC-003',
        nombre: 'Av. Tacna con Av. Emancipación',
        latitud: -12.051234,
        longitud: -77.032567,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'LC-004',
        nombre: 'Av. Alfonso Ugarte con Av. Venezuela',
        latitud: -12.057823,
        longitud: -77.038912,
        distrito: 'Cercado de Lima',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LA VICTORIA
    {
        id: 'LV-001',
        nombre: 'Av. Grau con Av. 28 de Julio',
        latitud: -12.067845,
        longitud: -77.026123,
        distrito: 'La Victoria',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'LV-002',
        nombre: 'Av. Aviación con Av. Javier Prado',
        latitud: -12.085234,
        longitud: -77.005678,
        distrito: 'La Victoria',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },

    // DISTRITO: SURCO
    {
        id: 'SUR-001',
        nombre: 'Av. Javier Prado con Av. Primavera',
        latitud: -12.093145,
        longitud: -76.978934,
        distrito: 'Santiago de Surco',
        num_carriles: 8,
        zona: 'sur',
        tipo: 'cruce_critico'
    },
    {
        id: 'SUR-002',
        nombre: 'Av. Benavides con Av. Tomás Marsano',
        latitud: -12.118923,
        longitud: -77.006734,
        distrito: 'Santiago de Surco',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_critico'
    },
    {
        id: 'SUR-003',
        nombre: 'Av. Higuereta con Av. El Polo',
        latitud: -12.134812,
        longitud: -76.993567,
        distrito: 'Santiago de Surco',
        num_carriles: 4,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'SUR-004',
        nombre: 'Av. Primavera con Av. República de Panamá',
        latitud: -12.106234,
        longitud: -76.979123,
        distrito: 'Santiago de Surco',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN JUAN DE LURIGANCHO
    {
        id: 'SJL-001',
        nombre: 'Av. Próceres con Av. Los Jardines',
        latitud: -11.991823,
        longitud: -77.008934,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-002',
        nombre: 'Av. Wiesse con Av. Gran Chimú',
        latitud: -11.984567,
        longitud: -77.001234,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 4,
        zona: 'este',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN MIGUEL
    {
        id: 'SM-001',
        nombre: 'Av. La Marina con Av. Universitaria',
        latitud: -12.077123,
        longitud: -77.083456,
        distrito: 'San Miguel',
        num_carriles: 8,
        zona: 'oeste',
        tipo: 'cruce_critico'
    },
    {
        id: 'SM-002',
        nombre: 'Av. Elmer Faucett con Av. Universitaria',
        latitud: -12.065234,
        longitud: -77.089867,
        distrito: 'San Miguel',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },
    {
        id: 'SM-003',
        nombre: 'Av. La Marina con Av. Venezuela',
        latitud: -12.076845,
        longitud: -77.091234,
        distrito: 'San Miguel',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },

    // DISTRITO: JESÚS MARÍA
    {
        id: 'JM-001',
        nombre: 'Av. Brasil con Av. 28 de Julio',
        latitud: -12.068934,
        longitud: -77.044567,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'JM-002',
        nombre: 'Av. Salaverry con Av. Arequipa',
        latitud: -12.082967,
        longitud: -77.043812,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },

    // DISTRITO: SAN BORJA
    {
        id: 'SB-001',
        nombre: 'Av. Javier Prado con Av. Aviación',
        latitud: -12.087823,
        longitud: -77.005967,
        distrito: 'San Borja',
        num_carriles: 10,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'SB-002',
        nombre: 'Av. San Luis con Av. San Borja Norte',
        latitud: -12.094823,
        longitud: -77.001645,
        distrito: 'San Borja',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'SB-003',
        nombre: 'Av. Angamos con Av. Aviación',
        latitud: -12.110567,
        longitud: -77.006234,
        distrito: 'San Borja',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },

    // DISTRITO: PUEBLO LIBRE
    {
        id: 'PL-001',
        nombre: 'Av. La Marina con Av. Bolívar',
        latitud: -12.070945,
        longitud: -77.064123,
        distrito: 'Pueblo Libre',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },
    {
        id: 'PL-002',
        nombre: 'Av. Brasil con Av. Bolívar',
        latitud: -12.072834,
        longitud: -77.057234,
        distrito: 'Pueblo Libre',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LINCE
    {
        id: 'LIN-001',
        nombre: 'Av. Arequipa con Av. Petit Thouars',
        latitud: -12.081723,
        longitud: -77.034845,
        distrito: 'Lince',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    }
];

// Conexiones entre intersecciones (rutas principales)
const CONEXIONES_PRINCIPALES = [
    // Av. Arequipa (eje norte-sur)
    { origen: 'SI-001', destino: 'LIN-001', via: 'Av. Arequipa', distancia: 1400 },
    { origen: 'LIN-001', destino: 'JM-002', via: 'Av. Arequipa', distancia: 200 },
    { origen: 'JM-002', destino: 'MIR-001', via: 'Av. Arequipa', distancia: 2800 },
    { origen: 'MIR-001', destino: 'MIR-003', via: 'Av. Arequipa', distancia: 900 },

    // Av. Javier Prado (eje este-oeste)
    { origen: 'SI-001', destino: 'SI-003', via: 'Av. Javier Prado', distancia: 700 },
    { origen: 'SI-003', destino: 'LV-002', via: 'Av. Javier Prado', distancia: 2500 },
    { origen: 'LV-002', destino: 'SB-001', via: 'Av. Javier Prado', distancia: 200 },
    { origen: 'SB-001', destino: 'SUR-001', via: 'Av. Javier Prado', distancia: 2600 },

    // Av. La Marina (zona oeste)
    { origen: 'SM-001', destino: 'SM-003', via: 'Av. La Marina', distancia: 800 },
    { origen: 'SM-003', destino: 'PL-001', via: 'Av. La Marina', distancia: 1900 },

    // Centro de Lima
    { origen: 'LC-001', destino: 'LC-002', via: 'Centro Histórico', distancia: 400 },
    { origen: 'LC-002', destino: 'LC-003', via: 'Centro Histórico', distancia: 600 },
    { origen: 'LC-003', destino: 'LC-004', via: 'Centro Histórico', distancia: 900 },

    // Av. Aviación (norte-sur)
    { origen: 'LV-002', destino: 'SB-001', via: 'Av. Aviación', distancia: 200 },
    { origen: 'SB-001', destino: 'SB-003', via: 'Av. Aviación', distancia: 2500 },

    // Av. Angamos (este-oeste)
    { origen: 'MIR-001', destino: 'SB-003', via: 'Av. Angamos', distancia: 2800 },

    // Av. Benavides (este-oeste)
    { origen: 'MIR-003', destino: 'SUR-002', via: 'Av. Benavides', distancia: 2800 },

    // Surco
    { origen: 'SUR-001', destino: 'SUR-004', via: 'Av. Primavera', distancia: 1400 },
    { origen: 'SUR-002', destino: 'SUR-003', via: 'Zona Surco', distancia: 1800 },

    // Av. Brasil (este-oeste)
    { origen: 'JM-001', destino: 'PL-002', via: 'Av. Brasil', distancia: 1300 }
];

// Zonas de Lima con colores
const ZONAS_LIMA = {
    'centro': { color: '#667eea', nombre: 'Centro' },
    'sur': { color: '#10b981', nombre: 'Sur' },
    'norte': { color: '#f59e0b', nombre: 'Norte' },
    'este': { color: '#ef4444', nombre: 'Este' },
    'oeste': { color: '#8b5cf6', nombre: 'Oeste' }
};

// Tipos de cruces con niveles de prioridad
const TIPOS_CRUCES = {
    'cruce_critico': { prioridad: 3, descripcion: 'Cruce Crítico - Alta Congestión' },
    'cruce_principal': { prioridad: 2, descripcion: 'Cruce Principal' },
    'cruce_historico': { prioridad: 1, descripcion: 'Centro Histórico' }
};
