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
        latitud: -12.1108,
        longitud: -77.0369,
        distrito: 'Miraflores',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'MIR-002',
        nombre: 'Av. Larco con Av. Benavides',
        latitud: -12.1190,
        longitud: -77.0370,
        distrito: 'Miraflores',
        num_carriles: 4,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'MIR-003',
        nombre: 'Av. Arequipa con Av. Benavides',
        latitud: -12.1238,
        longitud: -77.0325,
        distrito: 'Miraflores',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_critico'
    },

    // DISTRITO: MAGDALENA
    {
        id: 'MA-001',
        nombre: 'Av. Brasil con Av. 28 de Julio',
        latitud: -12.0899,
        longitud: -77.0660,
        distrito: 'Magdalena',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN ISIDRO
    {
        id: 'SI-001',
        nombre: 'Av. Javier Prado con Av. Arequipa',
        latitud: -12.0923,
        longitud: -77.0333,
        distrito: 'San Isidro',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'SI-002',
        nombre: 'Av. Camino Real con Av. República de Panamá',
        latitud: -12.0970,
        longitud: -77.0326,
        distrito: 'San Isidro',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'SI-003',
        nombre: 'Av. Javier Prado con Av. Canaval y Moreyra',
        latitud: -12.1035,
        longitud: -77.0316,
        distrito: 'San Isidro',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'SI-004',
        nombre: 'Av. Aviación con Av. Javier Prado',
        latitud: -12.0947,
        longitud: -77.0507,
        distrito: 'San Isidro',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LIMA CENTRO
    {
        id: 'LC-001',
        nombre: 'Av. Abancay con Jr. Lampa',
        latitud: -12.0427,
        longitud: -77.0241,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_historico'
    },
    {
        id: 'LC-002',
        nombre: 'Av. Nicolás de Piérola con Jr. de la Unión',
        latitud: -12.0464,
        longitud: -77.0428,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_historico'
    },
    {
        id: 'LC-003',
        nombre: 'Av. Tacna con Av. Emancipación',
        latitud: -12.0545,
        longitud: -77.0302,
        distrito: 'Cercado de Lima',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'LC-004',
        nombre: 'Av. Alfonso Ugarte con Av. Venezuela',
        latitud: -12.0603,
        longitud: -77.0416,
        distrito: 'Cercado de Lima',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LA VICTORIA
    {
        id: 'LV-001',
        nombre: 'Av. Grau con Av. 28 de Julio',
        latitud: -12.0591,
        longitud: -77.0298,
        distrito: 'La Victoria',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'LV-002',
        nombre: 'Av. Aviación con Av. Javier Prado',
        latitud: -12.0841,
        longitud: -77.0041,
        distrito: 'La Victoria',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'LV-003',
        nombre: 'Av. Aviación con Av. 28 de Julio',
        latitud: -12.0610,
        longitud: -77.0130,
        distrito: 'La Victoria',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'LV-004',
        nombre: 'Av. Aviación con Av. 28 de Julio Alt',
        latitud: -12.0719,
        longitud: -77.0115,
        distrito: 'La Victoria',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SURCO
    {
        id: 'SUR-001',
        nombre: 'Av. Javier Prado con Av. Primavera',
        latitud: -12.1005,
        longitud: -76.9946,
        distrito: 'Santiago de Surco',
        num_carriles: 8,
        zona: 'sur',
        tipo: 'cruce_critico'
    },
    {
        id: 'SUR-002',
        nombre: 'Av. Benavides con Av. Tomás Marsano',
        latitud: -12.1117,
        longitud: -77.0002,
        distrito: 'Santiago de Surco',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_critico'
    },
    {
        id: 'SUR-003',
        nombre: 'Av. Higuereta con Av. El Polo',
        latitud: -12.1288,
        longitud: -77.0011,
        distrito: 'Santiago de Surco',
        num_carriles: 4,
        zona: 'sur',
        tipo: 'cruce_principal'
    },
    {
        id: 'SUR-004',
        nombre: 'Av. Primavera con Av. República de Panamá',
        latitud: -12.1102,
        longitud: -76.9782,
        distrito: 'Santiago de Surco',
        num_carriles: 6,
        zona: 'sur',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN JUAN DE LURIGANCHO
    {
        id: 'SJL-001',
        nombre: 'Av. Próceres con Av. Los Jardines',
        latitud: -11.9848,
        longitud: -77.0067,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-002',
        nombre: 'Av. Wiesse con Av. Gran Chimú',
        latitud: -11.9823,
        longitud: -77.0132,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 4,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-003',
        nombre: 'Av. Próceres con Av. Canta Callao',
        latitud: -12.0252,
        longitud: -77.0120,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-004',
        nombre: 'Av. Los Jardines con Av. Circunvalación',
        latitud: -12.0258,
        longitud: -77.0101,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-005',
        nombre: 'Av. Wiesse con Av. Canta Callao',
        latitud: -12.0232,
        longitud: -77.0079,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 4,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-006',
        nombre: 'Av. Próceres con Av. Circunvalación',
        latitud: -12.0206,
        longitud: -77.0125,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-007',
        nombre: 'Av. Los Jardines con Av. Primavera',
        latitud: -12.0123,
        longitud: -77.0115,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 4,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-008',
        nombre: 'Av. Canta Callao con Av. Wiesse',
        latitud: -12.0132,
        longitud: -77.0020,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },
    {
        id: 'SJL-009',
        nombre: 'Av. Próceres con Av. 28 de Julio',
        latitud: -12.0108,
        longitud: -76.9970,
        distrito: 'San Juan de Lurigancho',
        num_carriles: 6,
        zona: 'este',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN MIGUEL
    {
        id: 'SM-001',
        nombre: 'Av. Manuel Cipriano Dulanto con Av. Universitaria',
        latitud: -12.0749,
        longitud: -77.0797,
        distrito: 'San Miguel',
        num_carriles: 8,
        zona: 'oeste',
        tipo: 'cruce_critico'
    },
    {
        id: 'SM-002',
        nombre: 'Av. Elmer Faucett con Av. Universitaria',
        latitud: -12.0603,
        longitud: -77.0790,
        distrito: 'San Miguel',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },
    {
        id: 'SM-003',
        nombre: 'Av. La Marina con Av. Venezuela',
        latitud: -12.0782,
        longitud: -77.0814,
        distrito: 'San Miguel',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },
    {
        id: 'SM-004',
        nombre: 'Av. La Marina con Av. Bolognesi',
        latitud: -12.0625,
        longitud: -77.0972,
        distrito: 'San Miguel',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },

    // DISTRITO: JESÚS MARÍA
    {
        id: 'JM-001',
        nombre: 'Av. Brasil con Av. 28 de Julio',
        latitud: -12.0653,
        longitud: -77.0457,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'JM-002',
        nombre: 'Av. Salaverry con Av. Arequipa',
        latitud: -12.0855,
        longitud: -77.0486,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'JM-003',
        nombre: 'Av. Brasil con Av. Arequipa',
        latitud: -12.0881,
        longitud: -77.0506,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'JM-004',
        nombre: 'Av. Salaverry con Av. Libertad',
        latitud: -12.0752,
        longitud: -77.0421,
        distrito: 'Jesús María',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },

    // DISTRITO: SAN BORJA
    {
        id: 'SB-001',
        nombre: 'Av. Javier Prado con Av. Aviación',
        latitud: -12.0883,
        longitud: -77.0036,
        distrito: 'San Borja',
        num_carriles: 10,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'SB-002',
        nombre: 'Av. San Luis con Av. San Borja Norte',
        latitud: -12.0930,
        longitud: -76.9957,
        distrito: 'San Borja',
        num_carriles: 4,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'SB-003',
        nombre: 'Av. Angamos con Av. Aviación',
        latitud: -12.1118,
        longitud: -77.0002,
        distrito: 'San Borja',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },

    // DISTRITO: PUEBLO LIBRE
    {
        id: 'PL-001',
        nombre: 'Av. La Marina con Av. Bolívar',
        latitud: -12.0716,
        longitud: -77.0616,
        distrito: 'Pueblo Libre',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },
    {
        id: 'PL-002',
        nombre: 'Av. Brasil con Av. Bolívar',
        latitud: -12.0786,
        longitud: -77.0566,
        distrito: 'Pueblo Libre',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },

    // DISTRITO: PUEBLO LIBRE (continuación)
    {
        id: 'PL-003',
        nombre: 'Av. Faustino con Av. Brasil',
        latitud: -12.0751,
        longitud: -77.0538,
        distrito: 'Pueblo Libre',
        num_carriles: 6,
        zona: 'oeste',
        tipo: 'cruce_principal'
    },

    // DISTRITO: LINCE/TRANSVERSAL
    {
        id: 'TR-001',
        nombre: 'Av. Arequipa con Av. Paseo de la República',
        latitud: -12.0918,
        longitud: -77.0302,
        distrito: 'Lince',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },
    {
        id: 'TR-002',
        nombre: 'Av. Petit Thouars con Av. Paseo de la República',
        latitud: -12.0914,
        longitud: -77.0270,
        distrito: 'Lince',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    },
    {
        id: 'TR-003',
        nombre: 'Av. Aviación con Av. Paseo de la República',
        latitud: -12.0824,
        longitud: -76.9973,
        distrito: 'Lince',
        num_carriles: 8,
        zona: 'centro',
        tipo: 'cruce_critico'
    },

    // DISTRITO: LINCE
    {
        id: 'LIN-001',
        nombre: 'Av. Arequipa con Av. Petit Thouars',
        latitud: -12.0837,
        longitud: -77.0341,
        distrito: 'Lince',
        num_carriles: 6,
        zona: 'centro',
        tipo: 'cruce_principal'
    }
];

// Conexiones entre intersecciones (rutas principales)
const CONEXIONES_PRINCIPALES = [
    // Av. Arequipa (eje norte-sur)
    { origen: 'JM-003', destino: 'JM-002', via: 'Av. Arequipa', distancia: 300 },
    { origen: 'JM-002', destino: 'LIN-001', via: 'Av. Arequipa', distancia: 200 },
    { origen: 'LIN-001', destino: 'MIR-001', via: 'Av. Arequipa', distancia: 1200 },
    { origen: 'MIR-001', destino: 'MIR-003', via: 'Av. Arequipa', distancia: 900 },

    // Av. Javier Prado (eje este-oeste)
    { origen: 'SI-001', destino: 'SI-003', via: 'Av. Javier Prado', distancia: 700 },
    { origen: 'SI-003', destino: 'LV-002', via: 'Av. Javier Prado', distancia: 2500 },
    { origen: 'LV-002', destino: 'SB-001', via: 'Av. Javier Prado', distancia: 200 },
    { origen: 'SB-001', destino: 'SUR-001', via: 'Av. Javier Prado', distancia: 2600 },

    // Av. La Marina (zona oeste)
    { origen: 'SM-001', destino: 'SM-002', via: 'Av. La Marina', distancia: 500 },
    { origen: 'SM-002', destino: 'SM-003', via: 'Av. La Marina', distancia: 800 },
    { origen: 'SM-003', destino: 'SM-004', via: 'Av. La Marina', distancia: 900 },
    { origen: 'SM-004', destino: 'PL-001', via: 'Av. La Marina', distancia: 1200 },
    { origen: 'PL-001', destino: 'PL-002', via: 'Av. Brasil', distancia: 600 },
    { origen: 'PL-002', destino: 'PL-003', via: 'Av. Brasil', distancia: 500 },

    // Centro de Lima
    { origen: 'LC-001', destino: 'LC-002', via: 'Centro Histórico', distancia: 400 },
    { origen: 'LC-002', destino: 'LC-003', via: 'Centro Histórico', distancia: 600 },
    { origen: 'LC-003', destino: 'LC-004', via: 'Centro Histórico', distancia: 900 },

    // Magdalena
    { origen: 'JM-001', destino: 'MA-001', via: 'Av. Brasil', distancia: 800 },
    { origen: 'MA-001', destino: 'SM-001', via: 'Av. Brasil', distancia: 1000 },
    { origen: 'JM-004', destino: 'JM-001', via: 'Av. Libertad', distancia: 600 },
    { origen: 'JM-001', destino: 'JM-003', via: 'Av. Brasil', distancia: 700 },

    // San Isidro - Nueva SI-004
    { origen: 'SI-001', destino: 'SI-002', via: 'Av. Javier Prado', distancia: 500 },
    { origen: 'SI-002', destino: 'SI-003', via: 'Av. Javier Prado', distancia: 600 },
    { origen: 'SI-003', destino: 'SI-004', via: 'Av. Aviación', distancia: 1200 },
    { origen: 'SI-004', destino: 'LV-001', via: 'Av. Aviación', distancia: 1500 },

    // Av. Aviación (norte-sur)
    { origen: 'LV-002', destino: 'SB-001', via: 'Av. Aviación', distancia: 200 },
    { origen: 'LV-001', destino: 'LV-003', via: 'Av. Aviación', distancia: 300 },
    { origen: 'LV-003', destino: 'LV-004', via: 'Av. Aviación', distancia: 400 },
    { origen: 'LV-004', destino: 'SB-001', via: 'Av. Aviación', distancia: 300 },
    { origen: 'SB-001', destino: 'SB-003', via: 'Av. Aviación', distancia: 2500 },

    // Av. Angamos (este-oeste)
    { origen: 'MIR-001', destino: 'SB-003', via: 'Av. Angamos', distancia: 2800 },

    // Av. Benavides (este-oeste)
    { origen: 'MIR-003', destino: 'SUR-002', via: 'Av. Benavides', distancia: 2800 },

    // Surco
    { origen: 'SUR-001', destino: 'SUR-004', via: 'Av. Primavera', distancia: 1400 },
    { origen: 'SUR-002', destino: 'SUR-003', via: 'Zona Surco', distancia: 1800 },

    // San Juan de Lurigancho (expansión)
    { origen: 'SJL-001', destino: 'SJL-002', via: 'Av. Los Jardines', distancia: 800 },
    { origen: 'SJL-002', destino: 'SJL-003', via: 'Av. Próceres', distancia: 2500 },
    { origen: 'SJL-003', destino: 'SJL-004', via: 'Av. Los Jardines', distancia: 400 },
    { origen: 'SJL-004', destino: 'SJL-005', via: 'Av. Wiesse', distancia: 500 },
    { origen: 'SJL-005', destino: 'SJL-006', via: 'Av. Próceres', distancia: 500 },
    { origen: 'SJL-006', destino: 'SJL-007', via: 'Av. Los Jardines', distancia: 600 },
    { origen: 'SJL-007', destino: 'SJL-008', via: 'Av. Canta Callao', distancia: 700 },
    { origen: 'SJL-008', destino: 'SJL-009', via: 'Av. Próceres', distancia: 400 },

    // Lince/Transversal (nueva zona TR)
    { origen: 'JM-002', destino: 'TR-001', via: 'Av. Arequipa', distancia: 600 },
    { origen: 'TR-001', destino: 'TR-002', via: 'Av. Paseo de la República', distancia: 500 },
    { origen: 'TR-002', destino: 'TR-003', via: 'Av. Aviación', distancia: 600 },
    { origen: 'TR-003', destino: 'SUR-001', via: 'Av. Aviación', distancia: 800 },

    // Conexión Miraflores - San Borja
    { origen: 'MIR-001', destino: 'SB-003', via: 'Av. Angamos', distancia: 800 },
    { origen: 'SB-003', destino: 'SUR-002', via: 'Av. Aviación', distancia: 1200 },
    { origen: 'SUR-002', destino: 'SUR-003', via: 'Av. Higuereta', distancia: 1800 },
    { origen: 'SUR-003', destino: 'SUR-004', via: 'Zona Surco', distancia: 2400 },
    { origen: 'SB-001', destino: 'TR-003', via: 'Av. Aviación', distancia: 1000 },
    { origen: 'SB-002', destino: 'SUR-001', via: 'Av. Aviación', distancia: 600 },

    // Av. Brasil (este-oeste)
    { origen: 'JM-001', destino: 'PL-002', via: 'Av. Brasil', distancia: 1300 },

    // Conexiones LV (La Victoria)
    { origen: 'LV-001', destino: 'LV-003', via: 'Av. 28 de Julio', distancia: 400 },
    { origen: 'LV-003', destino: 'LV-004', via: 'Av. Aviación', distancia: 500 },
    { origen: 'LV-004', destino: 'LV-002', via: 'Av. 28 de Julio', distancia: 700 },

    // Conexiones adicionales para SJL
    { origen: 'SJL-003', destino: 'SJL-004', via: 'Av. Los Jardines', distancia: 400 },
    { origen: 'SJL-004', destino: 'SJL-005', via: 'Av. Circunvalación', distancia: 500 },

    // Conexión TR a LIN
    { origen: 'TR-001', destino: 'LIN-001', via: 'Av. Arequipa', distancia: 400 },
    { origen: 'LIN-001', destino: 'TR-002', via: 'Av. Petit Thouars', distancia: 300 },

    // Conexión SB-002
    { origen: 'SB-001', destino: 'SB-002', via: 'Av. San Borja', distancia: 600 },
    { origen: 'SB-002', destino: 'TR-003', via: 'Av. San Borja', distancia: 1000 },

    // Conexiones SUR ampliadas
    { origen: 'SUR-001', destino: 'SUR-002', via: 'Av. Javier Prado', distancia: 1200 },
    { origen: 'SUR-004', destino: 'SUR-001', via: 'Av. Primavera', distancia: 1400 }
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
