/**
 * Sistema de Control Semafórico - JavaScript Mejorado y Funcional
 * Dashboard interactivo con datos reales de Lima
 */

// ==================== CONFIGURACIÓN ====================
const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// ==================== ESTADO GLOBAL ====================
const estado = {
    mapa: null,
    marcadores: {},
    lineas: [],
    callesSUMO: null,  // Layer de calles SUMO
    callesGeoJSON: null,  // Datos GeoJSON de calles
    websocket: null,
    backendConectado: false,  // Flag para saber si el backend está enviando datos
    intersecciones: [],
    olaVerdeActiva: null,
    timeoutOlaVerde: null,  // Timeout para desactivación automática
    marcadoresOlaVerde: [],  // Marcadores de la ola verde
    chartICV: null,
    chartFlujo: null,
    estadisticas: {
        flujoTotal: 0,
        contadorActualizaciones: 0,
        tiempoInicio: Date.now()
    },
    // Establecer modo por defecto para evitar que quede vacío y no arranque
    modoActual: 'simulador',
    simulacionInterval: null,
    actualizacionTraficoInterval: null,
    capaTrafico: null,  // Layer group para calles con tráfico
    datosTrafico: {},  // Datos de tráfico por conexión
    mostrarSUMOTrafico: false // Control para ocultar visualización de tráfico SUMO
    ,metricasSUMOResumen: null  // Resumen global de SUMO para sesgo en simulador
    ,__proxSUMOCache: {} // cache de proximidad por intersección
    ,__hudSUMO: null // control HUD con totales
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('%c=== SISTEMA DE CONTROL SEMAFÓRICO ===', 'color: #10b981; font-size: 16px; font-weight: bold;');
    console.log('Inicializando sistema...');

    try {
        // Verificar dependencias críticas
        const dependencias = {
            'Chart.js': typeof Chart !== 'undefined',
            'Particles': typeof particlesJS !== 'undefined',
            'INTERSECCIONES_LIMA': typeof INTERSECCIONES_LIMA !== 'undefined',
            'ZONAS_LIMA': typeof ZONAS_LIMA !== 'undefined'
        };

        Object.entries(dependencias).forEach(([nombre, cargado]) => {
            if (!cargado) {
                console.error(`❌ ${nombre} NO CARGADO`);
            } else {
            }
        });

        console.log('Iniciando mapa...');
        inicializarMapa();
        inicializarGraficos();

        console.log('Cargando intersecciones...');
        cargarInterseccionesReales();

        console.log('Configurando eventos...');
        configurarEventListeners();

        console.log('Conectando WebSocket...');
        conectarWebSocket();  // CRITICO: Conectar WebSocket para recibir actualizaciones

        // Importante: NO iniciar simulación local automáticamente.
        // La simulación solo debe correr cuando el usuario elija modo 'simulador'.

        // DEMO RÁPIDA: iniciar simulación local inmediata en modo simulador
        // para asegurar que "prenda" incluso sin backend.
        estado.modoActual = 'simulador';
        iniciarSimulacion();

        console.log('%c✓ Sistema inicializado correctamente', 'color: #10b981; font-weight: bold;');
    } catch (error) {
        console.error('%c❌ ERROR en la inicialización:', 'color: #ef4444; font-weight: bold;', error);
        alert('Error al inicializar el sistema. Revisa la consola del navegador (F12) para más detalles.');
    }
});

// ==================== PARTÍCULAS DE FONDO ====================
function inicializarParticulas() {
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            particles: {
                number: { value: 60, density: { enable: true, value_area: 800 } },
                color: { value: '#ffffff' },
                shape: { type: 'circle' },
                opacity: {
                    value: 0.3,
                    random: true,
                    anim: { enable: true, speed: 0.5, opacity_min: 0.05, sync: false }
                },
                size: {
                    value: 2,
                    random: true,
                    anim: { enable: true, speed: 1, size_min: 0.1, sync: false }
                },
                line_linked: {
                    enable: true,
                    distance: 120,
                    color: '#ffffff',
                    opacity: 0.15,
                    width: 1
                },
                move: {
                    enable: true,
                    speed: 1,
                    direction: 'none',
                    random: false,
                    straight: false,
                    out_mode: 'out',
                    bounce: false
                }
            },
            interactivity: {
                detect_on: 'canvas',
                events: {
                    onhover: { enable: true, mode: 'grab' },
                    onclick: { enable: false },
                    resize: true
                },
                modes: {
                    grab: { distance: 140, line_linked: { opacity: 0.5 } }
                }
            },
            retina_detect: true
        });
        console.log('Particulas inicializadas');
    }
}

// ==================== MAPA ====================
function inicializarMapa() {
    // Verificar que Leaflet esté cargado
    if (typeof L === 'undefined') {
        console.error('Leaflet no está cargado. El mapa no se mostrará.');
        return;
    }

    const centroLima = [-12.0464, -77.0428];

    estado.mapa = L.map('mapa', {
        zoomControl: true,
        attributionControl: false
    }).setView(centroLima, 13);

    // Mapa claro estándar
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(estado.mapa);

    // Configurar modo de obtener coordenadas
    setupMapClickForCoords();

    console.log('Mapa inicializado');
}

function agregarMarcadorInterseccion(interseccion) {
    const colorZona = ZONAS_LIMA[interseccion.zona].color;

    // Marcador con etiqueta de ID
    const icono = L.divIcon({
        html: `<div class="marcador-container">
                   <div class="marcador-semaforo" data-zona="${interseccion.zona}" data-interseccion="${interseccion.id}">
                       <div class="semaforo-luz luz-activa" id="luz-${interseccion.id}"></div>
                   </div>
                   <div class="marcador-label">${interseccion.id}</div>
               </div>`,
        className: '',
        iconSize: [40, 40],
        iconAnchor: [20, 35]
    });

    const marcador = L.marker([interseccion.latitud, interseccion.longitud], {
        icon: icono
    }).addTo(estado.mapa);

    marcador.bindPopup(`
        <div class="popup-profesional">
            <div class="popup-header" style="background: ${colorZona};">
                <i class="fas fa-traffic-light"></i>
                <strong>${interseccion.nombre}</strong>
            </div>
            <div class="popup-body">
                <div class="popup-row">
                    <span class="popup-label">ID:</span>
                    <span class="popup-value">${interseccion.id}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Distrito:</span>
                    <span class="popup-value">${interseccion.distrito}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Carriles:</span>
                    <span class="popup-value">${interseccion.num_carriles}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Zona:</span>
                    <span class="popup-value">${ZONAS_LIMA[interseccion.zona].nombre}</span>
                </div>
            </div>
        </div>
    `);

    estado.marcadores[interseccion.id] = marcador;
    // Log para debugging
    if (interseccion.id.includes('LV-') || interseccion.id.includes('SJL-')) {
        console.log(`✓ Marcador creado para ${interseccion.id}`);
    }
}

async function dibujarConexiones() {
    // Limpiar líneas existentes
    estado.lineas.forEach(linea => estado.mapa.removeLayer(linea));
    estado.lineas = [];

    console.log(`📍 Dibujando ${CONEXIONES_PRINCIPALES.length} conexiones...`);

    // Procesar conexiones en serie (para mejor control y caché)
    for (const conexion of CONEXIONES_PRINCIPALES) {
        const origen = INTERSECCIONES_LIMA.find(i => i.id === conexion.origen);
        const destino = INTERSECCIONES_LIMA.find(i => i.id === conexion.destino);

        if (!origen || !destino) {
            console.warn(`No se encontró origen o destino para: ${conexion.origen} -> ${conexion.destino}`);
            continue;
        }

        // Intentar obtener ruta real usando Mapbox
        const inicioCoords = [origen.latitud, origen.longitud];
        const finCoords = [destino.latitud, destino.longitud];

        let coordenadasRuta;

        try {
            const ruta = await obtenerRutaMapbox(inicioCoords, finCoords, 'driving');

            if (ruta && ruta.geometry && ruta.geometry.coordinates) {
                // Convertir de [lng, lat] (GeoJSON) a [lat, lng] (Leaflet)
                coordenadasRuta = ruta.geometry.coordinates.map(
                    coord => [coord[1], coord[0]]
                );
            } else {
                // Fallback: línea recta si falla Mapbox
                coordenadasRuta = [inicioCoords, finCoords];
            }
        } catch (error) {
            // En caso de error, usar línea recta
            console.warn(`Error obteniendo ruta para ${conexion.via}, usando línea recta`);
            coordenadasRuta = [inicioCoords, finCoords];
        }

        // Dibujar la conexión con estilo sólido
        const linea = L.polyline(coordenadasRuta, {
            color: '#6b7280',  // Color gris por defecto
            weight: 4.5,  // Línea grosor medio entre 3 y 6
            opacity: 0.7,
            lineCap: 'round',
            lineJoin: 'round'
            // SIN dashArray - línea sólida
        }).addTo(estado.mapa);

        // Tooltip mejorado con velocidad promedio
        linea.bindTooltip(
            `<strong>${conexion.via}</strong><br>` +
            `<small>Estado: cargando...</small><br>` +
            `<small>ICV: 0.00</small><br>` +
            `<small>Velocidad: 0 km/h</small>`,
            {
                permanent: false,
                direction: 'center',
                className: 'tooltip-ruta'
            }
        );

        // Almacenar información de la conexión para actualizaciones posteriores
        estado.lineas.push(linea);
        
        // Guardar referencia de conexión con datos
        if (!estado.conexionesMap) {
            estado.conexionesMap = {};
        }
        
        const conexionKey = `${conexion.origen}-${conexion.destino}`;
        estado.conexionesMap[conexionKey] = {
            layer: linea,
            origen: conexion.origen,
            destino: conexion.destino,
            via: conexion.via,
            coordenadas: coordenadasRuta
        };
    }

    console.log(`✅ ${estado.lineas.length} conexiones dibujadas`);
}

/**
 * Actualiza colores y tooltips de las líneas de conexión según ICV
 * @param {Array} metricas - Array con métricas de intersecciones
 */
function actualizarColoresConexionesSegunICV(metricas) {
    if (!estado.conexionesMap || Object.keys(estado.conexionesMap).length === 0) {
        return;
    }

    // Crear mapa de ICV y velocidad por intersección
    const icvPorInterseccion = {};
    const velocidadPorInterseccion = {};
    
    metricas.forEach(metrica => {
        icvPorInterseccion[metrica.interseccion_id] = metrica.icv;
        velocidadPorInterseccion[metrica.interseccion_id] = metrica.velocidad || 0;
    });

    // Actualizar cada conexión
    Object.values(estado.conexionesMap).forEach(conexion => {
        const icvOrigen = icvPorInterseccion[conexion.origen] || 0;
        const icvDestino = icvPorInterseccion[conexion.destino] || 0;
        const velocidadOrigen = velocidadPorInterseccion[conexion.origen] || 0;
        const velocidadDestino = velocidadPorInterseccion[conexion.destino] || 0;

        // Promedios
        const icvPromedio = (icvOrigen + icvDestino) / 2;
        const velocidadPromedio = (velocidadOrigen + velocidadDestino) / 2;

        // Determinar color según ICV
        let color, clasificacion;
        if (icvPromedio < 0.3) {
            color = '#10b981'; // Verde - Fluido
            clasificacion = 'Fluido';
        } else if (icvPromedio < 0.6) {
            color = '#f59e0b'; // Amarillo - Moderado
            clasificacion = 'Moderado';
        } else {
            color = '#ef4444'; // Rojo - Congestionado
            clasificacion = 'Congestionado';
        }

        // Actualizar estilo de la línea
        conexion.layer.setStyle({
            color: color,
            opacity: 0.7
        });

        // Actualizar tooltip con ICV y velocidad promedio
        conexion.layer.setTooltipContent(
            `<strong>${conexion.via}</strong><br>` +
            `<small>Estado: ${clasificacion}</small><br>` +
            `<small>ICV: ${icvPromedio.toFixed(2)}</small><br>` +
            `<small>Velocidad: ${Math.round(velocidadPromedio)} km/h</small>`
        );
    });
}

function actualizarColorMarcador(interseccionId, icv) {
    const marcador = estado.marcadores[interseccionId];
    if (!marcador) {
        if (interseccionId.includes('LV-') || interseccionId.includes('SJL-')) {
            console.warn(`⚠ NO EXISTE MARCADOR para ${interseccionId}`);
        }
        return;
    }

    // Determinar color según ICV
    let colorLuz;
    if (icv < 0.3) {
        colorLuz = '#10b981'; // Verde
    } else if (icv < 0.6) {
        colorLuz = '#f59e0b'; // Amarillo
    } else {
        colorLuz = '#ef4444'; // Rojo
    }

    const interseccion = INTERSECCIONES_LIMA.find(i => i.id === interseccionId);
    if (!interseccion) return;

    const icono = L.divIcon({
        html: `<div class="marcador-container">
                   <div class="marcador-semaforo pulsing" data-zona="${interseccion.zona}">
                       <div class="semaforo-luz luz-activa" style="background: ${colorLuz}; box-shadow: 0 0 15px ${colorLuz};"></div>
                   </div>
                   <div class="marcador-label">${interseccionId}</div>
               </div>`,
        className: '',
        iconSize: [40, 40],
        iconAnchor: [20, 35]
    });

    marcador.setIcon(icono);
}

// ==================== GRÁFICOS ====================
function inicializarGraficos() {
    // Verificar que Chart.js esté cargado
    if (typeof Chart === 'undefined') {
        console.error('Chart.js no está cargado. Los gráficos no se mostrarán.');
        return;
    }

    const configComun = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: '#f1f5f9',
                    font: { size: 13, weight: '600' },
                    padding: 15
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.08)' },
                ticks: {
                    color: '#cbd5e1',
                    font: { size: 12, weight: '500' }
                }
            },
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.08)' },
                ticks: {
                    color: '#cbd5e1',
                    maxRotation: 0,
                    font: { size: 12, weight: '500' }
                }
            }
        }
    };

    // Gráfico de ICV
    const ctxICV = document.getElementById('chartICV').getContext('2d');
    estado.chartICV = new Chart(ctxICV, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'ICV Promedio',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...configComun,
            scales: {
                ...configComun.scales,
                y: {
                    ...configComun.scales.y,
                    max: 1,
                    ticks: {
                        ...configComun.scales.y.ticks,
                        callback: (value) => value.toFixed(2)
                    }
                }
            }
        }
    });

    // Gráfico de Flujo
    const ctxFlujo = document.getElementById('chartFlujo').getContext('2d');
    estado.chartFlujo = new Chart(ctxFlujo, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Flujo (veh/min)',
                data: [],
                backgroundColor: 'rgba(16, 185, 129, 0.6)',
                borderColor: '#10b981',
                borderWidth: 1
            }]
        },
        options: configComun
    });

    console.log('Gráficos inicializados');
}

// FUNCIÓN OBSOLETA - La lógica está ahora integrada en actualizarDatosInterfaz()
// Se mantiene por compatibilidad pero ya no se usa
function actualizarGraficos(icvPromedio, flujoPromedio) {
    if (!estado.chartICV || !estado.chartFlujo) return; // Verificar que existan

    // En modo simulador, asegurar límites del ICV promedio [0.50, 0.60]
    if (estado.modoActual === 'simulador') {
        icvPromedio = Math.max(0.50, Math.min(0.60, icvPromedio || 0));
    }

    const timestamp = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });

    // Actualizar gráfico ICV
    estado.chartICV.data.labels.push(timestamp);
    estado.chartICV.data.datasets[0].data.push(icvPromedio);

    if (estado.chartICV.data.labels.length > 15) {
        estado.chartICV.data.labels.shift();
        estado.chartICV.data.datasets[0].data.shift();
    }

    estado.chartICV.update('none');

    // Actualizar gráfico Flujo
    estado.chartFlujo.data.labels.push(timestamp);
    estado.chartFlujo.data.datasets[0].data.push(flujoPromedio);

    if (estado.chartFlujo.data.labels.length > 15) {
        estado.chartFlujo.data.labels.shift();
        estado.chartFlujo.data.datasets[0].data.shift();
    }

    estado.chartFlujo.update('none');
}

// ==================== CARGA DE DATOS ====================
function cargarInterseccionesReales() {
    console.log('Cargando intersecciones reales de Lima...');

    estado.intersecciones = INTERSECCIONES_LIMA;

    // Debug: Mostrar coordenadas de intersecciones con nombres cortos
    const interseccionesCortas = estado.intersecciones.filter(i => 
        ['LIN-001', 'LV-001', 'LV-002', 'SM-001', 'SM-002', 'SM-003', 'JM-001', 'JM-002', 'SB-001', 'SB-002', 'SB-003', 'PL-001', 'PL-002'].includes(i.id)
    );
    
    if (interseccionesCortas.length > 0) {
        console.log('%c📍 INTERSECCIONES CON NOMBRES CORTOS CARGADAS:', 'color: #10b981; font-weight: bold;');
        interseccionesCortas.forEach(inter => {
            console.log(`  ${inter.id}: [${inter.latitud}, ${inter.longitud}] - ${inter.nombre}`);
        });
    }

    // Agregar marcadores
    estado.intersecciones.forEach(inter => {
        agregarMarcadorInterseccion(inter);
    });

    // Dibujar conexiones (líneas engrosadas entre intersecciones)
    dibujarConexiones();

    // Actualizar contador
    document.getElementById('num-intersecciones').textContent = estado.intersecciones.length;

    // Llenar selects
    llenarSelectsEmergencia();

    // Llenar selector de cámara para modo simulador
    cargarInterseccionesSimulador();

    console.log(`${estado.intersecciones.length} intersecciones cargadas`);
}

// ==================== SIMULACIÓN ====================
function iniciarSimulacion() {
    if (estado.simulacionInterval) {
        clearInterval(estado.simulacionInterval);
    }

    console.log('Simulación LOCAL iniciada - Usando datos aleatorios generados en el navegador');

    // Actualizar cada 3 segundos
    estado.simulacionInterval = setInterval(() => {
        const metricasSimuladas = generarMetricasSimuladas();
        actualizarMetricas(metricasSimuladas);
    }, 3000);

    // Primera actualización inmediata
    const metricasSimuladas = generarMetricasSimuladas();
    actualizarMetricas(metricasSimuladas);

    // Iniciar visualización de tráfico en el mapa
    if (!estado.actualizacionTraficoInterval) {
        iniciarActualizacionTrafico();
    }
}

function generarMetricasSimuladas() {
    const hora = new Date().getHours();

    // Perfil horario (0–1): picos moderan sin saturar todo
    let perfilHora = 0.5; // base media
    if ((hora >= 7 && hora <= 9) || (hora >= 17 && hora <= 19)) perfilHora = 0.65; // pico más moderado
    else if (hora >= 22 || hora <= 5) perfilHora = 0.25; // valle nocturno

    // Para suavizar cambios entre ticks conservamos última métrica si existe
    if (!estado.__cacheSim) estado.__cacheSim = {}; // { id: { icv, flujo, velocidad, cola } }

    // Historial para control de saturación del promedio
    if (!estado.__histICV) estado.__histICV = [];

    const resultados = estado.intersecciones.map(inter => {
        const seedBase = (inter.id.charCodeAt(0) + inter.id.charCodeAt(inter.id.length - 1)) % 97;
        const rnd = (Math.sin(Date.now() / 5000 + seedBase) + 1) / 2; // pseudo-ruido suave 0-1

        // Capacidad aproximada por número de carriles (si existe) para normalización
        const carriles = inter.num_carriles || 4;
        const capacidadVehiculos = carriles * 60; // capacidad aproximada instantánea

        // Flujo base (veh/min) con variación suavizada y perfil horario
        const flujo = (10 + carriles * 3.5) * (0.35 + perfilHora) * (0.55 + rnd * 0.7); // factores más contenidos

        // Número de vehículos instantáneo proporcional al flujo y carriles
        const numVehiculos = Math.min(
            Math.round(flujo * (0.3 + rnd * 0.9)),
            capacidadVehiculos
        );

        // Velocidad promedio decrece cuando flujo ocupa capacidad
        const ocupacionRel = numVehiculos / capacidadVehiculos; // 0–1
        const velLibre = 52; // km/h
        const velocidad = Math.max(8, velLibre * (1 - 0.55 * ocupacionRel) * (0.85 + (1 - rnd) * 0.3));

        // Cola estimada: función convexa de ocupación y baja velocidad
        const cola = Math.max(0,
            (ocupacionRel ** 1.4) * 200 * (velocidad < 25 ? 1.3 : 0.8)
        );

        // Calcular ICV sintético combinando componentes (similar a lógica difusa simplificada)
        // Normalizaciones:
        const velNorm = Math.min(1, velocidad / velLibre); // 1 = libre
        const flujoNorm = Math.min(1, flujo / (carriles * 30)); // saturación aproximada
        const colaNorm = Math.min(1, cola / 180); // escala cola

        // Pesos: congestión aumenta con flujo, cola y baja velocidad
        let icvLocal = 0.40 * flujoNorm + 0.30 * colaNorm + 0.15 * (1 - velNorm);
        // Añadir componente aleatoria leve para evitar sincronización completa
        icvLocal = Math.max(0, Math.min(0.95, icvLocal * (0.9 + (rnd-0.5) * 0.2)));

        // Mezcla con resumen de SUMO si está disponible (híbrido)
        // Esto ayuda a que, cuando haya tráfico real en parte del mapa, el simulador
        // se alinee en magnitud sin homogeneizar todo.
        let icv = icvLocal;
        if (estado.metricasSUMOResumen && typeof estado.metricasSUMOResumen.icvPromedio === 'number') {
            const icvSUMO = Math.min(0.99, Math.max(0, estado.metricasSUMOResumen.icvPromedio || 0));
            // Peso ajustado por proximidad
            const proximidad = calcularSesgoPorProximidadSUMO(inter);
            const mezcla = 0.15 + 0.35 * proximidad; // reducir influencia para evitar ponerse todo rojo
            // Variación por intersección para evitar uniformidad
            const jitter = (seedBase % 11) / 100; // 0–0.10
            icv = (1 - mezcla) * icvLocal + mezcla * (icvSUMO * (0.9 + jitter));
        }
        // Si NO hay datos de SUMO, no mezclar con un valor por defecto distinto de 0
        // (icv se queda en icvLocal).

        // Ajuste visual: valores más diversos por intersección en simulación
        // Mantener banda general, pero con centros distintos por intersección para evitar apariencia falsa
        let objetivoCentro = 0.57; // centro base
        // Desplazamiento por intersección (determinístico por ID) - más amplio
        const offsetId = ((seedBase % 17) - 8) * 0.0023; // ~[-0.0184, +0.0184]
        objetivoCentro = Math.max(0.553, Math.min(0.598, objetivoCentro + offsetId));

        // Sesgo por zona para mayor contraste (ligero)
        const zonaBiasMap = {
            'SJL': -0.006,
            'LIN': -0.004,
            'JM': 0.006,
            'PL': 0.005,
            'SB': 0.004,
            'SM': 0.004
        };
        const biasZona = zonaBiasMap[inter.zona] || 0;
        objetivoCentro = Math.max(0.553, Math.min(0.598, objetivoCentro + biasZona));
        // Cluster alto (zona oeste/centro cercanas entre sí)
        const clusterAlto = new Set([
            'SM-001','SM-002','SM-003','SM-004', // San Miguel y La Marina
            'JM-001','JM-003',                    // Jesús María
            'PL-001',                             // Pueblo Libre
            'TR-001','TR-002','TR-003',          // Paseo de la República / transversales
            'SB-001'                              // San Borja (Javier Prado con Aviación)
        ]);
        if (clusterAlto.has(inter.id)) {
            objetivoCentro = 0.605; // sesgo suave hacia ~0.605 (permitirá 0.60–0.61)
        }
        // Amplitud base y variación por intersección para no verse estático
        const amplitudBase = 0.026;           // banda total nominal aún más notoria
        const jitterAmp = ((seedBase % 13) - 6) * 0.0026; // ~±0.013
        const amplitud = Math.max(0.020, Math.min(0.036, amplitudBase + jitterAmp));
        // Oscilaciones lentas + ruido leve para microvariación
        const t = Date.now() / 30000; // periodo largo (~30s)
        const oscilacion1 = Math.sin(t + seedBase) * (amplitud * 0.55);
        const oscilacion2 = Math.cos(t * 0.85 + seedBase * 1.4) * (amplitud * 0.32);
        const microRuido = (Math.sin(t * 2.0 + seedBase * 2.1) * 0.004);
        icv = objetivoCentro + oscilacion1 + oscilacion2 + microRuido;
        // Clamp final con excepciones: cluster alto permite hasta 0.61
        if (clusterAlto.has(inter.id)) {
            icv = Math.max(0.551, Math.min(0.618, icv));
        } else {
            icv = Math.max(0.550, Math.min(0.600, icv));
        }

        // Suavizado temporal (exponencial) para evitar saltos bruscos
        const prev = estado.__cacheSim[inter.id];
        if (prev) {
            const alpha = 0.55; // peso de nuevo valor
            icv = prev.icv * (1 - alpha) + icv * alpha;
        }

        // También mezclar flujo con SUMO promedio de forma leve
        // Flujo regular (visual): banda moderada con variación lenta, independiente del backend
        let flujoOut = 28 + (carriles - 4) * 2; // base por carriles (veh/min)
        const oscilFlujo1 = Math.cos(t * 0.8 + seedBase) * 3; // oscilación principal
        const oscilFlujo2 = Math.sin(t * 1.1 + seedBase * 0.7) * 2; // oscilación secundaria
        const ruidoFlujo = ((seedBase % 5) - 2) * 0.3; // pequeño offset fijo por intersección
        flujoOut = Math.max(18, Math.min(44, flujoOut + oscilFlujo1 + oscilFlujo2 + ruidoFlujo));

        estado.__cacheSim[inter.id] = { icv, flujo: flujoOut, velocidad, cola, numVehiculos };

        // Regla solicitada: ICV > 20 (%) ya debe ser amarillo
        // Nuestro ICV está en 0–1, así que 20% = 0.20
        const color = icv < 0.20 ? '#10b981' : icv < 0.58 ? '#f59e0b' : '#ef4444';

        return {
            interseccion_id: inter.id,
            interseccion_nombre: inter.nombre,
            icv: parseFloat(icv.toFixed(3)),
            num_vehiculos: numVehiculos,
            flujo: parseFloat(flujoOut.toFixed(1)),
            velocidad: parseFloat(velocidad.toFixed(1)),
            cola: parseFloat(cola.toFixed(1)),
            color: color,
            nivel: icv < 0.33 ? 'Bajo' : icv < 0.66 ? 'Medio' : 'Alto'
        };
    });

    // Removido control de saturación para evitar cualquier tendencia acumulativa.
    // Los valores oscilan suavemente alrededor de 0.57 sin subir en bloque.

    return resultados;
}

// ==================== ACTUALIZACIÓN UNIFICADA DE DATOS ====================
/**
 * Función unificada para actualizar todos los componentes de la interfaz
 * @param {Array} metricas - Array de métricas de las intersecciones
 * @param {String} origen - Origen de los datos: 'backend' o 'local'
 */
function actualizarDatosInterfaz(metricas, origen = 'backend') {
    // 1. Si es backend, detener simulación local
    if (origen === 'backend') {
        if (!estado.backendConectado) {
            estado.backendConectado = true;
            console.log('Backend conectado - Usando datos en tiempo real del servidor');
        }

        if (estado.simulacionInterval && estado.modoActual === 'simulador') {
            console.log('Deteniendo simulación local - Backend tomó el control');
            clearInterval(estado.simulacionInterval);
            estado.simulacionInterval = null;
        }
    }

    // 2. Almacenar métricas en estado global para acceso desde simulación de video
    if (!estado.ultimasMetricas) {
        estado.ultimasMetricas = {};
    }
    metricas.forEach(m => {
        estado.ultimasMetricas[m.interseccion_id] = {
            num_vehiculos: m.num_vehiculos || 0,
            icv: m.icv || 0,
            flujo: m.flujo || 0,
            velocidad: m.velocidad || 0,
            cola: m.cola || 0,
            estado_semaforo: m.estado_semaforo || 'verde'
        };
    });

    // 3. Calcular promedios con clamp por intersección en modo simulador
    if (estado.modoActual === 'simulador') {
        const clusterAlto = new Set([
            'SM-001','SM-002','SM-003','SM-004',
            'JM-001','JM-003',
            'PL-001',
            'TR-001','TR-002','TR-003',
            'SB-001'
        ]);
        metricas = metricas.map(m => {
            const maxVal = clusterAlto.has(m.interseccion_id) ? 0.61 : 0.595;
            return {
                ...m,
                icv: Math.max(0.55, Math.min(maxVal, m.icv || 0))
            };
        });
    }
    let icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / Math.max(1, metricas.length);
    // Oscilación global suave en modo simulador para el promedio (≈0.58–0.59)
    if (estado.modoActual === 'simulador') {
        const tGlobal = Date.now() / 25000; // periodo largo
        const centroGlobal = 0.585;
        const ampGlobal = 0.005; // banda total ~0.58–0.59
        const variacion = Math.sin(tGlobal) * ampGlobal;
        icvPromedio = Math.max(0.58, Math.min(0.59, centroGlobal + variacion));
    }
    let flujoPromedio = metricas.reduce((sum, m) => sum + m.flujo, 0) / Math.max(1, metricas.length);

    // En modo SUMO, si el backend envió promedios agregados, usarlos directamente
    if (estado.modoActual === 'sumo' && estado.__overridePromedios) {
        if (typeof estado.__overridePromedios.icv === 'number') {
            icvPromedio = Math.max(0.02, estado.__overridePromedios.icv);
        }
        if (typeof estado.__overridePromedios.flujo === 'number') {
            flujoPromedio = Math.max(0.02, estado.__overridePromedios.flujo);
        }
        // Limpiar override para próximas iteraciones
        estado.__overridePromedios = null;
    }

    // 4. Actualizar cada intersección
    metricas.forEach(metrica => {
        const { interseccion_id, icv, clasificacion, color, flujo, velocidad, cola, estado_semaforo } = metrica;

        // Actualizar marcador en el mapa
        actualizarColorMarcador(interseccion_id, icv);

        // Actualizar estado del semáforo si viene en las métricas
        if (estado_semaforo) {
            // Mapear estados: 'verde', 'amarillo', 'rojo'
            // El backend envía la fase (verde/amarillo/rojo)
            const estadoMapeo = {
                'verde': 'verde',
                'amarillo': 'amarillo',
                'rojo': 'rojo'
            };
            
            const estadoSemaforo = estadoMapeo[estado_semaforo] || 'verde';
            
            // Actualizar semáforos (NS y EO opuestos)
            if (!window.semaforosInterseccion[interseccion_id]) {
                window.semaforosInterseccion[interseccion_id] = {
                    norte: { estado: estadoSemaforo, tiempo: 0 },
                    sur: { estado: estadoSemaforo, tiempo: 0 },
                    este: { estado: estadoSemaforo === 'verde' ? 'rojo' : 'verde', tiempo: 0 },
                    oeste: { estado: estadoSemaforo === 'verde' ? 'rojo' : 'verde', tiempo: 0 }
                };
            }
            
            // Actualizar estados globales también (para intersecciones genéricas)
            if (interseccion_id === 'SM-002') {  // Usar SM-002 como referencia global
                window.semaforosInterseccion.norte.estado = estadoSemaforo;
                window.semaforosInterseccion.sur.estado = estadoSemaforo;
                window.semaforosInterseccion.este.estado = estadoSemaforo === 'verde' ? 'rojo' : 'verde';
                window.semaforosInterseccion.oeste.estado = estadoSemaforo === 'verde' ? 'rojo' : 'verde';
            }
        }

        // Actualizar o crear tarjeta de métrica
        actualizarTarjetaMetrica(interseccion_id, {
            icv,
            // Ajuste de clasificación acorde a umbral 20%
            clasificacion: clasificacion || (icv < 0.20 ? 'Fluido' : icv < 0.58 ? 'Moderado' : 'Congestionado'),
            flujo,
            velocidad,
            cola
        });
    });

    // 4. Actualizar gráficos de forma unificada (solo si existen)
    if (estado.chartICV && estado.chartFlujo) {
        const timestamp = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        estado.chartICV.data.labels.push(timestamp);
        estado.chartICV.data.datasets[0].data.push(icvPromedio);

        // Limitar a 20 puntos
        if (estado.chartICV.data.labels.length > 20) {
            estado.chartICV.data.labels.shift();
            estado.chartICV.data.datasets[0].data.shift();
        }

        estado.chartICV.update('none');

        estado.chartFlujo.data.labels.push(timestamp);
        estado.chartFlujo.data.datasets[0].data.push(flujoPromedio);

        // Limitar a 20 puntos
        if (estado.chartFlujo.data.labels.length > 20) {
            estado.chartFlujo.data.labels.shift();
            estado.chartFlujo.data.datasets[0].data.shift();
        }

        estado.chartFlujo.update('none');
    }

    // 5. Actualizar estadísticas globales
    document.getElementById('num-intersecciones').textContent = metricas.length;
    document.getElementById('icv-promedio').textContent = icvPromedio.toFixed(2);
    document.getElementById('flujo-promedio').textContent = Math.round(flujoPromedio);

    // 6. Actualizar mini-stats (fluidas, moderadas, congestionadas, velocidad promedio)
    let callesFluidas = 0;
    let callesModeradas = 0;
    let callesCongestionadas = 0;
    let velocidadTotal = 0;

    metricas.forEach(metrica => {
        // Umbrales actualizados: amarillo desde 20%, rojo desde ~58%
        if (metrica.icv < 0.20) {
            callesFluidas++;
        } else if (metrica.icv < 0.58) {
            callesModeradas++;
        } else {
            callesCongestionadas++;
        }
        velocidadTotal += (metrica.velocidad || 0);
    });

    const velocidadPromedio = metricas.length > 0 ? velocidadTotal / metricas.length : 0;

    document.getElementById('calles-fluidas').textContent = callesFluidas;
    document.getElementById('calles-moderadas').textContent = callesModeradas;
    document.getElementById('calles-congestionadas').textContent = callesCongestionadas;
    document.getElementById('velocidad-promedio').textContent = Math.round(velocidadPromedio);

    // 7. Actualizar sistema difuso
    actualizarSistemaDifuso(metricas);

    // 8. Actualizar contador de decisiones
    estado.estadisticas.contadorActualizaciones++;
    document.getElementById('decisiones-tomadas').textContent = estado.estadisticas.contadorActualizaciones;

    // 9. Calcular olas verdes activas (intersecciones con alto tráfico)
    const olasActivas = metricas.filter(m => m.icv > 0.6).length;
    document.getElementById('olas-activas').textContent = olasActivas;

    // 10. Actualizar colores de conexiones según ICV y agregar velocidad promedio
    actualizarColoresConexionesSegunICV(metricas);
}

function actualizarMetricas(metricas) {
    // Función legacy - ahora usa la función unificada
    actualizarDatosInterfaz(metricas, 'local');
}

// FUNCIÓN OBSOLETA - Se mantiene por compatibilidad pero ya no se usa internamente
function actualizarMetricas_OLD(metricas) {
    const container = document.getElementById('metricas-container');

    // Calcular promedios
    let icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / metricas.length;
    if (estado.modoActual === 'simulador') {
        icvPromedio = Math.max(0.50, Math.min(0.60, icvPromedio || 0));
    }
    const flujoPromedio = metricas.reduce((sum, m) => sum + m.flujo, 0) / metricas.length;

    // Actualizar estadísticas globales
    document.getElementById('icv-promedio').textContent = icvPromedio.toFixed(2);
    document.getElementById('flujo-promedio').textContent = Math.round(flujoPromedio);

    // Actualizar gráficos
    actualizarGraficos(icvPromedio, flujoPromedio);

    // Actualizar tarjetas de métricas (mostrar solo primeras 8)
    container.innerHTML = '';
    metricas.slice(0, 8).forEach(metrica => {
        container.innerHTML += crearTarjetaMetrica(metrica);
        actualizarColorMarcador(metrica.interseccion_id, metrica.icv);
    });

    // Actualizar sistema difuso
    actualizarSistemaDifuso(metricas);

    // Actualizar contador de decisiones
    estado.estadisticas.contadorActualizaciones++;
    document.getElementById('decisiones-tomadas').textContent = estado.estadisticas.contadorActualizaciones;

    // Calcular olas verdes activas
    const olasActivas = metricas.filter(m => m.icv > 0.6).length;
    document.getElementById('olas-activas').textContent = olasActivas;
}

function crearTarjetaMetrica(metrica) {
    return `
        <div class="metrica-card" style="border-left-color: ${metrica.color};">
            <div class="metrica-header">
                <span class="metrica-nombre">${metrica.interseccion_id}</span>
                <div class="metrica-icv" style="background-color: ${metrica.color};">
                    ${metrica.icv.toFixed(2)}
                </div>
            </div>
            <div class="metrica-info">
                <small>${metrica.interseccion_nombre}</small>
            </div>
            <div class="metrica-detalles">
                <div class="detalle-item">
                    <span class="detalle-label"><i class="fas fa-car"></i> Vehículos</span>
                    <span class="detalle-valor">${metrica.num_vehiculos}</span>
                </div>
                <div class="detalle-item">
                    <span class="detalle-label"><i class="fas fa-tachometer-alt"></i> Flujo</span>
                    <span class="detalle-valor">${metrica.flujo.toFixed(1)} v/m</span>
                </div>
                <div class="detalle-item">
                    <span class="detalle-label"><i class="fas fa-road"></i> Velocidad</span>
                    <span class="detalle-valor">${metrica.velocidad.toFixed(0)} km/h</span>
                </div>
                <div class="detalle-item">
                    <span class="detalle-label"><i class="fas fa-arrows-alt-h"></i> Cola</span>
                    <span class="detalle-valor">${metrica.cola.toFixed(0)} m</span>
                </div>
            </div>
            <div class="metrica-footer">
                <span class="nivel-badge" style="background: ${metrica.color};">
                    ${metrica.nivel}
                </span>
            </div>
        </div>
    `;
}

function actualizarSistemaDifuso(metricas) {
    // Calcular tiempo verde promedio basado en ICV
    const icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / metricas.length;
    const tiempoVerde = icvPromedio < 0.3 ? 30 : icvPromedio < 0.6 ? 45 : 60;

    document.getElementById('tiempo-verde-medio').textContent = `${tiempoVerde}s`;

    // Reglas activas (basado en estados únicos)
    const reglasActivas = new Set(metricas.map(m => m.nivel)).size * 3;
    document.getElementById('reglas-activas').textContent = reglasActivas;
}

// ==================== MODOS DE OPERACIÓN ====================
function configurarEventListeners() {
    // Modo de operación
    document.getElementById('modo-operacion').addEventListener('change', cambiarModo);

    // Botón de emergencia
    document.getElementById('btn-emergencia').addEventListener('click', abrirModalEmergencia);

    // Botón de reinicio de simulador
    const btnReiniciar = document.getElementById('btn-reiniciar-simulador');
    if (btnReiniciar) {
        btnReiniciar.addEventListener('click', reiniciarSimulador);
    }

    // NUEVO: Botones del Procesador Video
    const btnToggleVideo = document.getElementById('btn-toggle-video');
    const btnExpandVideo = document.getElementById('btn-expand-video');

    if (btnToggleVideo) {
        btnToggleVideo.addEventListener('click', toggleVideoYOLO);
        console.log('✓ Event listener agregado a btn-toggle-video (Procesador Video)');
    } else {
        console.error('❌ btn-toggle-video no encontrado en el DOM');
    }

    if (btnExpandVideo) {
        btnExpandVideo.addEventListener('click', toggleExpandVideo);
        console.log('✓ Event listener agregado a btn-expand-video (Procesador Video)');
    } else {
        console.error('❌ btn-expand-video no encontrado en el DOM');
    }

    // NUEVO: Doble clic en canvas para expandir
    const videoCanvas = document.getElementById('video-canvas');
    if (videoCanvas) {
        videoCanvas.addEventListener('dblclick', toggleExpandVideo);
        console.log('✓ Event listener agregado a video-canvas');
    }

    // NUEVO: Selector de intersección para cámara
    const selectorInterseccion = document.getElementById('selector-interseccion-cam');
    if (selectorInterseccion) {
        selectorInterseccion.addEventListener('change', seleccionarInterseccionCamara);
        console.log('✓ Event listener agregado a selector-interseccion-cam');
    } else {
        console.error('❌ selector-interseccion-cam no encontrado en el DOM');
    }

    // NUEVO: Controles de Motor Giratorio Horizontal con soporte para mantener presionado
    const btnLeft = document.getElementById('ptz-left');
    const btnRight = document.getElementById('ptz-right');

    if (btnLeft) {
        btnLeft.addEventListener('mousedown', () => iniciarRotacionContinua('left'));
        btnLeft.addEventListener('mouseup', detenerRotacionContinua);
        btnLeft.addEventListener('mouseleave', detenerRotacionContinua);
        btnLeft.addEventListener('touchstart', (e) => { e.preventDefault(); iniciarRotacionContinua('left'); });
        btnLeft.addEventListener('touchend', (e) => { e.preventDefault(); detenerRotacionContinua(); });
    }

    if (btnRight) {
        btnRight.addEventListener('mousedown', () => iniciarRotacionContinua('right'));
        btnRight.addEventListener('mouseup', detenerRotacionContinua);
        btnRight.addEventListener('mouseleave', detenerRotacionContinua);
        btnRight.addEventListener('touchstart', (e) => { e.preventDefault(); iniciarRotacionContinua('right'); });
        btnRight.addEventListener('touchend', (e) => { e.preventDefault(); detenerRotacionContinua(); });
    }

    // NUEVO: Toggle modo automático/manual
    document.getElementById('toggle-seguimiento-auto')?.addEventListener('change', toggleSeguimientoAuto);

    // NOTA: Backdrop no tiene pointer-events, solo es visual
    // Para cerrar el panel expandido, usar el botón o tecla ESC

    // NUEVO: Tecla ESC para cerrar video expandido
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && estadoVideo.expandido) {
            toggleExpandVideo();
        }
    });

    // IMPORTANTE: Iniciar actualización de tráfico y métricas del dashboard
    // Esto debe estar SIEMPRE activo sin importar el modo
    if (!estado.actualizacionTraficoInterval) {
        iniciarActualizacionTrafico();
    }

    console.log('Event listeners configurados');
}

async function cambiarModo(event) {
    const nuevoModo = event.target.value;
    const modoAnterior = estado.modoActual;
    estado.modoActual = nuevoModo;

    console.log(`Cambiando modo de ${modoAnterior} a: ${nuevoModo}`);

    // Si estábamos en modo SUMO, notificar al backend para desconectar
    if (modoAnterior === 'sumo' && nuevoModo !== 'sumo') {
        try {
            console.log('📡 Notificando al backend para cerrar SUMO...');
            await fetch(`${API_URL}/api/modo/cambiar?modo=${nuevoModo}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.error('Error desconectando SUMO:', error);
        }
    }

    // Detener simulación actual
    if (estado.simulacionInterval) {
        clearInterval(estado.simulacionInterval);
        estado.simulacionInterval = null;
    }

    // Limpiar calles SUMO si existen
    limpiarCallesSUMO();

    // Detener video si estaba activo
    if (procesandoVideo) {
        detenerModoVideo();
    }

    document.getElementById('selector-interseccion-cam').style.display = 'none';

    switch (nuevoModo) {
        case 'simulador':
            // Notificar al backend
            try {
                await fetch(`${API_URL}/api/modo/cambiar?modo=simulador`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (error) {
                console.error('Error cambiando a modo simulador:', error);
            }
            
            iniciarSimulacion();
            if (!estado.actualizacionTraficoInterval) {
                iniciarActualizacionTrafico();
            }
            document.getElementById('selector-interseccion-cam').style.display = 'block';
            cargarInterseccionesSimulador();
            break;
        case 'video':
        case 'procesador_video':
        case 'procesador-video':
            console.log('Modo Procesador Video seleccionado');
            
            // Notificar al backend
            try {
                await fetch(`${API_URL}/api/modo/cambiar?modo=video`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (error) {
                console.error('Error cambiando a modo video:', error);
            }
            
            // NO limpiar tráfico - solo limpiar las capas visuales del mapa
            if (estado.capaTrafico) {
                estado.capaTrafico.clearLayers();
            }
            // MANTENER actualizacionTraficoInterval para que siga actualizando las métricas
            document.getElementById('selector-interseccion-cam').style.display = 'block';
            await cargarInterseccionesVideo();
            break;
        case 'sumo':
            console.log('Modo SUMO - Cargando visualizacion de trafico');
            
            // Mostrar panel SUMO y superponerlo exactamente sobre el recuadro de video
            const sumoPanel = document.getElementById('sumo-status-panel');
            const panelVideo = document.getElementById('panel-video');
            const videoContainer = document.querySelector('#panel-video .video-container');
            if (sumoPanel && panelVideo && videoContainer) {
                // No ocultar el panel-video para mantener el mismo diseño de tarjeta
                panelVideo.style.position = 'relative';

                // Mover el panel SUMO como hijo del contenedor de video para ocupar ese recuadro
                if (sumoPanel.parentElement !== videoContainer) {
                    videoContainer.appendChild(sumoPanel);
                }
                sumoPanel.classList.add('sumo-overlay');
                sumoPanel.style.display = 'flex';
            }
            
            // ⚡ CRÍTICO: Notificar al backend para que inicie SUMO-GUI
            try {
                console.log('📡 Notificando al backend para iniciar SUMO...');
                const response = await fetch(`${API_URL}/api/modo/cambiar?modo=sumo`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    const data = await response.json();
                    console.log('✅ Backend confirmó:', data.mensaje);
                } else {
                    console.warn('⚠️  Backend respondió con error:', response.status);
                }
            } catch (error) {
                console.error('❌ Error notificando al backend:', error);
            }
            
            // Limpiar solo capas visuales
            if (estado.capaTrafico) {
                estado.capaTrafico.clearLayers();
            }
            
            // MANTENER actualizacionTraficoInterval para que siga actualizando las métricas
            await cargarYVisualizarCallesSUMO();
            
            // Iniciar actualización de estado SUMO de inmediato y cada 2s
            if (estado.actualizacionEstadoSUMO) {
                clearInterval(estado.actualizacionEstadoSUMO);
            }
            actualizarEstadoSUMO();
            estado.actualizacionEstadoSUMO = setInterval(actualizarEstadoSUMO, 2000);
            // No mostrar notificaciones emergentes en modo SUMO
            
            break;
    }
    
    // Ocultar panel SUMO si no está en modo SUMO
    if (nuevoModo !== 'sumo') {
        const sumoPanel = document.getElementById('sumo-status-panel');
        const panelVideo = document.getElementById('panel-video');
        if (sumoPanel) {
            sumoPanel.style.display = 'none';
            // Mantenerlo en DOM pero oculto; diseño coherente
            sumoPanel.style.position = 'absolute';
        }
        if (panelVideo) {
            panelVideo.style.visibility = 'visible';
        }
        if (estado.actualizacionEstadoSUMO) {
            clearInterval(estado.actualizacionEstadoSUMO);
            estado.actualizacionEstadoSUMO = null;
        }
        // Si salimos de SUMO, forzar métricas a cero como si servidor se desconectara
        if (modoAnterior === 'sumo') {
            estado.__overridePromedios = { icv: 0, flujo: 0 };
            const sinteticaCero = [{
                interseccion_id: 'SUMO-AGREGADO',
                icv: 0,
                flujo: 0,
                velocidad: 0,
                cola: 0,
                num_vehiculos: 0,
                color: '#10b981',
                clasificacion: 'Fluido'
            }];
            actualizarDatosInterfaz(sinteticaCero, 'backend');
        }
    }
}

// ==================== REINICIO DE SIMULADOR ====================
async function reiniciarSimulador() {
    const btnReiniciar = document.getElementById('btn-reiniciar-simulador');
    
    try {
        // Cambiar estado del botón a "cargando"
        btnReiniciar.disabled = true;
        const iconOriginal = btnReiniciar.innerHTML;
        btnReiniciar.innerHTML = '<i class="fas fa-spinner"></i> Cargando...';
        
        console.log('🔄 Enviando solicitud de reinicio del simulador...');
        
        const response = await fetch('http://localhost:8000/api/simulacion/reiniciar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ escenario: 'hora_pico_manana' })
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Simulador reiniciado correctamente');
            console.log('📊 Respuesta:', data);
            
            // Mostrar notificación
            mostrarNotificacion('✅ Simulador reiniciado con todas las 47 intersecciones', 'success');
            
            // Esperar un poco para que se reinicie el simulador
            setTimeout(() => {
                btnReiniciar.disabled = false;
                btnReiniciar.innerHTML = iconOriginal;
            }, 2000);
        } else {
            console.error('❌ Error en la respuesta del servidor:', response.status);
            mostrarNotificacion('❌ Error al reiniciar el simulador', 'error');
            btnReiniciar.disabled = false;
            btnReiniciar.innerHTML = iconOriginal;
        }
    } catch (error) {
        console.error('❌ Error de conexión:', error);
        mostrarNotificacion('❌ Error de conexión con el servidor', 'error');
        
        const btnReiniciar = document.getElementById('btn-reiniciar-simulador');
        btnReiniciar.disabled = false;
        btnReiniciar.innerHTML = '<i class="fas fa-sync"></i> Reiniciar';
    }
}

// Función para mostrar notificaciones
function mostrarNotificacion(mensaje, tipo = 'info') {
    // Crear elemento de notificación
    const notif = document.createElement('div');
    notif.className = `notificacion notificacion-${tipo}`;
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        z-index: 9999;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        max-width: 400px;
    `;
    
    // Aplicar colores según tipo
    const colores = {
        success: 'background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white;',
        error: 'background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white;',
        info: 'background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white;',
        warning: 'background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white;'
    };
    
    notif.style.cssText += colores[tipo] || colores.info;
    notif.textContent = mensaje;
    
    document.body.appendChild(notif);
    
    // Remover después de 3 segundos
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// ==================== EMERGENCIAS ====================
function llenarSelectsEmergencia() {
    const origenSelect = document.getElementById('origen-emergencia');
    const destinoSelect = document.getElementById('destino-emergencia');

    estado.intersecciones.forEach(inter => {
        origenSelect.innerHTML += `<option value="${inter.id}">${inter.nombre}</option>`;
    });

    // Por defecto llenar destino con intersecciones (bomberos/policia)
    destinoSelect.innerHTML = '';
    estado.intersecciones.forEach(inter => {
        destinoSelect.innerHTML += `<option value="${inter.id}">${inter.nombre}</option>`;
    });

    // Inicializar estructuras para hospitales
    estado.hospitalMarkers = estado.hospitalMarkers || [];
    estado.hospitalDestinoMap = estado.hospitalDestinoMap || {}; // mapa hospitalId -> nearest interseccionId
}

// Actualiza el select de destino según tipo de vehículo (ambulancia -> hospitales)
function actualizarDestinoModal() {
    const tipo = document.getElementById('tipo-emergencia').value;
    const destinoSelect = document.getElementById('destino-emergencia');

    destinoSelect.innerHTML = '';

    if (tipo === 'ambulancia' && typeof HOSPITALES_LIMA !== 'undefined') {
        // Llenar con hospitales
        HOSPITALES_LIMA.forEach(h => {
            destinoSelect.innerHTML += `<option value="${h.id}">${h.nombre} (${h.tipo})</option>`;
        });

        // Mostrar marcadores en el mapa
        mostrarMarcadoresHospitales();
    } else {
        // Llenar con intersecciones
        estado.intersecciones.forEach(inter => {
            destinoSelect.innerHTML += `<option value="${inter.id}">${inter.nombre}</option>`;
        });

        // Limpiar marcadores de hospitales
        limpiarMarcadoresHospitales();
    }
}

function mostrarMarcadoresHospitales() {
    if (!estado.mapa || typeof HOSPITALES_LIMA === 'undefined') return;

    // Limpiar marcadores previos
    limpiarMarcadoresHospitales();

    HOSPITALES_LIMA.forEach(h => {
        const iconHtml = `
            <div style="display:flex;align-items:center;justify-content:center;background:#ffffff;border-radius:50%;width:40px;height:40px;border:3px solid #2563eb;box-shadow:0 4px 10px rgba(0,0,0,0.15);">
                <span style="font-size:18px;">🏥</span>
            </div>`;

        const m = L.marker([h.lat, h.lon], {
            title: h.nombre,
            icon: L.divIcon({ html: iconHtml, className: '', iconSize: [40, 40] })
        }).addTo(estado.mapa);
        m.bindPopup(`<strong>${h.nombre}</strong><br/>Tipo: ${h.tipo}`);
        estado.hospitalMarkers.push(m);
    });
}

function limpiarMarcadoresHospitales() {
    if (!estado.hospitalMarkers) return;
    estado.hospitalMarkers.forEach(m => {
        try { estado.mapa.removeLayer(m); } catch (e) {}
    });
    estado.hospitalMarkers = [];
}

// Mapear hospital a la intersección más cercana y cachear en estado.hospitalDestinoMap
function mapHospitalToNearestIntersection(hospital) {
    if (!estado.intersecciones) return null;

    // Si ya está calculado
    if (estado.hospitalDestinoMap && estado.hospitalDestinoMap[hospital.id]) {
        return estado.hospitalDestinoMap[hospital.id];
    }

    let mejorId = null;
    let mejorDist = Infinity;

    estado.intersecciones.forEach(inter => {
        const d = calcularDistancia(hospital.lat, hospital.lon, inter.latitud, inter.longitud);
        if (d < mejorDist) {
            mejorDist = d;
            mejorId = inter.id;
        }
    });

    estado.hospitalDestinoMap[hospital.id] = mejorId;
    return mejorId;
}

// Solicita al backend estimaciones de tiempo a múltiples destinos (intersecciones)
async function estimarDestinosDesdeOrigen(origenId, destinosInterseccionIds) {
    try {
        const resp = await fetch(`${API_URL}/api/emergencia/estimar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origen: origenId, destinos: destinosInterseccionIds })
        });
        if (!resp.ok) {
            const texto = await resp.text().catch(() => null);
            console.error('Estimación fallida. Status:', resp.status, 'Body:', texto);
            throw new Error(`Estimación fallida: ${resp.status} - ${texto}`);
        }
        return await resp.json();
    } catch (e) {
        console.error('Error estimando destinos:', e);
        return null;
    }
}

// Sugiere el mejor hospital (menor tiempo estimado) y selecciona en el modal
async function sugerirMejorHospital(origenId) {
    if (!origenId || typeof HOSPITALES_LIMA === 'undefined') return;

    // Mapear hospitales a intersecciones
    const mapping = HOSPITALES_LIMA.map(h => ({
        hospitalId: h.id,
        interId: mapHospitalToNearestIntersection(h)
    })).filter(m => m.interId);

    const destinos = mapping.map(m => m.interId);
    const estimaciones = await estimarDestinosDesdeOrigen(origenId, destinos);

    // Si el backend respondió con estimaciones válidas, elegir por tiempo estimado
    if (estimaciones && Array.isArray(estimaciones) && estimaciones.length > 0) {
        let mejor = null;
        estimaciones.forEach(e => {
            if (!mejor || e.tiempo_estimado < mejor.tiempo_estimado) mejor = e;
        });

        if (mejor) {
            const m = mapping.find(x => x.interId === mejor.destino);
            if (m) {
                const destinoSelect = document.getElementById('destino-emergencia');
                destinoSelect.value = m.hospitalId;
                // mostrarNotificacion('info', `Sugerido: ${HOSPITALES_LIMA.find(h=>h.id===m.hospitalId).nombre} (ETA ${Math.round(mejor.tiempo_estimado)}s)`);
                return;
            }
        }
    }

    // Si no hay estimaciones (backend caído) o no devolvió resultados, fallback geográfico (distancia mínima)
    const origenInter = INTERSECCIONES_LIMA.find(i => i.id === origenId);
    if (!origenInter) return;

    let mejorHospital = null;
    let mejorDist = Infinity;
    mapping.forEach(m => {
        const h = HOSPITALES_LIMA.find(hs => hs.id === m.hospitalId);
        if (!h) return;
        const d = calcularDistancia(origenInter.latitud, origenInter.longitud, h.lat, h.lon);
        if (d < mejorDist) {
            mejorDist = d;
            mejorHospital = m;
        }
    });

    if (mejorHospital) {
        const destinoSelect = document.getElementById('destino-emergencia');
        destinoSelect.value = mejorHospital.hospitalId;
        // mostrarNotificacion('info', `Sugerido (por distancia): ${HOSPITALES_LIMA.find(h=>h.id===mejorHospital.hospitalId).nombre} (~${Math.round(mejorDist)} m)`);
    }
}

function abrirModalEmergencia() {
    document.getElementById('modal-emergencia').style.display = 'flex';
    // Actualizar selects según tipo actual
    setTimeout(() => {
        actualizarDestinoModal();
        const tipo = document.getElementById('tipo-emergencia')?.value;
        const origen = document.getElementById('origen-emergencia')?.value;
        // Mostrar íconos de hospitales inmediatamente al abrir si es ambulancia
        if (tipo === 'ambulancia') {
            try { mostrarMarcadoresHospitales(); } catch {}
        }
        if (tipo === 'ambulancia' && origen) {
            sugerirMejorHospital(origen);
        }
    }, 50);
}

// --- MODO: AÑADIR HOSPITAL EN MAPA (cliente-side) ---
// Botón flotante dentro del modal que permite marcar una ubicación en el mapa
function inicializarAgregarHospitalUI() {
    // Ocultar funcionalidad de "Marcar hospital en mapa" de la interfaz
    // No crear ni insertar el botón
    return;
}

// Inicializar control al cargar la app
document.addEventListener('DOMContentLoaded', () => {
    inicializarAgregarHospitalUI();
});

function cerrarModalEmergencia() {
    document.getElementById('modal-emergencia').style.display = 'none';
    // Mantener íconos visibles si hay una ola verde activa; si no, limpiar
    try {
        if (!estado.olaVerdeActiva) {
            limpiarMarcadoresHospitales();
        }
    } catch {}
}

// Sistema de pesos por gravedad/prioridad de emergencia
function obtenerPrioridadEmergencia(tipo) {
    const prioridades = {
        'ambulancia': {
            peso: 100,  // Máxima prioridad
            nivel: 'CRÍTICA',
            color: '#ef4444',
            descripcion: 'Vida en peligro - Prioridad Absoluta'
        },
        'bomberos': {
            peso: 80,   // Alta prioridad
            nivel: 'ALTA',
            color: '#f59e0b',
            descripcion: 'Emergencia de seguridad pública'
        },
        'policia': {
            peso: 60,   // Prioridad moderada
            nivel: 'MODERADA',
            color: '#3b82f6',
            descripcion: 'Respuesta policial requerida'
        }
    };

    return prioridades[tipo] || prioridades['policia'];
}

async function activarEmergencia() {
    const tipo = document.getElementById('tipo-emergencia').value;
    const origen = document.getElementById('origen-emergencia').value;
    let destino = document.getElementById('destino-emergencia').value;
    // velocidad removida de la UI; backend usa valor por defecto si no se provee

    // Validación de campos
    if (!origen || !destino) {
        alert('Por favor seleccione origen y destino');
        return;
    }

    if (origen === destino) {
        alert('El origen y destino no pueden ser iguales');
        return;
    }

    // Obtener prioridad según tipo de vehículo
    const prioridad = obtenerPrioridadEmergencia(tipo);

    // Mapear prioridad a los valores esperados por la API: 'critica'|'alta'|'media'
    const prioridadApi = (tipo === 'ambulancia') ? 'critica' : (tipo === 'bomberos' ? 'alta' : 'media');

    console.log('Activando ola verde con prioridad:', { tipo, origen, destino, prioridad: prioridadApi });

    try {
        // Guardar referencia del hospital destino original (antes de mapear) para mostrarlo correctamente
        let hospitalDestinoOriginal = null;
        if (tipo === 'ambulancia' && typeof HOSPITALES_LIMA !== 'undefined') {
            const destinoOriginal = destino;
            hospitalDestinoOriginal = HOSPITALES_LIMA.find(h => h.id === destinoOriginal);
        }

        // Intentar llamar al backend para calcular ruta óptima con Dijkstra
        // Si destino es un hospital (ambulancia), mapear a intersección cercana antes de enviar
        if (tipo === 'ambulancia' && typeof HOSPITALES_LIMA !== 'undefined') {
            const hosp = HOSPITALES_LIMA.find(h => h.id === destino);
            if (hosp) {
                const mapped = mapHospitalToNearestIntersection(hosp);
                if (mapped) destino = mapped; // usar intersección como destino para backend
            }
        }

        // Re-verificar que origen y destino no sean iguales tras el mapeo (hospital -> intersección)
        if (origen === destino) {
            alert('El origen y destino mapeado son iguales; por favor elige otro destino u origen.');
            return;
        }

        const response = await fetch(`${API_URL}/api/emergencia/activar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tipo: tipo,
                origen: origen,
                destino: destino,
                prioridad: prioridadApi
            })
        });

        if (!response.ok) {
            // Leer body de error para debugging y mostrar al usuario
            const texto = await response.text().catch(() => null);
            console.error('Activar emergencia falló. Status:', response.status, 'Body:', texto);
            alert(`Error activando emergencia: ${response.status}\n${texto || ''}`);
            return;
        }

        const resultado = await response.json();


            // Refuerzo: en modo SUMO, si por cualquier razón quedó en 0/NaN, aplicar mínimos
            if (estado.modoActual === 'sumo') {
                if (!isFinite(icvPromedio) || icvPromedio <= 0) icvPromedio = 0.02;
                if (!isFinite(flujoPromedio) || flujoPromedio <= 0) flujoPromedio = 0.02;
            }
        console.log('Ruta calculada por backend:', resultado);

        // Verificar que haya una ruta válida
        if (!resultado.ruta || resultado.ruta.length < 2) {
            alert('No se pudo encontrar una ruta entre las intersecciones seleccionadas.');
            return;
        }

        // Adjuntar datos del hospital destino al resultado para visualización
        if (hospitalDestinoOriginal) {
            resultado._hospitalDestino = hospitalDestinoOriginal;
            console.log('✅ Hospital destino adjuntado:', hospitalDestinoOriginal.nombre);
        }

        // Usar la función que procesa correctamente la respuesta del backend
        await mostrarOlaVerdeActivada(resultado);

        cerrarModalEmergencia();

    } catch (error) {
        console.error('Error conectando con backend:', error);
        console.log('Usando modo simulado sin backend');


        // MODO FALLBACK: Calcular ruta simple sin backend
        const rutaSimulada = calcularRutaSimple(origen, destino);

        if (!rutaSimulada || rutaSimulada.length < 2) {
            alert('No se pudo calcular una ruta entre las intersecciones seleccionadas.');
            return;
        }

        // Calcular distancia y tiempo estimados
        const distanciaTotal = calcularDistanciaRuta(rutaSimulada);
        const velocidadSimulada = 50; // km/h por defecto en modo fallback
        const tiempoEstimado = (distanciaTotal) * 3.6 / velocidadSimulada; // segundos

        const resultado = {
            ruta: rutaSimulada,
            distancia_total: distanciaTotal,
            tiempo_estimado: tiempoEstimado,
            vehiculo: {
                tipo: tipo,
                velocidad: velocidad,
                prioridad: prioridad.nivel
            }
        };

        console.log('Ruta simulada calculada:', resultado);
        
        // Adjuntar hospital destino si es ambulancia (modo fallback)
        if (tipo === 'ambulancia' && typeof HOSPITALES_LIMA !== 'undefined') {
            const destinoOriginalFallback = document.getElementById('destino-emergencia').value;
            const hospitalFallback = HOSPITALES_LIMA.find(h => h.id === destinoOriginalFallback);
            if (hospitalFallback) {
                resultado._hospitalDestino = hospitalFallback;
            }
        }
        
        await mostrarOlaVerdeActivada(resultado);
        
        // Cerrar modal después de mostrar la ruta
        cerrarModalEmergencia();
    }
}

// Calcular ruta simple entre dos intersecciones (sin Dijkstra)
function calcularRutaSimple(origenId, destinoId) {
    // Buscar intersecciones
    const origen = INTERSECCIONES_LIMA.find(i => i.id === origenId);
    const destino = INTERSECCIONES_LIMA.find(i => i.id === destinoId);

    if (!origen || !destino) {
        return null;
    }

    // Ruta directa simple
    // En una implementación real, esto usaría Dijkstra o A*
    // Por ahora, devolvemos las intersecciones más cercanas en línea
    const ruta = [origenId];

    // Encontrar intersecciones intermedias basadas en proximidad geográfica
    let actual = origen;
    const visitados = new Set([origenId]);
    const maxIntersecciones = 10; // Límite de seguridad

    while (ruta.length < maxIntersecciones) {
        // Encontrar la intersección no visitada más cercana al destino
        let mejorSiguiente = null;
        let mejorDistancia = Infinity;

        INTERSECCIONES_LIMA.forEach(inter => {
            if (!visitados.has(inter.id)) {
                // Calcular distancia desde esta intersección al destino
                const distAlDestino = calcularDistancia(
                    inter.latitud, inter.longitud,
                    destino.latitud, destino.longitud
                );

                // Verificar que esté "conectada" (dentro de un radio razonable)
                const distDesdeActual = calcularDistancia(
                    actual.latitud, actual.longitud,
                    inter.latitud, inter.longitud
                );

                if (distDesdeActual < 2000 && distAlDestino < mejorDistancia) {
                    mejorDistancia = distAlDestino;
                    mejorSiguiente = inter;
                }
            }
        });

        if (!mejorSiguiente || mejorSiguiente.id === destinoId) {
            ruta.push(destinoId);
            break;
        }

        ruta.push(mejorSiguiente.id);
        visitados.add(mejorSiguiente.id);
        actual = mejorSiguiente;
    }

    return ruta;
}

// Calcular distancia total de una ruta
function calcularDistanciaRuta(ruta) {
    let distanciaTotal = 0;

    for (let i = 0; i < ruta.length - 1; i++) {
        const inter1 = INTERSECCIONES_LIMA.find(int => int.id === ruta[i]);
        const inter2 = INTERSECCIONES_LIMA.find(int => int.id === ruta[i + 1]);

        if (inter1 && inter2) {
            distanciaTotal += calcularDistancia(
                inter1.latitud, inter1.longitud,
                inter2.latitud, inter2.longitud
            );
        }
    }

    return distanciaTotal;
}

// Calcular distancia entre dos puntos (fórmula de Haversine)
function calcularDistancia(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Radio de la Tierra en metros
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distancia en metros
}

function desactivarOlaVerde() {
    console.log('🧹 Desactivando ola verde y limpiando mapa...');
    
    // Cancelar timeout de desactivación automática si existe
    if (estado.timeoutOlaVerde) {
        clearTimeout(estado.timeoutOlaVerde);
        estado.timeoutOlaVerde = null;
        console.log('   ✓ Timeout cancelado');
    }
    
    // Limpiar polyline principal
    if (estado.olaVerdeActiva) {
        try {
            estado.mapa.removeLayer(estado.olaVerdeActiva);
            console.log('   ✓ Polyline removida');
        } catch (e) {
            console.warn('   ⚠️ Error eliminando polyline:', e);
        }
        estado.olaVerdeActiva = null;
    }

    // Limpiar marcadores
    if (estado.marcadoresOlaVerde && estado.marcadoresOlaVerde.length > 0) {
        estado.marcadoresOlaVerde.forEach(m => {
            try {
                estado.mapa.removeLayer(m);
            } catch (e) {
                console.warn('   ⚠️ Error limpiando marcador:', e);
            }
        });
        console.log(`   ✓ ${estado.marcadoresOlaVerde.length} marcadores removidos`);
        estado.marcadoresOlaVerde = [];
    }

    // Actualizar UI
    const container = document.getElementById('olas-verdes-container');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-road"></i>
                <p>No hay olas verdes activas</p>
                <small>Activa una emergencia para ver la ruta</small>
            </div>
        `;
    }

    console.log('✅ Ola verde desactivada completamente');

    // Además, ocultar iconos de hospitales si estaban visibles (ambulancia)
    try {
        limpiarMarcadoresHospitales();
    } catch (e) {
        console.warn('   ⚠️ Error limpiando marcadores de hospitales:', e);
    }
}

// Actualizar display de velocidad en el modal
document.getElementById('velocidad-emergencia')?.addEventListener('input', function() {
    document.getElementById('velocidad-display').textContent = this.value + ' km/h';
});

// Actualizar indicador de prioridad cuando cambia el tipo de vehículo
document.getElementById('tipo-emergencia')?.addEventListener('change', function() {
    actualizarIndicadorPrioridad(this.value);
    // Actualizar destino (hospitales vs intersecciones)
    actualizarDestinoModal();
});

document.getElementById('origen-emergencia')?.addEventListener('change', function() {
    const tipo = document.getElementById('tipo-emergencia')?.value;
    if (tipo === 'ambulancia') {
        const origenId = this.value;
        sugerirMejorHospital(origenId);
    }
});

function actualizarIndicadorPrioridad(tipo) {
    const prioridad = obtenerPrioridadEmergencia(tipo);
    const indicator = document.getElementById('prioridad-indicator');

    if (!indicator) return;

    // Actualizar contenido
    indicator.querySelector('.prioridad-nivel').textContent = prioridad.nivel;
    indicator.querySelector('.prioridad-peso').textContent = `Peso: ${prioridad.peso}`;
    indicator.querySelector('.prioridad-descripcion').textContent = prioridad.descripcion;

    // Actualizar estilos según prioridad
    indicator.style.borderColor = prioridad.color;
    indicator.style.background = `linear-gradient(135deg, ${prioridad.color}15, ${prioridad.color}25)`;
    indicator.querySelector('.prioridad-nivel').style.color = prioridad.color;

    // Animación de actualización
    indicator.style.animation = 'none';
    setTimeout(() => {
        indicator.style.animation = 'priorityPulse 0.5s ease';
    }, 10);
}

// Inicializar el indicador con ambulancia por defecto
document.addEventListener('DOMContentLoaded', () => {
    actualizarIndicadorPrioridad('ambulancia');
});

// ==================== VISUALIZACIÓN CALLES SUMO ====================

async function cargarYVisualizarCallesSUMO() {
    try {
        console.log('Cargando calles de SUMO...');

        // Cargar GeoJSON de calles
        const response = await fetch(`${API_URL}/api/sumo/calles`);
        if (!response.ok) {
            console.error('Error cargando calles SUMO');
            alert('Error: No se pudo cargar el mapa de calles SUMO. Asegúrate de ejecutar extraer_calles.py primero.');
            return;
        }

        estado.callesGeoJSON = await response.json();
        console.log(`Calles cargadas: ${estado.callesGeoJSON.features.length}`);

        // Crear layer de calles
        if (!estado.mostrarSUMOTrafico) {
            // Si no se debe mostrar, limpiar cualquier resto visual
            limpiarCallesSUMO();
            // NO retornamos: igual queremos alimentar métricas desde SUMO
        }

        estado.callesSUMO = L.geoJSON(estado.callesGeoJSON, {
            style: function(feature) {
                return {
                    color: '#4a5568',
                    weight: 3,
                    opacity: 0.6
                };
            },
            onEachFeature: function(feature, layer) {
                const props = feature.properties;
                layer.bindPopup(`
                    <div class="popup-profesional">
                        <div class="popup-header" style="background: #4a5568;">
                            <i class="fas fa-road"></i>
                            <strong>${props.nombre || props.id}</strong>
                        </div>
                        <div class="popup-body">
                            <div class="popup-row">
                                <span class="popup-label">ID:</span>
                                <span class="popup-value">${props.id}</span>
                            </div>
                            <div class="popup-row">
                                <span class="popup-label">Longitud:</span>
                                <span class="popup-value">${props.longitud} m</span>
                            </div>
                            <div class="popup-row">
                                <span class="popup-label">Vel. Máx:</span>
                                <span class="popup-value">${props.velocidad_max} km/h</span>
                            </div>
                            <div class="popup-row">
                                <span class="popup-label">Carriles:</span>
                                <span class="popup-value">${props.num_lanes}</span>
                            </div>
                        </div>
                    </div>
                `);
                // Tooltip sutil para mostrar métricas en vivo cuando existan
                layer.bindTooltip(() => {
                    const id = props.id;
                    const m = (estado.__ultimoSUMOCalles || []).find(c => c.id === id);
                    if (!m) return `${props.nombre || id}`;
                    const cong = (m.congestion !== undefined) ? `${Math.round(m.congestion*100)}%` : 'N/A';
                    const vel = (m.velocidad !== undefined) ? `${Number(m.velocidad).toFixed(1)} km/h` : 'N/A';
                    const veh = (m.vehiculos !== undefined) ? `${m.vehiculos} veh` : 'N/A';
                    return `${props.nombre || id}\nCongestión: ${cong}\nVelocidad: ${vel}\nVehículos: ${veh}`;
                }, { sticky: true, direction: 'top', opacity: 0.9 });
            }
        }).addTo(estado.mapa);

        console.log('[OK] Calles visualizadas en el mapa');

        // Iniciar actualización de tráfico cada 2 segundos SIEMPRE en modo SUMO
        actualizarTraficoSUMO();
        estado.actualizacionTraficoInterval = setInterval(actualizarTraficoSUMO, 2000);

    } catch (error) {
        console.error('Error cargando calles SUMO:', error);
        alert('Error al cargar visualización de calles SUMO');
    }
}

async function actualizarEstadoSUMO() {
    try {
        // Usar un solo endpoint que ya agregue métricas
        const resp = await fetch(`${API_URL}/api/sumo/estado`);
        const data = await resp.json();

        if (!data.conectado) {
            console.warn('⚠️ SUMO no conectado');
            // Forzar caída de métricas a 0 en modo SUMO
            estado.__overridePromedios = { icv: 0, flujo: 0 };
            const sinteticaCero = [{
                interseccion_id: 'SUMO-AGREGADO',
                icv: 0,
                flujo: 0,
                velocidad: 0,
                cola: 0,
                num_vehiculos: 0,
                color: '#10b981',
                clasificacion: 'Fluido'
            }];
            actualizarDatosInterfaz(sinteticaCero, 'backend');
            return;
        }
        // Métricas agregadas del endpoint principal
        const totalVehiculos = data.vehiculos_totales || 0;
        const velocidadPromedio = data.velocidad_promedio || 0;
        const callesActivas = data.calles_con_trafico || 0;
        const congestionPromedio = data.congestion_promedio || 0;
        const semaforos = data.semaforos || 0;
        const tiempoSim = typeof data.tiempo_simulado_s === 'number' ? data.tiempo_simulado_s : 0;

        // Actualizar UI
        const elSemaforos = document.getElementById('sumo-semaforos');
        const elVehiculos = document.getElementById('sumo-vehiculos');
        const elCalles = document.getElementById('sumo-calles-activas');
        const elVelocidad = document.getElementById('sumo-velocidad');
        const elCongestion = document.getElementById('sumo-congestion');
        const elTiempo = document.getElementById('sumo-tiempo');

        if (elSemaforos) elSemaforos.textContent = semaforos;
        if (elVehiculos) elVehiculos.textContent = totalVehiculos;
        if (elCalles) elCalles.textContent = callesActivas;
        if (elVelocidad) elVelocidad.textContent = `${Number(velocidadPromedio).toFixed(1)} km/h`;
        if (elCongestion) elCongestion.textContent = `${Math.round(congestionPromedio * 100)}%`;
        if (elTiempo) elTiempo.textContent = `${Number(tiempoSim).toFixed(1)}s`;

        console.log('📊 SUMO:', { totalVehiculos, velocidadPromedio, callesActivas, congestionPromedio, semaforos, tiempoSim });

        // Importante: sin backend no generamos métricas sintéticas en modo SUMO.
        // Los datos de SUMO deben provenir del backend exclusivamente.
    } catch (error) {
        console.error('❌ Error actualizando estado SUMO:', error);
    }
}

async function actualizarTraficoSUMO() {
    if (estado.modoActual !== 'sumo') {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/sumo/trafico`);
        const data = await response.json();

        if (!data.calles || data.calles.length === 0) {
            return;
        }

        // Crear mapa de congestión por ID de calle con mínimos y micro-ruido si viene 0
        const congestionPorCalle = {};
        data.calles.forEach(calle => {
            let cong = typeof calle.congestion === 'number' ? calle.congestion : 0;
            if (cong <= 0) {
                const seed = (calle.id.charCodeAt(0) + (calle.id.charCodeAt(calle.id.length - 1) || 0)) % 97;
                const jitter = (Math.sin(Date.now() / 7000 + seed) + 1) * 0.01; // 0–0.02
                cong = 0.03 + jitter; // mínimo visible ~0.03–0.05
            }
            congestionPorCalle[calle.id] = Math.max(0.02, Math.min(0.99, cong));
        });

        // Umbrales dinámicos: si hay suficientes calles activas, usar percentiles 33/66
        const activasParaUmbrales = data.calles
            .filter(c => typeof c.congestion === 'number' && (c.vehiculos || 0) > 0)
            .map(c => c.congestion)
            .sort((a, b) => a - b);

        function pct(arr, p) {
            if (arr.length === 0) return 0;
            const idx = Math.min(arr.length - 1, Math.max(0, Math.floor((arr.length - 1) * p)));
            return arr[idx];
        }

        let tVerdeAmarillo = 0.3;
        let tAmarilloRojo = 0.6;
        if (activasParaUmbrales.length >= 12) { // con suficientes muestras, ajustar a cuantiles
            tVerdeAmarillo = pct(activasParaUmbrales, 0.33);
            tAmarilloRojo = pct(activasParaUmbrales, 0.66);
        }

        // Guardar último snapshot para tooltips
        estado.__ultimoSUMOCalles = data.calles;

        // Eliminar cualquier leyenda de tráfico SUMO si existiera (no debe visualizarse)
        if (estado.__leyendaSUMO) {
            try {
                const container = estado.__leyendaSUMO.getContainer && estado.__leyendaSUMO.getContainer();
                if (container && container.parentNode) container.parentNode.removeChild(container);
            } catch {}
            estado.__leyendaSUMO = null;
        }

        // HUD removido: no mostrar cantidad de vehículos ni velocidad promedio en el mapa
        if (estado.__hudSUMO) {
            try {
                const containerHud = estado.__hudSUMO.getContainer && estado.__hudSUMO.getContainer();
                if (containerHud && containerHud.parentNode) containerHud.parentNode.removeChild(containerHud);
            } catch {}
            estado.__hudSUMO = null;
        }

        // Actualizar colores de las calles (solo si visualización habilitada)
        if (estado.mostrarSUMOTrafico && estado.callesSUMO) {
        estado.callesSUMO.eachLayer(function(layer) {
            const feature = layer.feature;
            const idCalle = feature.properties.id;
            const congestion = congestionPorCalle[idCalle];

            if (congestion !== undefined) {
                // Determinar color según umbrales dinámicos
                let color;
                if (congestion < tVerdeAmarillo) {
                    color = '#10b981';  // Verde - fluido
                } else if (congestion < tAmarilloRojo) {
                    color = '#f59e0b';  // Amarillo - moderado
                } else {
                    color = '#ef4444';  // Rojo - congestionado
                }

                // Hacer más gruesa la línea en edges con muchos vehículos para visibilidad
                const v = congestionPorCalle[idCalle];
                let vehiculosEdge = (v !== undefined) ? (data.calles.find(c => c.id === idCalle)?.vehiculos || 0) : 0;
                if (vehiculosEdge <= 0) vehiculosEdge = 1; // mínimo visible
                const weight = vehiculosEdge >= 10 ? 5 : vehiculosEdge >= 5 ? 4 : 3;

                layer.setStyle({
                    color: color,
                    weight: weight,
                    opacity: 0.8
                });
            }
        });
        }

        // ==================== INTEGRACIÓN CON SISTEMA DE MÉTRICAS (ICV / Flujo) ====================
        // Transformar las calles en un conjunto de "métricas" compatibles con actualizarDatosInterfaz
        // Evitamos saturar la interfaz: tomamos solo las calles activas (vehículos > 0) y un máximo de 40
        const callesActivas = data.calles.filter(c => (c.vehiculos || 0) > 0);
        // Ordenar por número de vehículos descendente para priorizar las más relevantes
        callesActivas.sort((a, b) => (b.vehiculos || 0) - (a.vehiculos || 0));
        const seleccion = callesActivas.slice(0, 40);

        const metricas = seleccion.map(c => {
            // ICV: usar congestión con piso y micro-ruido si viene 0
            let icv = typeof c.congestion === 'number' ? c.congestion : 0;
            if (icv <= 0) {
                const seed = (c.id.charCodeAt(0) + (c.id.charCodeAt(c.id.length - 1) || 0)) % 97;
                const jitter = (Math.cos(Date.now() / 6000 + seed) + 1) * 0.01; // 0–0.02
                icv = 0.03 + jitter;
            }
            icv = Math.max(0.02, Math.min(0.99, icv));

            // Flujo: asegurar mínimo visible 1 veh
            let flujo = (c.vehiculos || 0);
            if (flujo <= 0) flujo = 1;

            const velocidad = typeof c.velocidad === 'number' ? c.velocidad : 0; // km/h
            const cola = 0; // No tenemos longitud de cola por edge, dejamos 0 por ahora
            const color = icv < 0.3 ? 'verde' : icv < 0.6 ? 'amarillo' : 'rojo';
            return {
                interseccion_id: `CALLE:${c.id}`,
                icv: icv,
                flujo: flujo,
                velocidad: velocidad,
                cola: cola,
                num_vehiculos: flujo,
                color: color,
                clasificacion: icv < 0.3 ? 'Fluido' : icv < 0.6 ? 'Moderado' : 'Congestionado'
            };
        });

        // Además, agregamos métricas por intersección real basadas en proximidad a edges SUMO
        const indexCentroides = {};
        try {
            for (const feat of (estado.callesGeoJSON?.features || [])) {
                const id = feat.properties?.id;
                const geom = feat.geometry;
                if (!id || !geom || geom.type !== 'LineString') continue;
                const cen = _centroideLinea(geom.coordinates);
                if (cen) indexCentroides[id] = cen;
            }
        } catch {}

        const metricasInter = [];
        for (const inter of (typeof INTERSECCIONES_LIMA !== 'undefined' ? INTERSECCIONES_LIMA : [])) {
            const latI = inter.latitud, lonI = inter.longitud;
            // Buscar edges cercanos activos
            const vecinos = [];
            for (const c of data.calles) {
                const id = c.id;
                const cen = indexCentroides[id];
                if (!cen) continue;
                const d = _distanciaHaversine(latI, lonI, cen.lat, cen.lon);
                if (d <= 800 && (c.vehiculos||0) > 0) {
                    vecinos.push({ d, c });
                }
            }
            vecinos.sort((a,b)=>a.d-b.d);
            const usados = vecinos.slice(0, 6); // tomar hasta 6 más cercanos

            let icv = 0, flujo = 0, velocidad = 0;
            if (usados.length > 0) {
                icv = usados.reduce((s, x)=> s + (x.c.congestion||0), 0) / usados.length;
                velocidad = usados.reduce((s, x)=> s + (x.c.velocidad||0), 0) / usados.length;
                // flujo: estimar como suma de vehículos con ponderación por distancia (más cerca, más peso)
                const sumPesos = usados.reduce((s,x)=> s + (1/(1+x.d/200)), 0);
                flujo = usados.reduce((s,x)=> s + (x.c.vehiculos||0) * (1/(1+x.d/200)), 0) / Math.max(1, sumPesos);
                // escalar a veh/min aproximado (variación): multiplicar por 2 para rango visible
                flujo = flujo * 2;
                // añadir variación temporal suave (oscilación + ruido leve) para evitar constancia
                const seed = (inter.id.charCodeAt(0) + (inter.id.charCodeAt(inter.id.length - 1) || 0)) % 97;
                const t = Date.now() / 12000; // periodo ~12s
                const oscil = 0.15 + 0.10 * Math.sin(t + seed);   // ±10%
                const micro = 0.95 + 0.10 * Math.sin(t * 1.7 + seed * 1.3); // micro variación
                flujo = flujo * oscil * micro;
            } else {
                // Sin vecinos activos: aplicar mínimos y microvariación para no quedar en 0
                const seed = (inter.id.charCodeAt(0) + (inter.id.charCodeAt(inter.id.length - 1) || 0)) % 97;
                const jitter = (Math.sin(Date.now() / 8000 + seed) + 1) * 0.01; // 0–0.02
                icv = 0.03 + jitter;
                // Flujo mínimo con oscilación perceptible
                const t = Date.now() / 10000;
                flujo = 1 * (1 + 0.6 * Math.abs(Math.sin(t + seed))); // 1–1.6
                velocidad = 0;
            }

            // Clamps finales por seguridad
            icv = Math.max(0.02, Math.min(0.99, icv));
            flujo = Math.max(1, Math.min(120, flujo));

            // Aplicar regla de color: amarillo desde 20%
            const color = icv < 0.20 ? '#10b981' : icv < 0.58 ? '#f59e0b' : '#ef4444';

            metricasInter.push({
                interseccion_id: inter.id,
                interseccion_nombre: inter.nombre,
                icv: Number(icv.toFixed(3)),
                flujo: Number(flujo.toFixed(1)),
                velocidad: Number((velocidad||0).toFixed(1)),
                cola: 0,
                num_vehiculos: Math.round(flujo),
                color: color,
                clasificacion: icv < 0.20 ? 'Fluido' : icv < 0.58 ? 'Moderado' : 'Congestionado'
            });
        }

        if (metricas.length > 0 || metricasInter.length > 0) {
            // Guardar resumen global de SUMO para usarlo como sesgo en simulación
            const icvProm = activasParaUmbrales.length > 0 ? (
                activasParaUmbrales.reduce((a,b)=>a+b,0) / activasParaUmbrales.length
            ) : null;
            const velocidadesActivas = data.calles
                .filter(c => (c.vehiculos||0)>0 && typeof c.velocidad==='number')
                .map(c => c.velocidad);
            const velProm = velocidadesActivas.length>0 ? (
                velocidadesActivas.reduce((a,b)=>a+b,0) / velocidadesActivas.length
            ) : null;
            const flujoProm = data.calles
                .filter(c => (c.vehiculos||0)>0)
                .reduce((a,c)=>a + (c.vehiculos||0), 0) / Math.max(1, data.calles.filter(c => (c.vehiculos||0)>0).length);

            estado.metricasSUMOResumen = {
                icvPromedio: icvProm,
                velocidadPromedio: velProm,
                flujoPromedio: flujoProm
            };

            // Si el backend proporcionó promedios agregados, establecer override para gráficos
            if (typeof data.icv_red_promedio === 'number' || typeof data.flujo_promedio === 'number') {
                estado.__overridePromedios = {
                    icv: typeof data.icv_red_promedio === 'number' ? data.icv_red_promedio : undefined,
                    flujo: typeof data.flujo_promedio === 'number' ? data.flujo_promedio : undefined
                };
            }

            // Alimentar el sistema unificado para que se actualicen:
            // - ICV promedio
            // - Flujo promedio
            // - Contadores de calles fluidas / moderadas / congestionadas
            // - Tarjetas y gráficos
            // Primero intersecciones reales (activarlas en SUMO), luego edges si quieres ver detalle
            if (metricasInter.length > 0) {
                actualizarDatosInterfaz(metricasInter, 'backend');
            } else if (metricas.length > 0) {
                actualizarDatosInterfaz(metricas, 'backend');
            }
        }

        // Si no hay métricas de calles activas, aún así actualizar promedios para gráficos en modo SUMO
        if (metricas.length === 0 && metricasInter.length === 0 && (typeof data.icv_red_promedio === 'number' || typeof data.flujo_promedio === 'number')) {
            estado.__overridePromedios = {
                icv: typeof data.icv_red_promedio === 'number' ? data.icv_red_promedio : undefined,
                flujo: typeof data.flujo_promedio === 'number' ? data.flujo_promedio : undefined
            };
            // Enviar una métrica sintética mínima para que la interfaz se refresque
            const sintetica = [{
                interseccion_id: 'SUMO-AGREGADO',
                icv: Math.max(0.02, estado.__overridePromedios.icv || 0.02),
                flujo: Math.max(0.02, estado.__overridePromedios.flujo || 0.02),
                velocidad: 0,
                cola: 0,
                num_vehiculos: Math.max(1, Math.round((estado.__overridePromedios.flujo || 1))),
                color: '#f59e0b',
                clasificacion: 'Moderado'
            }];
            actualizarDatosInterfaz(sintetica, 'backend');
        }

    } catch (error) {
        console.error('Error actualizando tráfico SUMO:', error);
    }
}

// ==================== SESGO POR PROXIMIDAD A CALLES SUMO ====================
function _distanciaHaversine(lat1, lon1, lat2, lon2) {
    const R = 6371000; // m
    const toRad = x => x * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function _centroideLinea(coords) {
    // coords: [[lon,lat], ...]
    if (!coords || coords.length === 0) return null;
    let lat = 0, lon = 0;
    coords.forEach(([x,y]) => { lon += x; lat += y; });
    const n = coords.length;
    return { lat: lat/n, lon: lon/n };
}

function calcularSesgoPorProximidadSUMO(inter) {
    // Devuelve un peso 0–1: cerca de calles con tráfico → mayor peso SUMO
    if (!estado.callesGeoJSON || !estado.__ultimoSUMOCalles) return 0.0;
    if (estado.__proxSUMOCache[inter.id]) return estado.__proxSUMOCache[inter.id];

    const { latitud: latI, longitud: lonI } = inter;
    let mejor = Infinity;
    for (const feat of estado.callesGeoJSON.features) {
        const id = feat.properties?.id;
        const snap = estado.__ultimoSUMOCalles.find(c => c.id === id);
        if (!snap || (snap.vehiculos||0) <= 0) continue; // considerar solo calles activas
        const geom = feat.geometry;
        if (!geom || geom.type !== 'LineString') continue;
        const cen = _centroideLinea(geom.coordinates);
        if (!cen) continue;
        const d = _distanciaHaversine(latI, lonI, cen.lat, cen.lon);
        if (d < mejor) mejor = d;
    }

    // Mapear distancia a peso: <200m → 1.0, 200–1000m → decae, >2km → ~0
    let peso = 0.0;
    if (isFinite(mejor)) {
        if (mejor <= 200) peso = 1.0;
        else if (mejor <= 1000) peso = 0.6 * (1 - (mejor - 200) / 800) + 0.4; // decaimiento lineal
        else if (mejor <= 2000) peso = 0.2 * (1 - (mejor - 1000) / 1000);
        else peso = 0.0;
    }
    estado.__proxSUMOCache[inter.id] = Math.max(0, Math.min(1, peso));
    return estado.__proxSUMOCache[inter.id];
}

function limpiarCallesSUMO() {
    if (estado.callesSUMO) {
        estado.mapa.removeLayer(estado.callesSUMO);
        estado.callesSUMO = null;
        estado.callesGeoJSON = null;
        console.log('Calles SUMO limpiadas del mapa');
    }
    // Remover leyenda y HUD si existen
    try {
        const containerLey = estado.__leyendaSUMO && estado.__leyendaSUMO.getContainer && estado.__leyendaSUMO.getContainer();
        if (containerLey && containerLey.parentNode) containerLey.parentNode.removeChild(containerLey);
        estado.__leyendaSUMO = null;
    } catch {}
    try {
        const containerHud = estado.__hudSUMO && estado.__hudSUMO.getContainer && estado.__hudSUMO.getContainer();
        if (containerHud && containerHud.parentNode) containerHud.parentNode.removeChild(containerHud);
        estado.__hudSUMO = null;
    } catch {}
    if (estado.actualizacionTraficoInterval) {
        clearInterval(estado.actualizacionTraficoInterval);
        estado.actualizacionTraficoInterval = null;
    }
}

// ==================== WEBSOCKET - CONEXION CRITICA ====================

function conectarWebSocket() {
    console.log('Conectando a WebSocket...');

    estado.websocket = new WebSocket(WS_URL);

    estado.websocket.onopen = () => {
        console.log('[OK] WebSocket conectado');
        document.getElementById('connection-status').textContent = 'CONECTADO';
        document.querySelector('.status-dot').classList.add('pulsing');
    };

    estado.websocket.onmessage = (event) => {
        try {
            const mensaje = JSON.parse(event.data);
            procesarMensajeWebSocket(mensaje);
        } catch (error) {
            console.error('Error procesando mensaje WebSocket:', error);
        }
    };

    estado.websocket.onerror = (error) => {
        console.error('Error WebSocket:', error);
        document.getElementById('connection-status').textContent = 'ERROR';
    };

    estado.websocket.onclose = () => {
        console.log('WebSocket desconectado. Reintentando en 3s...');
        document.getElementById('connection-status').textContent = 'DESCONECTADO';
        document.querySelector('.status-dot').classList.remove('pulsing');

        // Marcar backend como desconectado
        estado.backendConectado = false;

        // Iniciar simulación local como fallback si estamos en modo simulador
        if (estado.modoActual === 'simulador' && !estado.simulacionInterval) {
            console.warn('Backend desconectado - Iniciando simulación local como fallback');
            iniciarSimulacion();
        }

        // Reconectar automáticamente
        setTimeout(() => {
            if (estado.websocket.readyState === WebSocket.CLOSED) {
                conectarWebSocket();
            }
        }, 3000);
    };
}

function procesarMensajeWebSocket(mensaje) {
    const { tipo, datos } = mensaje;

    console.log(`[WebSocket] Mensaje recibido - Tipo: ${tipo}`, datos);

    switch (tipo) {
        case 'metricas_actualizadas':
            // En modo simulador (demo visual), ignorar métricas backend para evitar sobrescritura
            if (estado.modoActual === 'simulador') {
                console.log('[WebSocket] Ignorado en modo simulador (demo visual sin backend)');
                break;
            }
            console.log(`[WebSocket] Actualizando ${datos.length} métricas...`);
            actualizarMetricasDesdeBackend(datos);
            break;

        case 'ola_verde_activada':
            console.log('[WebSocket] Ola verde activada');
            mostrarOlaVerdeActivada(datos);
            break;

        case 'ola_verde_desactivada':
            console.log('[WebSocket] Ola verde desactivada por el backend');
            desactivarOlaVerde();
            break;

        case 'ola_verde_completada':
            console.log('[WebSocket] Ola verde completada exitosamente');
            desactivarOlaVerde();
            break;

        case 'modo_cambiado':
            console.log(`[WebSocket] Modo cambiado a: ${datos.modo}`);
            break;

        default:
            console.warn('[WebSocket] Mensaje desconocido:', tipo);
    }
}

function actualizarMetricasDesdeBackend(metricas) {
    console.log(`[Backend] Recibidas ${metricas.length} métricas, actualizando interfaz...`);
    // Función actualizada - ahora usa la función unificada
    actualizarDatosInterfaz(metricas, 'backend');
}

function actualizarTarjetaMetrica(interseccionId, metricas) {
    // Buscar o crear tarjeta de métrica
    let tarjeta = document.querySelector(`[data-interseccion="${interseccionId}"]`);

    if (!tarjeta) {
        const container = document.getElementById('metricas-container');
        tarjeta = document.createElement('div');
        tarjeta.className = 'metrica-card';
        tarjeta.setAttribute('data-interseccion', interseccionId);
        container.appendChild(tarjeta);
    }

    const interseccion = INTERSECCIONES_LIMA.find(i => i.id === interseccionId);
    if (!interseccion) return;

    // Determinar color según ICV
    let colorClass = 'verde';
    if (metricas.icv >= 0.6) colorClass = 'rojo';
    else if (metricas.icv >= 0.3) colorClass = 'amarillo';

    tarjeta.innerHTML = `
        <div class="metrica-header">
            <span class="metrica-nombre">${interseccion.nombre || interseccionId}</span>
            <span class="metrica-icv icv-${colorClass}">${metricas.icv.toFixed(2)}</span>
        </div>
        <div class="metrica-detalles">
            <div class="metrica-detalle">
                <span class="label">Flujo:</span>
                <span class="valor">${metricas.flujo.toFixed(1)} veh/min</span>
            </div>
            <div class="metrica-detalle">
                <span class="label">Velocidad:</span>
                <span class="valor">${metricas.velocidad.toFixed(1)} km/h</span>
            </div>
        </div>
    `;
}

// ==================== MODO Procesador Video ====================

let streamVideo = null;
let procesandoVideo = false;
let intervaloVideo = null;
let intervaloMetricas = null;
// Elemento video usado para getUserMedia (si aplica)
let _videoElementLocal = null;
let _rafIdLocalVideo = null;

// Inicia la cámara local (getUserMedia) y prepara un elemento <video>
async function intentarCamaraLocal() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('getUserMedia no soportado en este navegador');
    }

    // Si ya existe la cámara local, reutilizarla
    if (_videoElementLocal && _videoElementLocal.srcObject) {
        return _videoElementLocal;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });

    const video = document.createElement('video');
    video.style.display = 'none';
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.srcObject = stream;
    document.body.appendChild(video);

    // Esperar a que el video pueda reproducirse
    await video.play();

    _videoElementLocal = video;
    streamVideo = video; // marcar como stream activo para la lógica existente

    return video;
}

function detenerCamaraLocal() {
    if (_rafIdLocalVideo) {
        cancelAnimationFrame(_rafIdLocalVideo);
        _rafIdLocalVideo = null;
    }

    if (_videoElementLocal) {
        try {
            const s = _videoElementLocal.srcObject;
            if (s && s.getTracks) {
                s.getTracks().forEach(t => t.stop());
            }
        } catch (e) {
            console.warn('Error deteniendo tracks de la cámara local:', e);
        }

        if (_videoElementLocal.parentNode) {
            _videoElementLocal.parentNode.removeChild(_videoElementLocal);
        }
        _videoElementLocal = null;
    }
}

async function activarModoVideo(videoIndex) {
    try {
        console.log(`Activando MIR ${String(videoIndex).padStart(3, '0')}...`);

        const canvas = document.getElementById('video-canvas');
        const ctx = canvas.getContext('2d');

        let streamUrl;
        const esCamara = (videoIndex === 0);

        if (esCamara) {
            console.log('Conectando a camara de laptop...');
            // Endpoint remoto (fallback) para la cámara en el backend
            streamUrl = `${API_URL}/api/video/stream-camera`;
        } else {
            console.log(`Conectando a video procesado (indice ${videoIndex - 1})...`);
            streamUrl = `${API_URL}/api/video/stream-video-index/${videoIndex - 1}?t=${Date.now()}`;
        }

        console.log('URL del stream:', streamUrl);
        procesandoVideo = true;

        // Para la cámara MIR000, usar SIEMPRE el stream del backend con YOLO
        if (esCamara) {
            console.log('Conectando a stream de cámara con YOLO desde backend...');

            // Crear elemento img para recibir el stream MJPEG del backend
            const imgElement = document.createElement('img');
            imgElement.style.display = 'none';
            document.body.appendChild(imgElement);

            imgElement.src = streamUrl;
            console.log('Iniciando stream de cámara con análisis YOLO...');

            const actualizarCanvas = () => {
                if (!procesandoVideo || !modoEsProcesadorVideo()) {
                    detenerModoVideo();
                    return;
                }

                try {
                    if (imgElement.complete && imgElement.naturalHeight !== 0) {
                        ctx.drawImage(imgElement, 0, 0, canvas.width, canvas.height);
                    }
                } catch (error) {
                    console.error('Error dibujando frame de cámara:', error);
                }

                requestAnimationFrame(actualizarCanvas);
            };

            imgElement.onload = () => {
                imgElement._retryCount = 0;
                console.log('✓ Stream de cámara con YOLO conectado');
                actualizarCanvas();
            };

            imgElement.onerror = () => {
                imgElement._retryCount = (imgElement._retryCount || 0) + 1;
                console.error(`Error conectando al stream de cámara (intento ${imgElement._retryCount})`);
                console.error('URL intentada:', streamUrl);

                if (imgElement._retryCount <= 5) {
                    setTimeout(() => {
                        try {
                            imgElement.src = `${streamUrl}?t=${Date.now()}&_r=${imgElement._retryCount}`;
                        } catch (e) {
                            console.error('Error reintentando cargar stream de cámara:', e);
                        }
                    }, 500 * imgElement._retryCount);
                } else {
                    console.error('No se pudo conectar al stream de cámara después de varios intentos.');
                    detenerModoVideo();
                }
            };

            streamVideo = imgElement;

        } else {
            // Para videos pregrabados, usar el método original que funciona
            const imgElement = document.createElement('img');
            imgElement.style.display = 'none';
            document.body.appendChild(imgElement);

            imgElement.src = streamUrl;
            console.log('Cargando video procesado:', streamUrl);

            const actualizarCanvas = () => {
                if (!procesandoVideo || !modoEsProcesadorVideo()) {
                    detenerModoVideo();
                    return;
                }

                try {
                    if (imgElement.complete && imgElement.naturalHeight !== 0) {
                        ctx.drawImage(imgElement, 0, 0, canvas.width, canvas.height);
                    }
                } catch (error) {
                    console.error('Error dibujando frame:', error);
                }

                requestAnimationFrame(actualizarCanvas);
            };

            imgElement.onload = () => {
                // Resetear contador de reintentos y arrancar render
                imgElement._retryCount = 0;
                console.log('✓ Video procesado conectado');
                actualizarCanvas();
            };

            imgElement.onerror = () => {
                imgElement._retryCount = (imgElement._retryCount || 0) + 1;
                console.error(`Error conectando al stream de video (intento ${imgElement._retryCount})`);
                console.error('URL intentada:', streamUrl);

                if (imgElement._retryCount <= 5) {
                    // Reintentar con timestamp nuevo para evitar cache
                    setTimeout(() => {
                        try {
                            imgElement.src = `${streamUrl.split('?')[0]}?t=${Date.now()}&_r=${imgElement._retryCount}`;
                        } catch (e) {
                            console.error('Error reintentando cargar video procesado:', e);
                        }
                    }, 500 * imgElement._retryCount);
                } else {
                    console.warn('No se pudo conectar al stream de video después de varios intentos. Intentando usar cámara local (getUserMedia) como fallback.');
                    intentarCamaraLocal().catch(err => {
                        console.error('Fallback getUserMedia falló:', err);
                        detenerModoVideo();
                    });
                }
            };

            streamVideo = imgElement;
        }

        const actualizarMetricas = async () => {
            try {
                const response = await fetch(`${API_URL}/api/video/metricas-stream`);
                const metricas = await response.json();

                document.getElementById('video-vehiculos').textContent = metricas.num_vehiculos || 0;
                document.getElementById('video-fps').textContent = metricas.fps || 0;
                document.getElementById('video-icv').textContent = (metricas.icv || 0).toFixed(2);
            } catch (error) {
                console.error('Error obteniendo metricas:', error);
                // Mostrar valores por defecto en caso de error
                document.getElementById('video-vehiculos').textContent = '0';
                document.getElementById('video-fps').textContent = '0';
                document.getElementById('video-icv').textContent = '0.00';
            }
        };

        // Actualizar métricas
        if (intervaloMetricas) {
            clearInterval(intervaloMetricas);
        }
        intervaloMetricas = setInterval(actualizarMetricas, 1000);
        console.log('✓ Metricas activadas - actualizando cada segundo');

        console.log('[OK] Modo video activado');

    } catch (error) {
        console.error('Error activando modo video:', error);
        alert('Error al activar el modo video. Ver consola para mas detalles.');
        detenerModoVideo();
    }
}

function cargarInterseccionesSimulador() {
    const selector = document.getElementById('selector-interseccion-cam');
    selector.innerHTML = '<option value="">Selecciona interseccion...</option>';

    estado.intersecciones.forEach(inter => {
        const option = document.createElement('option');
        option.value = inter.id;
        option.textContent = inter.nombre;
        selector.appendChild(option);
    });

    selector.onchange = seleccionarInterseccionCamara;

    // Nota: ya no se auto-selecciona ni se activa el video automáticamente
    // El usuario debe seleccionar manualmente la intersección y activar el Procesador Video
}

async function cargarInterseccionesVideo() {
    try {
        const response = await fetch(`${API_URL}/api/video/listar-videos-procesados`);
        const data = await response.json();

        const selector = document.getElementById('selector-interseccion-cam');
        selector.innerHTML = '';

        const optionSelecciona = document.createElement('option');
        optionSelecciona.value = '';
        optionSelecciona.textContent = 'Selecciona MIR...';
        selector.appendChild(optionSelecciona);

        const optionCamara = document.createElement('option');
        optionCamara.value = '0';
        optionCamara.textContent = 'MIR 000 - Camara Laptop';
        selector.appendChild(optionCamara);

        // Agregar MIR 001 y MIR 002 según los videos guardados por la última ejecución
        if (data.videos && data.videos.length > 0) {
            const nombres = data.videos.map(v => v.nombre || v); // soporte para string o objeto
            // MIR 001 corresponde al índice 0
            const opt1 = document.createElement('option');
            opt1.value = '1';
            opt1.textContent = `MIR 001 - ${nombres[0] || 'Video 1'}`;
            selector.appendChild(opt1);

            // MIR 002 corresponde al índice 1 si existe
            if (data.videos.length > 1) {
                const opt2 = document.createElement('option');
                opt2.value = '2';
                opt2.textContent = `MIR 002 - ${nombres[1] || 'Video 2'}`;
                selector.appendChild(opt2);
            }
        }

        selector.value = '';

        selector.onchange = async () => {
            const selectedValue = selector.value;
            if (selectedValue === '') {
                detenerModoVideo();
                estadoVideo.activo = false;
                const indicator = document.querySelector('.camera-mode-indicator');
                const texto = document.getElementById('modo-camara-texto');
                indicator.classList.remove('active');
                texto.textContent = 'Desactivado';
            } else {
                const videoIndex = parseInt(selectedValue);
                if (procesandoVideo) {
                    detenerModoVideo();
                }

                estadoVideo.activo = true;
                const indicator = document.querySelector('.camera-mode-indicator');
                const texto = document.getElementById('modo-camara-texto');
                indicator.classList.add('active');
                texto.textContent = 'Activo';

                await activarModoVideo(videoIndex);
            }
        };

        // Nota: no se auto-activa la cámara ni el video aquí. El usuario debe seleccionar y activar manualmente.

    } catch (error) {
        console.error('Error cargando videos:', error);
        alert('Error cargando lista de videos. Asegurate de que el servidor backend este corriendo.');
    }
}

function detenerModoVideo() {
    procesandoVideo = false;

    if (intervaloVideo) {
        clearInterval(intervaloVideo);
        intervaloVideo = null;
    }

    if (intervaloMetricas) {
        clearInterval(intervaloMetricas);
        intervaloMetricas = null;
    }

    if (streamVideo) {
        if (streamVideo instanceof HTMLImageElement) {
            streamVideo.src = '';
            if (streamVideo.parentNode) {
                streamVideo.parentNode.removeChild(streamVideo);
            }
        } else if (streamVideo.getTracks) {
            streamVideo.getTracks().forEach(track => track.stop());
        }
        streamVideo = null;
    }

    // Limpiar TODOS los elementos img que puedan estar cargando streams
    const imgElements = document.querySelectorAll('img[src*="/api/video/stream"]');
    imgElements.forEach(img => {
        img.src = '';
        if (img.parentNode) {
            img.parentNode.removeChild(img);
        }
    });

    // Detener y limpiar cámara local si estaba activa
    try {
        detenerCamaraLocal();
    } catch (e) {
        console.warn('Error al detener cámara local:', e);
    }

    const canvas = document.getElementById('video-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    document.getElementById('video-vehiculos').textContent = '0';
    document.getElementById('video-icv').textContent = '0.00';
    document.getElementById('video-fps').textContent = '0';

    console.log('[OK] Modo video detenido');
}

function dibujarDetecciones(ctx, detecciones, canvasWidth, canvasHeight) {
    // Configurar estilo para dibujar
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.font = '14px Arial';
    ctx.fillStyle = '#00ff00';

    detecciones.forEach(det => {
        // Las coordenadas vienen normalizadas [0-1], escalar al canvas
        const x1 = det.bbox[0] * canvasWidth;
        const y1 = det.bbox[1] * canvasHeight;
        const x2 = det.bbox[2] * canvasWidth;
        const y2 = det.bbox[3] * canvasHeight;

        // Dibujar rectángulo
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Dibujar etiqueta
        const label = `${det.clase} ${(det.confianza * 100).toFixed(0)}%`;
        ctx.fillText(label, x1, y1 - 5);
    });
}

// ==================== MEJORA DE OLAS VERDES ====================

async function mostrarOlaVerdeActivada(datos) {
    console.log('📍 Mostrando ola verde:', datos);
    console.log('   ¿Tiene hospital destino?', !!datos._hospitalDestino);
    if (datos._hospitalDestino) {
        console.log('   Hospital:', datos._hospitalDestino.nombre);
    }

    // Limpiar completamente cualquier ola verde anterior
    desactivarOlaVerde();
    // Asegurar que los íconos de hospitales estén visibles mientras la ola esté activa (si aplica)
    try {
        const tipoVehiculo = datos.vehiculo?.tipo;
        if (tipoVehiculo === 'ambulancia') {
            mostrarMarcadoresHospitales();
        }
    } catch {}

    // Obtener ruta de la ola verde
    const ruta = datos.ruta || [];
    if (ruta.length < 2) {
        console.log('Ruta de ola verde vacía o inválida');
        return;
    }

    // Calcular ruta y destino
    let coordenadasRutaReal;
    let destinoFinalCoords;
    let nombreDestino = 'Destino';
    let iconoDestino = '🏁';

    console.log('🔍 Verificando modo de ruta...');
    console.log('   datos._hospitalDestino:', datos._hospitalDestino);
    console.log('   Tipo:', typeof datos._hospitalDestino);
    
    if (datos._hospitalDestino && datos._hospitalDestino.lat && datos._hospitalDestino.lon) {
        // ========== MODO HOSPITAL: Ruta ÓPTIMA directa sin intersecciones intermedias ==========
        console.log('🔴 DETECTADO HOSPITAL DESTINO - Modo ruta directa activado');
        const hosp = datos._hospitalDestino;
        console.log('   Hospital:', hosp);
        const origenInter = INTERSECCIONES_LIMA.find(i => i.id === ruta[0]);
        
        if (!origenInter) {
            console.error('No se encontró intersección origen');
            return;
        }

        const origenCoords = [origenInter.latitud, origenInter.longitud];
        destinoFinalCoords = [hosp.lat, hosp.lon];
        nombreDestino = hosp.nombre;
        iconoDestino = '🏥';
        
        console.log('🏥 MODO HOSPITAL - Ruta directa óptima');
        console.log('   Desde:', ruta[0], origenCoords);
        console.log('   Hasta:', nombreDestino, destinoFinalCoords);
        
        // Calcular ruta ÓPTIMA directa con Mapbox (solo origen y hospital)
        // Esto usa el algoritmo de Mapbox para encontrar la ruta más rápida/corta
        try {
            const rutaMapbox = await obtenerRutaMapbox(origenCoords, destinoFinalCoords, 'driving');
            
            if (rutaMapbox && rutaMapbox.geometry && rutaMapbox.geometry.coordinates) {
                coordenadasRutaReal = rutaMapbox.geometry.coordinates.map(c => [c[1], c[0]]);
                const distanciaKm = (rutaMapbox.distance / 1000).toFixed(2);
                const tiempoMin = (rutaMapbox.duration / 60).toFixed(1);
                const velocidadProm = ((rutaMapbox.distance / 1000) / (rutaMapbox.duration / 3600)).toFixed(1);
                
                console.log('   ✅ Ruta óptima calculada:');
                console.log('      📏 Distancia:', distanciaKm, 'km');
                console.log('      ⏱️  Tiempo estimado:', tiempoMin, 'min');
                console.log('      🚗 Velocidad promedio:', velocidadProm, 'km/h');
                if (rutaMapbox.weight) console.log('      ⚖️  Peso de ruta:', rutaMapbox.weight.toFixed(1));
                
                // Guardar datos de Mapbox para mostrar en el panel
                datos._datosMapbox = {
                    distance: rutaMapbox.distance,
                    duration: rutaMapbox.duration,
                    weight: rutaMapbox.weight,
                    weight_name: rutaMapbox.weight_name
                };
            } else {
                console.warn('   ⚠️  Mapbox falló, usando línea directa');
                coordenadasRutaReal = [origenCoords, destinoFinalCoords];
            }
        } catch (error) {
            console.warn('   ❌ Error Mapbox:', error);
            coordenadasRutaReal = [origenCoords, destinoFinalCoords];
        }
    } else {
        // ========== MODO INTERSECCIÓN: Ruta directa (igual que hospital) ==========
        const destinoInter = INTERSECCIONES_LIMA.find(i => i.id === ruta[ruta.length - 1]);
        
        if (!destinoInter) {
            console.error('No se encontró intersección destino');
            return;
        }

        const destinoCoords = [destinoInter.latitud, destinoInter.longitud];
        destinoFinalCoords = destinoCoords;
        nombreDestino = destinoInter.nombre;
        iconoDestino = '🏁';
        
        console.log('🚦 Destino: Intersección -', nombreDestino);
        console.log('🚗 Calculando ruta directa óptima');
        
        // Calcular ruta DIRECTA con Mapbox (solo origen y destino)
        try {
            const rutaMapbox = await obtenerRutaMapbox(origenCoords, destinoCoords, 'driving');
            
            if (rutaMapbox && rutaMapbox.geometry && rutaMapbox.geometry.coordinates) {
                coordenadasRutaReal = rutaMapbox.geometry.coordinates.map(c => [c[1], c[0]]);
                
                datos._datosMapbox = {
                    distance: rutaMapbox.distance,
                    duration: rutaMapbox.duration,
                    weight: rutaMapbox.weight,
                    weight_name: rutaMapbox.weight_name
                };
                
                const distanciaKm = (rutaMapbox.distance / 1000).toFixed(2);
                const tiempoMin = (rutaMapbox.duration / 60).toFixed(1);
                console.log('   ✅ Ruta calculada:', distanciaKm, 'km,', tiempoMin, 'min');
            } else {
                console.warn('   ⚠️  Mapbox falló, usando línea directa');
                coordenadasRutaReal = [origenCoords, destinoCoords];
            }
        } catch (error) {
            console.warn('   ❌ Error Mapbox:', error);
            coordenadasRutaReal = [origenCoords, destinoCoords];
        }
    }

    // Verificar qué coordenadas se van a dibujar
    console.log('📍 FINAL - Dibujando polyline con', coordenadasRutaReal ? coordenadasRutaReal.length : 0, 'puntos');
    if (coordenadasRutaReal && coordenadasRutaReal.length > 0) {
        console.log('   Primera coord:', coordenadasRutaReal[0]);
        console.log('   Última coord:', coordenadasRutaReal[coordenadasRutaReal.length - 1]);
    }
    
    estado.olaVerdeActiva = L.polyline(coordenadasRutaReal, {
        color: '#10b981',  // Verde brillante
        weight: 8,
        opacity: 0.9,
        dashArray: '15, 10',
        lineCap: 'round',
        lineJoin: 'round',
        className: 'ruta-emergencia-animada'
    }).addTo(estado.mapa);
    console.log('✓ Polyline dibujada en el mapa');

    // Inicializar array de marcadores si no existe
    if (!estado.marcadoresOlaVerde) {
        estado.marcadoresOlaVerde = [];
    }

    // Agregar marcadores en origen y destino
    const origen = coordenadasRutaReal[0];
    const destino = destinoFinalCoords;  // Usar destino final (hospital o intersección)

    const markerOrigen = L.marker(origen, {
        icon: L.divIcon({
            html: '<div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 8px; border-radius: 50%; font-size: 24px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.5); border: 3px solid white;">🚦</div>',
            className: '',
            iconSize: [50, 50]
        })
    }).addTo(estado.mapa).bindPopup('<b style="color: #10b981;">Origen</b>');

    // Marcador de destino (hospital o intersección) - oculto visualmente
    const markerDestino = L.marker(destino, {
        icon: L.divIcon({
            html: `<div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 8px; border-radius: 50%; font-size: 24px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5); border: 3px solid white; opacity: 0;">${iconoDestino}</div>`,
            className: '',
            iconSize: [50, 50]
        })
    }).addTo(estado.mapa).bindPopup(`<b style="color: #ef4444;">${nombreDestino}</b>`);

    estado.marcadoresOlaVerde.push(markerOrigen, markerDestino);

    // Centrar mapa en la ruta (usar coordenadas reales)
    estado.mapa.fitBounds(coordenadasRutaReal);

    // Extraer datos reales de Mapbox si están disponibles
    let datosMapbox = datos._datosMapbox || {};
    let distanciaKm = datosMapbox.distance ? (datosMapbox.distance / 1000).toFixed(2) : ((datos.distancia_total || 0) / 1000).toFixed(2);
    let tiempoMin = datosMapbox.duration ? (datosMapbox.duration / 60).toFixed(1) : ((datos.tiempo_estimado || 0) / 60).toFixed(1);
    let velocidadPromedio = datosMapbox.distance && datosMapbox.duration 
        ? ((datosMapbox.distance / 1000) / (datosMapbox.duration / 3600)).toFixed(1) 
        : '-';
    
    // Actualizar panel de olas verdes con datos reales de Mapbox
    const container = document.getElementById('olas-verdes-container');
    const iconoVehiculo = datos.vehiculo?.tipo === 'ambulancia' ? '🚑' : 
                          datos.vehiculo?.tipo === 'bomberos' ? '🚒' : '🚨';
    const tipoVehiculo = datos.vehiculo?.tipo || 'Emergencia';
    const destinoTexto = nombreDestino !== 'Destino' ? nombreDestino : `${ruta[ruta.length - 1]}`;
    
    container.innerHTML = `
        <div class="metrica-card" style="background: rgba(16, 185, 129, 0.2); border-left: 3px solid #10b981; margin-bottom: 0;">
            <div class="metrica-header" style="margin-bottom: 0.6rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.5rem;">${iconoVehiculo}</span>
                    <div style="flex: 1;">
                        <div class="metrica-nombre" style="font-size: 0.8rem; margin-bottom: 0.1rem;">Ola Verde Activa</div>
                        <div style="font-size: 0.65rem; color: rgba(255,255,255,0.7);">${tipoVehiculo.toUpperCase()}</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.4rem;">
                    <div class="metrica-icv" style="background: #10b981; font-size: 0.7rem; padding: 0.2rem 0.6rem;">
                        ACTIVA
                    </div>
                    <button onclick="desactivarOlaVerde()" style="background: #ef4444; color: white; border: none; padding: 0.3rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.7rem; transition: all 0.2s;" onmouseover="this.style.background='#dc2626'" onmouseout="this.style.background='#ef4444'" title="Desactivar ola verde">
                        ✕
                    </button>
                </div>
            </div>
            <div class="metrica-detalles" style="grid-template-columns: 1fr; gap: 0.4rem;">
                <div class="detalle-item">
                    <span class="detalle-label">📍 Destino</span>
                    <div class="detalle-valor" style="font-size: 0.7rem; font-weight: 600;">${destinoTexto}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.3rem;">
                    <div class="detalle-item">
                        <span class="detalle-label">📏 Distancia</span>
                        <div class="detalle-valor">${distanciaKm} km</div>
                    </div>
                    <div class="detalle-item">
                        <span class="detalle-label">⏱️ Tiempo</span>
                        <div class="detalle-valor">${tiempoMin} min</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.3rem;">
                    <div class="detalle-item">
                        <span class="detalle-label">🚗 Velocidad</span>
                        <div class="detalle-valor">${velocidadPromedio} km/h</div>
                    </div>
                    ${datosMapbox.weight ? `
                    <div class="detalle-item">
                        <span class="detalle-label">⚖️ Peso</span>
                        <div class="detalle-valor">${datosMapbox.weight.toFixed(1)}</div>
                    </div>` : '<div></div>'}
                </div>
            </div>

        </div>
    `;

    // Desactivar automáticamente después del tiempo estimado
    const tiempoDesactivacion = (datos.tiempo_estimado || 30) * 1000;
    console.log(`⏱️  Ola verde se desactivará automáticamente en ${tiempoDesactivacion/1000}s`);
    
    estado.timeoutOlaVerde = setTimeout(() => {
        console.log('⏱️  Tiempo cumplido, desactivando ola verde automáticamente');
        desactivarOlaVerde();
    }, tiempoDesactivacion);
}

// ==================== NUEVAS FUNCIONES DE VIDEO Y CÁMARA ====================

// Estado del panel de video
const estadoVideo = {
    activo: false,
    expandido: false,
    interseccionSeleccionada: null,
    vistaActual: 'mapa',  // 'mapa' o 'camara'
    ptz: {
        pan: 0,     // -180 a 180
        tilt: 0,    // -90 a 90
        zoom: 1.0   // 1.0 a 5.0
    },
    seguimientoAuto: false,
    vehiculoEmergenciaSeguido: null
};

// Helper: devuelve true si el modo actual corresponde al Procesador Video
function modoEsProcesadorVideo() {
    return ['video', 'procesador_video', 'procesador-video'].includes(estado.modoActual);
}

// Toggle activar/desactivar del Procesador Video
function toggleVideoYOLO() {
    const btn = document.getElementById('btn-toggle-video');
    if (!btn) {
        console.error('Botón btn-toggle-video no encontrado');
        return;
    }

    const indicator = document.querySelector('.camera-mode-indicator');
    const texto = document.getElementById('modo-camara-texto');

    if (!indicator || !texto) {
        console.error('Elementos de indicador no encontrados');
        return;
    }

    if (estadoVideo.activo) {
        estadoVideo.activo = false;
        // Actualizar ícono del botón (mantener el elemento <i> si existe para evitar quitar contenido)
        let iconElemOff = btn.querySelector('i');
        if (!iconElemOff) {
            iconElemOff = document.createElement('i');
            btn.appendChild(iconElemOff);
        }
        iconElemOff.className = 'fas fa-play';
        btn.title = 'Activar Cámara';
        indicator.classList.remove('active');
        texto.textContent = 'Desactivado';

        if (modoEsProcesadorVideo()) {
            detenerModoVideo();
            const selector = document.getElementById('selector-interseccion-cam');
            if (selector) selector.value = '';
        } else {
            detenerSimulacionVideoInterseccion();
        }

        console.log('✓ Video desactivado');
    } else {
        // Verificar que haya una intersección seleccionada antes de activar
        const selector = document.getElementById('selector-interseccion-cam');

        if (modoEsProcesadorVideo() && (!selector || !selector.value || selector.value === '')) {
            alert('Por favor selecciona una opcion MIR del selector');
            return;
        }

        if (estado.modoActual === 'simulador' && (!estadoVideo.interseccionSeleccionada)) {
            console.warn('[DEBUG] No hay intersección seleccionada en modo simulador');
            alert('Por favor selecciona una intersección del selector');
            return;
        }

        console.log('[DEBUG] Activando video...');
        console.log('[DEBUG] Modo actual:', estado.modoActual);
        console.log('[DEBUG] Intersección seleccionada:', estadoVideo.interseccionSeleccionada);

        estadoVideo.activo = true;
        // Actualizar ícono del botón (mantener el elemento <i> si existe para evitar quitar contenido)
        let iconElem = btn.querySelector('i');
        if (!iconElem) {
            iconElem = document.createElement('i');
            btn.appendChild(iconElem);
        }
        // Usar icono 'pause' para indicar que se puede pausar/stop
        iconElem.className = 'fas fa-pause';
        btn.title = 'Desactivar Cámara';
        indicator.classList.add('active');
        texto.textContent = 'Activo';

        if (modoEsProcesadorVideo()) {
            // En modo Procesador Video, activar según la selección (automáticamente se activa con el onChange del selector)
            console.log('[DEBUG] Modo Procesador Video - activando video procesado');
            const selectedValue = selector.value;
            const videoIndex = parseInt(selectedValue);
            activarModoVideo(videoIndex);
        } else {
            // En modo simulador
            console.log('[DEBUG] Modo simulador - iniciando simulación de video');
            window.motorGiratorioAnimacion.anguloObjetivo = estadoVideo.ptz.pan;
            iniciarSimulacionVideoInterseccion();
        }

        console.log('✓ Video activado correctamente');
    }
}

// Toggle expandir/contraer panel de video
function toggleExpandVideo() {
    // Null checks para prevenir errores
    const panel = document.getElementById('panel-video');
    const btn = document.getElementById('btn-expand-video');

    if (!panel || !btn) {
        console.error('Elementos del panel de video no encontrados');
        return;
    }

    // Toggle estado
    estadoVideo.expandido = !estadoVideo.expandido;

        if (estadoVideo.expandido) {
        // Expandir panel
        panel.classList.add('expanded');
        // Actualizar ícono del botón expandir/contraer sin reemplazar innerHTML
        let expandIcon = btn.querySelector('i');
        if (!expandIcon) {
            expandIcon = document.createElement('i');
            btn.appendChild(expandIcon);
        }
        expandIcon.className = 'fas fa-compress';
        btn.title = 'Contraer (ESC)';
        document.body.style.overflow = 'hidden';
        // Forzar visibilidad de los botones de cabecera cuando el panel está expandido
        const btnToggle = document.getElementById('btn-toggle-video');
        const headerActions = panel.querySelector('.header-actions');

        if (headerActions) {
            headerActions.style.position = 'absolute';
            headerActions.style.right = '16px';
            headerActions.style.top = '12px';
            headerActions.style.zIndex = '10002';
            headerActions.style.pointerEvents = 'auto';
        }

        if (btnToggle) {
            btnToggle.style.display = 'flex';
            btnToggle.style.visibility = 'visible';
            btnToggle.style.zIndex = '10003';
        }

        if (btn) {
            btn.style.display = 'flex';
            btn.style.visibility = 'visible';
            btn.style.zIndex = '10003';
        }
        console.log('✓ Panel de video expandido');
        } else {
        // Contraer panel
        panel.classList.remove('expanded');
        // Actualizar ícono del botón expandir/contraer sin reemplazar innerHTML
        let expandIconCollapse = btn.querySelector('i');
        if (!expandIconCollapse) {
            expandIconCollapse = document.createElement('i');
            btn.appendChild(expandIconCollapse);
        }
        expandIconCollapse.className = 'fas fa-expand';
        btn.title = 'Expandir';
        document.body.style.overflow = '';
        // Restaurar estilos inline que pudieran haberse aplicado al expandir
        const btnToggleRestore = document.getElementById('btn-toggle-video');
        const headerActionsRestore = panel.querySelector('.header-actions');

        if (headerActionsRestore) {
            headerActionsRestore.style.position = '';
            headerActionsRestore.style.right = '';
            headerActionsRestore.style.top = '';
            headerActionsRestore.style.zIndex = '';
            headerActionsRestore.style.pointerEvents = '';
        }

        if (btnToggleRestore) {
            btnToggleRestore.style.display = '';
            btnToggleRestore.style.visibility = '';
            btnToggleRestore.style.zIndex = '';
        }

        if (btn) {
            btn.style.display = '';
            btn.style.visibility = '';
            btn.style.zIndex = '';
        }
        console.log('✓ Panel de video contraído');
    }
}

// Cambiar entre vista mapa y vista cámara
function cambiarVistaMapaCamara() {
    const mainContent = document.querySelector('.main-content');
    const panelVideo = document.getElementById('panel-video');

    if (estadoVideo.vistaActual === 'mapa') {
        // Cambiar a vista cámara
        estadoVideo.vistaActual = 'camara';
        mainContent.style.display = 'none';

        // Mover panel de video al centro
        panelVideo.style.position = 'fixed';
        panelVideo.style.top = '100px';
        panelVideo.style.left = '50%';
        panelVideo.style.transform = 'translateX(-50%)';
        panelVideo.style.width = '80%';
        panelVideo.style.maxWidth = '1200px';
        panelVideo.style.zIndex = '100';

        console.log('Cambiado a vista cámara');
    } else {
        // Cambiar a vista mapa
        estadoVideo.vistaActual = 'mapa';
        mainContent.style.display = 'block';

        // Restaurar posición del panel de video
        panelVideo.style.position = 'static';
        panelVideo.style.transform = 'none';
        panelVideo.style.width = 'auto';
        panelVideo.style.zIndex = 'auto';

        console.log('Cambiado a vista mapa');
    }
}

// Seleccionar intersección para ver su cámara
function seleccionarInterseccionCamara(event) {
    const interseccionId = event.target.value;
    console.log('[DEBUG] seleccionarInterseccionCamara llamada con:', interseccionId);

    if (!interseccionId) {
        estadoVideo.interseccionSeleccionada = null;
        console.log('[DEBUG] Intersección deseleccionada');
        return;
    }

    estadoVideo.interseccionSeleccionada = interseccionId;
    const interseccion = INTERSECCIONES_LIMA.find(i => i.id === interseccionId);

    if (interseccion) {
        console.log(`✓ Intersección seleccionada: ${interseccion.nombre} (${interseccionId})`);

        // Los controles PTZ se mostrarán automáticamente via CSS
        // solo cuando el panel esté expandido (#panel-video.expanded .ptz-controls)

        // Centrar mapa en la intersección
        if (estado.mapa) {
            estado.mapa.setView([interseccion.latitud, interseccion.longitud], 16);
        }

        // Resetear posición PTZ
        estadoVideo.ptz = { pan: 0, tilt: 0, zoom: 1.0 };
        actualizarDisplayPTZ();
    }
}

// Variables para animación suave del motor giratorio
if (!window.motorGiratorioAnimacion) {
    window.motorGiratorioAnimacion = {
        anguloObjetivo: 0,
        animando: false,
        intervaloRotacion: null,
        direccionActual: null
    };
}

// Iniciar rotación continua mientras se mantiene presionado
function iniciarRotacionContinua(direccion) {
    // Si ya hay una rotación en curso, detenerla primero
    if (window.motorGiratorioAnimacion.intervaloRotacion) {
        clearInterval(window.motorGiratorioAnimacion.intervaloRotacion);
    }

    window.motorGiratorioAnimacion.direccionActual = direccion;

    // Ejecutar inmediatamente el primer movimiento
    moverCamara(direccion);

    // Continuar moviendo cada 50ms mientras esté presionado
    window.motorGiratorioAnimacion.intervaloRotacion = setInterval(() => {
        moverCamara(direccion);
    }, 50); // 20 veces por segundo = rotación suave
}

// Detener rotación continua al soltar el botón
function detenerRotacionContinua() {
    if (window.motorGiratorioAnimacion.intervaloRotacion) {
        clearInterval(window.motorGiratorioAnimacion.intervaloRotacion);
        window.motorGiratorioAnimacion.intervaloRotacion = null;
        window.motorGiratorioAnimacion.direccionActual = null;
    }
}

// Mover motor giratorio horizontal (solo izquierda/derecha) con animación suave
function moverCamara(direccion) {
    const incremento = 1; // 1 grado por click (movimiento fino y gradual)

    // Calcular nuevo ángulo objetivo
    let nuevoObjetivo = window.motorGiratorioAnimacion.anguloObjetivo;

    switch (direccion) {
        case 'left':
            nuevoObjetivo = Math.max(-180, window.motorGiratorioAnimacion.anguloObjetivo - incremento);
            break;
        case 'right':
            nuevoObjetivo = Math.min(180, window.motorGiratorioAnimacion.anguloObjetivo + incremento);
            break;
    }

    window.motorGiratorioAnimacion.anguloObjetivo = nuevoObjetivo;

    // Iniciar animación si no está ya animando
    if (!window.motorGiratorioAnimacion.animando) {
        animarRotacionMotor();
    }

    console.log(`Motor giratorio: ${direccion} - Objetivo: ${nuevoObjetivo}°`);
}

// Animar rotación del motor gradualmente
function animarRotacionMotor() {
    window.motorGiratorioAnimacion.animando = true;

    const animar = () => {
        const anguloActual = estadoVideo.ptz.pan;
        const anguloObjetivo = window.motorGiratorioAnimacion.anguloObjetivo;
        const diferencia = anguloObjetivo - anguloActual;

        // Si estamos muy cerca del objetivo, establecer el valor final
        if (Math.abs(diferencia) < 0.5) {
            estadoVideo.ptz.pan = anguloObjetivo;
            actualizarDisplayPTZ();
            window.motorGiratorioAnimacion.animando = false;
            return; // Terminar animación
        }

        // Interpolar suavemente (velocidad proporcional a la distancia)
        const velocidad = 0.25; // Velocidad más rápida para movimientos de 1 grado
        estadoVideo.ptz.pan += diferencia * velocidad;

        actualizarDisplayPTZ();

        // Continuar animación
        requestAnimationFrame(animar);
    };

    animar();
}

// Actualizar display de ángulo de rotación
function actualizarDisplayPTZ() {
    document.getElementById('ptz-pan-value').textContent = estadoVideo.ptz.pan.toFixed(0);
}

// Nota: El motor giratorio controla el ángulo de la cámara física,
// pero la simulación visual no necesita transformaciones PTZ.

// Toggle modo automático/manual del motor giratorio
function toggleSeguimientoAuto(event) {
    estadoVideo.seguimientoAuto = event.target.checked;
    const modeText = document.getElementById('mode-text');

    if (estadoVideo.seguimientoAuto) {
        modeText.textContent = 'Automático';
        console.log('Modo automático activado - Motor sigue vehículos de emergencia');
        // Si hay un vehículo de emergencia activo, empezar a seguirlo
        if (estado.olaVerdeActiva) {
            iniciarSeguimientoVehiculoEmergencia();
        }
    } else {
        modeText.textContent = 'Manual';
        console.log('Modo manual activado - Control directo del motor');
        detenerSeguimientoVehiculoEmergencia();
    }
}

// Iniciar seguimiento de vehículo de emergencia
function iniciarSeguimientoVehiculoEmergencia() {
    if (!estadoVideo.seguimientoAuto) return;

    // Simular seguimiento del vehículo de emergencia
    const seguimientoInterval = setInterval(() => {
        if (!estadoVideo.seguimientoAuto || !estado.olaVerdeActiva) {
            clearInterval(seguimientoInterval);
            return;
        }

        // Simular movimiento de motor giratorio siguiendo al vehículo
        // En implementación real, esto consultaría la posición del vehículo y ajustaría el motor

        // Por ahora, simulamos un paneo suave
        estadoVideo.ptz.pan += Math.sin(Date.now() / 1000) * 2;
        estadoVideo.ptz.pan = Math.max(-180, Math.min(180, estadoVideo.ptz.pan));

        actualizarDisplayPTZ();

    }, 100); // Actualizar cada 100ms

    console.log('Seguimiento de vehículo de emergencia iniciado');
}

// Detener seguimiento de vehículo de emergencia
function detenerSeguimientoVehiculoEmergencia() {
    estadoVideo.vehiculoEmergenciaSeguido = null;
    console.log('Seguimiento de vehículo de emergencia detenido');
}

// Iniciar simulación de video de intersección
function iniciarSimulacionVideoInterseccion() {
    console.log('[DEBUG] iniciarSimulacionVideoInterseccion llamada');
    console.log('[DEBUG] estadoVideo.interseccionSeleccionada:', estadoVideo.interseccionSeleccionada);

    if (!estadoVideo.interseccionSeleccionada) {
        console.warn('No hay intersección seleccionada para simular video');
        return;
    }

    const canvas = document.getElementById('video-canvas');
    if (!canvas) {
        console.error('Canvas video-canvas no encontrado');
        return;
    }

    const ctx = canvas.getContext('2d');
    console.log('[DEBUG] Canvas y contexto obtenidos correctamente');

    // Detener intervalo anterior si existe
    if (estado.simulacionVideoInterval) {
        clearInterval(estado.simulacionVideoInterval);
        console.log('[DEBUG] Intervalo anterior detenido');
    }

    // Simular video con datos de la intersección
    let frameCount = 0;
    estado.simulacionVideoInterval = setInterval(() => {
        if (!estadoVideo.activo) {
            clearInterval(estado.simulacionVideoInterval);
            console.log('[DEBUG] Simulación detenida (video desactivado)');
            return;
        }

        frameCount++;
        if (frameCount % 25 === 0) {  // Log cada 5 segundos (25 frames a 5 FPS)
            console.log(`[DEBUG] Renderizando frame ${frameCount}`);
        }

        // Dibujar fondo oscuro
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Simular vista de calle con vehículos
        dibujarSimulacionCalle(ctx, canvas);

        // Actualizar métricas de video
        const metricasSimuladas = obtenerMetricasInterseccionParaVideo(estadoVideo.interseccionSeleccionada);
        actualizarMetricasVideo(metricasSimuladas);

    }, 200); // 5 FPS

    console.log('✓ Simulación de video de intersección iniciada correctamente');
}

// Detener simulación de video
function detenerSimulacionVideoInterseccion() {
    if (estado.simulacionVideoInterval) {
        clearInterval(estado.simulacionVideoInterval);
        estado.simulacionVideoInterval = null;
    }

    // Limpiar canvas
    const canvas = document.getElementById('video-canvas');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Resetear métricas
    document.getElementById('video-vehiculos').textContent = '0';
    document.getElementById('video-fps').textContent = '0';
    document.getElementById('video-icv').textContent = '0.00';

    console.log('Simulación de video detenida');
}

// Variables para animación de vehículos y semáforos
if (!window.vehiculosAnimados) {
    window.vehiculosAnimados = [];
    window.ultimoFrameVehiculos = Date.now();
}

// Sistema de control de semáforos
if (!window.semaforosInterseccion) {
    window.semaforosInterseccion = {
        // Estados: 'verde', 'amarillo', 'rojo'
        norte: { estado: 'verde', tiempo: 0 },
        sur: { estado: 'verde', tiempo: 0 },
        este: { estado: 'rojo', tiempo: 0 },
        oeste: { estado: 'rojo', tiempo: 0 },
        ultimaActualizacion: Date.now()
    };
}

// Actualizar ciclo de semáforos
function actualizarSemaforos() {
    const ahora = Date.now();
    const deltaTime = (ahora - window.semaforosInterseccion.ultimaActualizacion) / 1000;
    window.semaforosInterseccion.ultimaActualizacion = ahora;

    // Actualizar tiempo de cada semáforo
    ['norte', 'sur', 'este', 'oeste'].forEach(direccion => {
        const sem = window.semaforosInterseccion[direccion];
        sem.tiempo += deltaTime;

        // Ciclo: Verde (25s) → Amarillo (3s) → Rojo (25s)
        if (sem.estado === 'verde' && sem.tiempo >= 25) {
            sem.estado = 'amarillo';
            sem.tiempo = 0;
        } else if (sem.estado === 'amarillo' && sem.tiempo >= 3) {
            sem.estado = 'rojo';
            sem.tiempo = 0;
        } else if (sem.estado === 'rojo' && sem.tiempo >= 25) {
            sem.estado = 'verde';
            sem.tiempo = 0;
        }
    });

    // Sincronizar Norte-Sur y Este-Oeste (semáforos opuestos siempre iguales)
    window.semaforosInterseccion.sur.estado = window.semaforosInterseccion.norte.estado;
    window.semaforosInterseccion.sur.tiempo = window.semaforosInterseccion.norte.tiempo;

    window.semaforosInterseccion.oeste.estado = window.semaforosInterseccion.este.estado;
    window.semaforosInterseccion.oeste.tiempo = window.semaforosInterseccion.este.tiempo;
}

// Dibujar los 4 semáforos de la intersección
function dibujarSemaforos(ctx, centroX, centroY, anchoPista) {
    const radioLuz = 5;
    const espacioLuces = 14;

    // Función auxiliar para dibujar un semáforo completo
    function dibujarSemaforo(x, y, estado) {
        // Poste del semáforo
        ctx.fillStyle = '#2c2c2c';
        ctx.fillRect(x - 6, y - 24, 12, 48);

        // Luz Roja (arriba)
        ctx.fillStyle = estado === 'rojo' ? '#ef4444' : '#4a1e1e';
        ctx.beginPath();
        ctx.arc(x, y - espacioLuces, radioLuz, 0, Math.PI * 2);
        ctx.fill();

        // Luz Amarilla (centro)
        ctx.fillStyle = estado === 'amarillo' ? '#fbbf24' : '#4a4021';
        ctx.beginPath();
        ctx.arc(x, y, radioLuz, 0, Math.PI * 2);
        ctx.fill();

        // Luz Verde (abajo)
        ctx.fillStyle = estado === 'verde' ? '#10b981' : '#1e3a2e';
        ctx.beginPath();
        ctx.arc(x, y + espacioLuces, radioLuz, 0, Math.PI * 2);
        ctx.fill();

        // Brillo adicional para luz activa
        if (estado === 'verde' || estado === 'amarillo' || estado === 'rojo') {
            ctx.shadowBlur = 15;
            ctx.shadowColor = estado === 'verde' ? '#10b981' : (estado === 'amarillo' ? '#fbbf24' : '#ef4444');
            ctx.fillStyle = estado === 'verde' ? '#10b981' : (estado === 'amarillo' ? '#fbbf24' : '#ef4444');
            ctx.beginPath();
            const yLuz = estado === 'verde' ? y + espacioLuces : (estado === 'amarillo' ? y : y - espacioLuces);
            ctx.arc(x, yLuz, radioLuz, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    // Semáforo NORTE (controla vehículos que van hacia el norte)
    // Ubicado antes de la intersección para vehículos que suben
    dibujarSemaforo(centroX + anchoPista * 1.5, centroY - anchoPista * 2 - 35, window.semaforosInterseccion.norte.estado);

    // Semáforo SUR (controla vehículos que van hacia el sur)
    // Ubicado antes de la intersección para vehículos que bajan
    dibujarSemaforo(centroX - anchoPista * 1.5, centroY + anchoPista * 2 + 35, window.semaforosInterseccion.sur.estado);

    // Semáforo ESTE (controla vehículos que van hacia el este)
    // Ubicado antes de la intersección para vehículos que van a la derecha
    dibujarSemaforo(centroX + anchoPista * 2 + 35, centroY + anchoPista * 1.5, window.semaforosInterseccion.este.estado);

    // Semáforo OESTE (controla vehículos que van hacia el oeste)
    // Ubicado antes de la intersección para vehículos que van a la izquierda
    dibujarSemaforo(centroX - anchoPista * 2 - 35, centroY - anchoPista * 1.5, window.semaforosInterseccion.oeste.estado);
}

// Dibujar simulación de intersección con 4 vías
function dibujarSimulacionCalle(ctx, canvas) {
    const w = canvas.width;
    const h = canvas.height;
    const centroX = w / 2;
    const centroY = h / 2;
    const anchoPista = 35;

    // Fondo (cielo/ciudad)
    ctx.fillStyle = '#1a2332';
    ctx.fillRect(0, 0, w, h);

    // ========== CALLES ==========
    // Calle VERTICAL (Norte-Sur)
    ctx.fillStyle = '#3a3a3a';
    ctx.fillRect(centroX - anchoPista * 2, 0, anchoPista * 4, h);

    // Calle HORIZONTAL (Este-Oeste)
    ctx.fillStyle = '#3a3a3a';
    ctx.fillRect(0, centroY - anchoPista * 2, w, anchoPista * 4);

    // ========== LÍNEAS DE PISTAS ==========
    ctx.strokeStyle = '#ffeb3b';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 10]);

    // Línea central vertical (separa Norte-Sur)
    ctx.beginPath();
    ctx.moveTo(centroX, 0);
    ctx.lineTo(centroX, centroY - anchoPista * 2);
    ctx.moveTo(centroX, centroY + anchoPista * 2);
    ctx.lineTo(centroX, h);
    ctx.stroke();

    // Línea central horizontal (separa Este-Oeste)
    ctx.beginPath();
    ctx.moveTo(0, centroY);
    ctx.lineTo(centroX - anchoPista * 2, centroY);
    ctx.moveTo(centroX + anchoPista * 2, centroY);
    ctx.lineTo(w, centroY);
    ctx.stroke();

    // Líneas divisoras pistas verticales
    ctx.beginPath();
    ctx.moveTo(centroX - anchoPista, 0);
    ctx.lineTo(centroX - anchoPista, centroY - anchoPista * 2);
    ctx.moveTo(centroX - anchoPista, centroY + anchoPista * 2);
    ctx.lineTo(centroX - anchoPista, h);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(centroX + anchoPista, 0);
    ctx.lineTo(centroX + anchoPista, centroY - anchoPista * 2);
    ctx.moveTo(centroX + anchoPista, centroY + anchoPista * 2);
    ctx.lineTo(centroX + anchoPista, h);
    ctx.stroke();

    // Líneas divisoras pistas horizontales
    ctx.beginPath();
    ctx.moveTo(0, centroY - anchoPista);
    ctx.lineTo(centroX - anchoPista * 2, centroY - anchoPista);
    ctx.moveTo(centroX + anchoPista * 2, centroY - anchoPista);
    ctx.lineTo(w, centroY - anchoPista);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, centroY + anchoPista);
    ctx.lineTo(centroX - anchoPista * 2, centroY + anchoPista);
    ctx.moveTo(centroX + anchoPista * 2, centroY + anchoPista);
    ctx.lineTo(w, centroY + anchoPista);
    ctx.stroke();

    ctx.setLineDash([]);

    // ========== ZONA DE INTERSECCIÓN ==========
    ctx.fillStyle = '#2a2a2a';
    ctx.fillRect(centroX - anchoPista * 2, centroY - anchoPista * 2, anchoPista * 4, anchoPista * 4);

    // Líneas de paso peatonal (cebra)
    ctx.fillStyle = '#ffffff';
    const anchoLinea = 8;
    const espacioLinea = 10;
    // Paso norte
    for (let i = 0; i < 4; i++) {
        ctx.fillRect(centroX - anchoPista * 2 + i * (anchoLinea + espacioLinea), centroY - anchoPista * 2 - 15, anchoLinea, 15);
    }
    // Paso sur
    for (let i = 0; i < 4; i++) {
        ctx.fillRect(centroX - anchoPista * 2 + i * (anchoLinea + espacioLinea), centroY + anchoPista * 2, anchoLinea, 15);
    }
    // Paso este
    for (let i = 0; i < 4; i++) {
        ctx.fillRect(centroX + anchoPista * 2, centroY - anchoPista * 2 + i * (anchoLinea + espacioLinea), 15, anchoLinea);
    }
    // Paso oeste
    for (let i = 0; i < 4; i++) {
        ctx.fillRect(centroX - anchoPista * 2 - 15, centroY - anchoPista * 2 + i * (anchoLinea + espacioLinea), 15, anchoLinea);
    }

    // ========== ACTUALIZAR Y DIBUJAR SEMÁFOROS ==========
    actualizarSemaforos();
    dibujarSemaforos(ctx, centroX, centroY, anchoPista);

    // ========== VEHÍCULOS ANIMADOS ==========
    actualizarYDibujarVehiculos(ctx, canvas, centroX, centroY, anchoPista);

    // ========== INFORMACIÓN SUPERPUESTA ==========
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(5, 5, 200, 45);
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 13px Arial';
    ctx.fillText(`📍 ${estadoVideo.interseccionSeleccionada}`, 12, 22);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px Arial';
    ctx.fillText(`Vehículos detectados: ${window.vehiculosAnimados.length}`, 12, 38);
}

// Actualizar y dibujar vehículos en movimiento
function actualizarYDibujarVehiculos(ctx, canvas, centroX, centroY, anchoPista) {
    const ahora = Date.now();
    const deltaTime = (ahora - window.ultimoFrameVehiculos) / 1000; // segundos
    window.ultimoFrameVehiculos = ahora;

    // Obtener métricas reales de la intersección seleccionada
    const metricas = estado.ultimasMetricas && estadoVideo.interseccionSeleccionada
        ? estado.ultimasMetricas[estadoVideo.interseccionSeleccionada]
        : null;

    // Determinar número objetivo de vehículos basado en métricas reales
    let numObjetivoVehiculos = 3; // Default bajo si no hay métricas
    let probabilidadAparicion = 0.05; // Probabilidad baja por defecto

    if (metricas) {
        // Calcular número objetivo basado en num_vehiculos y ICV
        const numVehiculosReal = metricas.num_vehiculos || 0;
        const icvReal = metricas.icv || 0;

        // Escalar el número de vehículos a un rango visible (3-15 vehículos en pantalla)
        numObjetivoVehiculos = Math.min(15, Math.max(3, Math.floor(numVehiculosReal / 2)));

        // Ajustar probabilidad de aparición según el flujo y ICV
        // Mayor ICV = más tráfico = mayor probabilidad
        probabilidadAparicion = 0.05 + (icvReal * 0.25); // 0.05 a 0.30
    }

    // Añadir nuevos vehículos basado en métricas reales
    if (Math.random() < probabilidadAparicion && window.vehiculosAnimados.length < numObjetivoVehiculos) {
        const direccion = ['norte', 'sur', 'este', 'oeste'][Math.floor(Math.random() * 4)];
        const pista = Math.random() > 0.5 ? 0 : 1; // 0 = pista izquierda/superior, 1 = pista derecha/inferior

        // Velocidad basada en las métricas reales
        let velocidadPixeles = 80; // Default
        if (metricas && metricas.velocidad) {
            // Convertir velocidad real (km/h) a píxeles por segundo (escala visual)
            // Velocidad real típica: 5-60 km/h -> Velocidad visual: 30-120 píx/s
            velocidadPixeles = 30 + (metricas.velocidad * 1.5);
        }

        const vehiculo = {
            direccion: direccion,
            pista: pista,
            color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][Math.floor(Math.random() * 5)],
            velocidad: velocidadPixeles,
            progreso: 0,
            detenido: false
        };

        window.vehiculosAnimados.push(vehiculo);
    }

    // Actualizar y dibujar cada vehículo
    for (let i = window.vehiculosAnimados.length - 1; i >= 0; i--) {
        const v = window.vehiculosAnimados[i];

        // Verificar si debe detenerse por el semáforo
        const estadoSemaforo = window.semaforosInterseccion[v.direccion].estado;
        const distanciaDetencion = 80; // Distancia en píxeles antes de la intersección para detenerse

        // Calcular si está cerca de la intersección
        let debeDetenerse = false;
        if (v.direccion === 'norte' && v.progreso > (canvas.height - centroY - anchoPista * 2 - distanciaDetencion) && v.progreso < (canvas.height - centroY + anchoPista * 2)) {
            debeDetenerse = (estadoSemaforo === 'rojo' || estadoSemaforo === 'amarillo');
        } else if (v.direccion === 'sur' && v.progreso > (centroY - anchoPista * 2 - distanciaDetencion) && v.progreso < (centroY + anchoPista * 2)) {
            debeDetenerse = (estadoSemaforo === 'rojo' || estadoSemaforo === 'amarillo');
        } else if (v.direccion === 'este' && v.progreso > (centroX - anchoPista * 2 - distanciaDetencion) && v.progreso < (centroX + anchoPista * 2)) {
            debeDetenerse = (estadoSemaforo === 'rojo' || estadoSemaforo === 'amarillo');
        } else if (v.direccion === 'oeste' && v.progreso > (canvas.width - centroX - anchoPista * 2 - distanciaDetencion) && v.progreso < (canvas.width - centroX + anchoPista * 2)) {
            debeDetenerse = (estadoSemaforo === 'rojo' || estadoSemaforo === 'amarillo');
        }

        // Solo avanzar si no debe detenerse
        if (!debeDetenerse) {
            v.progreso += v.velocidad * deltaTime;
            v.detenido = false;
        } else {
            v.detenido = true;
        }

        let x, y, ancho, alto;
        const tamañoVehiculo = 25;

        // Calcular posición según dirección
        if (v.direccion === 'norte') {
            // Subiendo (de abajo hacia arriba)
            x = centroX + (v.pista === 0 ? anchoPista * 0.5 : anchoPista * 1.5);
            y = canvas.height - v.progreso;
            ancho = 18;
            alto = tamañoVehiculo;

            if (y < -30) {
                window.vehiculosAnimados.splice(i, 1);
                continue;
            }
        } else if (v.direccion === 'sur') {
            // Bajando (de arriba hacia abajo)
            x = centroX - (v.pista === 0 ? anchoPista * 1.5 : anchoPista * 0.5);
            y = v.progreso;
            ancho = 18;
            alto = tamañoVehiculo;

            if (y > canvas.height + 30) {
                window.vehiculosAnimados.splice(i, 1);
                continue;
            }
        } else if (v.direccion === 'este') {
            // Hacia la derecha
            x = v.progreso;
            y = centroY + (v.pista === 0 ? anchoPista * 0.5 : anchoPista * 1.5);
            ancho = tamañoVehiculo;
            alto = 18;

            if (x > canvas.width + 30) {
                window.vehiculosAnimados.splice(i, 1);
                continue;
            }
        } else { // oeste
            // Hacia la izquierda
            x = canvas.width - v.progreso;
            y = centroY - (v.pista === 0 ? anchoPista * 1.5 : anchoPista * 0.5);
            ancho = tamañoVehiculo;
            alto = 18;

            if (x < -30) {
                window.vehiculosAnimados.splice(i, 1);
                continue;
            }
        }

        // Dibujar vehículo
        ctx.fillStyle = v.color;
        ctx.fillRect(x - ancho/2, y - alto/2, ancho, alto);

        // Ventanas (más oscuras)
        ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
        if (v.direccion === 'norte' || v.direccion === 'sur') {
            ctx.fillRect(x - ancho/2 + 2, y - alto/2 + 3, ancho - 4, alto * 0.35);
        } else {
            ctx.fillRect(x - ancho/2 + 3, y - alto/2 + 2, ancho * 0.35, alto - 4);
        }

        // Luces delanteras (pequeños detalles)
        ctx.fillStyle = '#ffeb3b';
        if (v.direccion === 'norte') {
            ctx.fillRect(x - ancho/2 + 3, y - alto/2, 4, 2);
            ctx.fillRect(x + ancho/2 - 7, y - alto/2, 4, 2);
        } else if (v.direccion === 'sur') {
            ctx.fillRect(x - ancho/2 + 3, y + alto/2 - 2, 4, 2);
            ctx.fillRect(x + ancho/2 - 7, y + alto/2 - 2, 4, 2);
        } else if (v.direccion === 'este') {
            ctx.fillRect(x + ancho/2 - 2, y - alto/2 + 3, 2, 4);
            ctx.fillRect(x + ancho/2 - 2, y + alto/2 - 7, 2, 4);
        } else {
            ctx.fillRect(x - ancho/2, y - alto/2 + 3, 2, 4);
            ctx.fillRect(x - ancho/2, y + alto/2 - 7, 2, 4);
        }
    }
}

// Obtener métricas de intersección para mostrar en video
function obtenerMetricasInterseccionParaVideo(interseccionId) {
    // Buscar las métricas reales de la intersección desde el estado global
    const interseccion = INTERSECCIONES_LIMA.find(i => i.id === interseccionId);

    if (!interseccion) {
        console.warn(`Intersección ${interseccionId} no encontrada`);
        return {
            vehiculos: 0,
            fps: 5,
            icv: '0.00',
            flujo: 0,
            velocidad: 0,
            cola: 0
        };
    }

    // Buscar métricas actuales desde el último broadcast
    // Las métricas se almacenan cuando llegan por WebSocket o simulación local
    const metricasActuales = estado.ultimasMetricas || {};
    const metricaInterseccion = metricasActuales[interseccionId];

    if (metricaInterseccion) {
        // Tenemos métricas reales, usarlas
        return {
            vehiculos: metricaInterseccion.num_vehiculos || 0,
            fps: 5,
            icv: (metricaInterseccion.icv || 0).toFixed(2),
            flujo: metricaInterseccion.flujo || 0,
            velocidad: metricaInterseccion.velocidad || 0,
            cola: metricaInterseccion.cola || 0
        };
    }

    // Si no hay métricas, retornar valores en cero (no hay tráfico)
    return {
        vehiculos: 0,
        fps: 5,
        icv: '0.00',
        flujo: 0,
        velocidad: 0,
        cola: 0
    };
}

// Actualizar métricas de video en la UI
function actualizarMetricasVideo(metricas) {
    document.getElementById('video-vehiculos').textContent = metricas.vehiculos;
    document.getElementById('video-fps').textContent = metricas.fps;
    document.getElementById('video-icv').textContent = metricas.icv;
}

// Poblar selector de intersecciones para cámara
function poblarSelectorIntersecciones() {
    const selector = document.getElementById('selector-interseccion-cam');

    if (!selector || !INTERSECCIONES_LIMA) return;

    // Limpiar opciones existentes (excepto la primera)
    selector.innerHTML = '<option value="">Selecciona intersección...</option>';

    // Agregar todas las intersecciones
    INTERSECCIONES_LIMA.forEach(inter => {
        const option = document.createElement('option');
        option.value = inter.id;
        option.textContent = `${inter.id} - ${inter.nombre}`;
        selector.appendChild(option);
    });

    console.log(`Selector de intersecciones poblado con ${INTERSECCIONES_LIMA.length} opciones`);
}

// Llamar al poblar selector cuando se carguen las intersecciones
const cargarInterseccionesRealesOriginal = cargarInterseccionesReales;
cargarInterseccionesReales = function() {
    cargarInterseccionesRealesOriginal();
    setTimeout(poblarSelectorIntersecciones, 500);
    // DESHABILITADO: Sistema de tráfico en calles (dibujaba líneas verdes en el mapa)
    // setTimeout(() => {
    //     inicializarCapaTrafico();
    //     iniciarActualizacionTrafico();
    // }, 1000);
};

// ==================== SISTEMA DE TRÁFICO EN CALLES (AJUSTADO A PISTAS REALES) ====================

/**
 * Inicializa la capa de tráfico en las calles (estilo Google Maps)
 */
function inicializarCapaTrafico() {
    if (!estado.mapa) return;

    // Crear layer group para las calles con tráfico
    estado.capaTrafico = L.layerGroup().addTo(estado.mapa);

    console.log('Capa de tráfico inicializada');
}

/**
 * Actualiza la visualización de tráfico en las calles
 * Dibuja polylines siguiendo las PISTAS REALES con waypoints
 */
function actualizarVisualizacionTrafico() {
    if (!estado.capaTrafico) return;

    // Limpiar capa anterior
    estado.capaTrafico.clearLayers();

    // Para cada conexión entre intersecciones, dibujar la calle siguiendo la ruta real
    CONEXIONES_PRINCIPALES.forEach(conexion => {
        const origen = INTERSECCIONES_LIMA.find(i => i.id === conexion.origen);
        const destino = INTERSECCIONES_LIMA.find(i => i.id === conexion.destino);

        if (!origen || !destino) return;

        // Obtener datos de tráfico para esta conexión
        const traficoData = estado.datosTrafico[`${conexion.origen}-${conexion.destino}`] || {
            congestion: Math.random() * 0.8,
            velocidad: 30 + Math.random() * 30,
            numVehiculos: Math.floor(Math.random() * 20) + 5
        };

        // Determinar color según nivel de congestión (estilo Google Maps)
        let color, weight, opacity;
        if (traficoData.congestion < 0.3) {
            color = '#10b981'; // Verde - fluido
            weight = 6;
            opacity = 0.8;
        } else if (traficoData.congestion < 0.6) {
            color = '#f59e0b'; // Amarillo/Naranja - moderado
            weight = 7;
            opacity = 0.85;
        } else {
            color = '#ef4444'; // Rojo - congestionado
            weight = 8;
            opacity = 0.9;
        }

        // Generar waypoints para seguir la ruta real de la calle
        const waypoints = generarWaypointsCalle(origen, destino, conexion.via);

        // Crear polyline gruesa siguiendo los waypoints - ESTABLE AL ZOOM
        const calle = L.polyline(waypoints, {
            color: color,
            weight: weight,
            opacity: opacity,
            lineCap: 'round',
            lineJoin: 'round',
            smoothFactor: 0.5,  // Reducir suavizado para estabilidad
            noClip: false,
            className: 'calle-trafico',
            // Propiedades adicionales para estabilidad
            interactive: true,
            bubblingMouseEvents: false
        });

        // Tooltip con información de tráfico
        calle.bindTooltip(`
            <div style="font-family: Arial; font-size: 11px;">
                <strong>${conexion.via}</strong><br/>
                Velocidad: ${traficoData.velocidad.toFixed(0)} km/h<br/>
                Vehículos: ${traficoData.numVehiculos}<br/>
                Estado: ${traficoData.congestion < 0.3 ? 'Fluido' : traficoData.congestion < 0.6 ? 'Moderado' : 'Congestionado'}
            </div>
        `, {
            permanent: false,
            direction: 'center',
            className: 'tooltip-trafico'
        });

        calle.addTo(estado.capaTrafico);
    });

    // Actualizar mini stats splits
    actualizarMiniStatsSplits();

    console.log(`Tráfico actualizado en ${CONEXIONES_PRINCIPALES.length} calles`);
}

/**
 * Actualiza las mini estadísticas laterales (splits)
 */
function actualizarMiniStatsSplits() {
    let callesFluidas = 0;
    let callesModeradas = 0;
    let callesCongestionadas = 0;
    let velocidadTotal = 0;
    let count = 0;

    // Contar calles por estado
    for (const clave in estado.datosTrafico) {
        const datos = estado.datosTrafico[clave];
        count++;
        velocidadTotal += datos.velocidad;

        if (datos.congestion < 0.3) {
            callesFluidas++;
        } else if (datos.congestion < 0.6) {
            callesModeradas++;
        } else {
            callesCongestionadas++;
        }
    }

    const velocidadPromedio = count > 0 ? velocidadTotal / count : 0;

    // Actualizar UI
    document.getElementById('calles-fluidas').textContent = callesFluidas;
    document.getElementById('calles-moderadas').textContent = callesModeradas;
    document.getElementById('calles-congestionadas').textContent = callesCongestionadas;
    document.getElementById('velocidad-promedio').textContent = velocidadPromedio.toFixed(0);
}

/**
 * Genera waypoints para que la línea siga la ruta real de la calle
 * En lugar de línea recta, crea puntos intermedios siguiendo la curvatura de la vía
 */
function generarWaypointsCalle(origen, destino, nombreVia) {
    const waypoints = [[origen.latitud, origen.longitud]];

    // Calcular dirección general
    const deltaLat = destino.latitud - origen.latitud;
    const deltaLon = destino.longitud - origen.longitud;
    const distancia = Math.sqrt(deltaLat * deltaLat + deltaLon * deltaLon);

    // Número de puntos intermedios basado en la distancia - REDUCIDO para estabilidad
    const numPuntos = Math.max(2, Math.floor(distancia * 80)); // Menos puntos = más estable al zoom

    // Determinar si la calle es recta o tiene curvas basado en su nombre
    const esRecta = nombreVia.includes('Av. Arequipa') || nombreVia.includes('Av. Javier Prado');

    if (esRecta) {
        // Para avenidas rectas, usar interpolación lineal SIMPLE (sin variaciones aleatorias)
        for (let i = 1; i < numPuntos; i++) {
            const t = i / numPuntos;
            const lat = origen.latitud + deltaLat * t;
            const lon = origen.longitud + deltaLon * t;
            waypoints.push([lat, lon]);
        }
    } else {
        // Para calles con curvas, usar interpolación bezier
        const midLat = (origen.latitud + destino.latitud) / 2;
        const midLon = (origen.longitud + destino.longitud) / 2;

        // Punto de control para la curva (perpendicular al centro)
        const perpLat = -deltaLon * 0.3;
        const perpLon = deltaLat * 0.3;
        const controlLat = midLat + perpLat;
        const controlLon = midLon + perpLon;

        // Generar puntos siguiendo curva cuadrática
        for (let i = 1; i < numPuntos; i++) {
            const t = i / numPuntos;
            const t2 = t * t;
            const mt = 1 - t;
            const mt2 = mt * mt;

            // Fórmula de Bezier cuadrática
            const lat = mt2 * origen.latitud + 2 * mt * t * controlLat + t2 * destino.latitud;
            const lon = mt2 * origen.longitud + 2 * mt * t * controlLon + t2 * destino.longitud;

            waypoints.push([lat, lon]);
        }
    }

    waypoints.push([destino.latitud, destino.longitud]);
    return waypoints;
}

/**
 * Simula datos de tráfico para las conexiones
 */
function simularDatosTrafico() {
    CONEXIONES_PRINCIPALES.forEach(conexion => {
        const clave = `${conexion.origen}-${conexion.destino}`;

        // Si ya existe, hacer una variación suave
        if (estado.datosTrafico[clave]) {
            const actual = estado.datosTrafico[clave];
            estado.datosTrafico[clave] = {
                congestion: Math.max(0, Math.min(1, actual.congestion + (Math.random() - 0.5) * 0.1)),
                velocidad: Math.max(10, Math.min(60, actual.velocidad + (Math.random() - 0.5) * 5)),
                numVehiculos: Math.max(0, Math.floor(actual.numVehiculos + (Math.random() - 0.5) * 3))
            };
        } else {
            // Crear datos iniciales
            const hora = new Date().getHours();
            let factorCongestion = 0.3;

            // Hora pico
            if ((hora >= 7 && hora <= 9) || (hora >= 17 && hora <= 19)) {
                factorCongestion = 0.7;
            }

            estado.datosTrafico[clave] = {
                congestion: Math.random() * factorCongestion,
                velocidad: 20 + Math.random() * 40,
                numVehiculos: Math.floor(Math.random() * 25) + 5
            };
        }
    });
}

/**
 * Inicia la actualización periódica de tráfico
 */
function iniciarActualizacionTrafico() {
    // Detener intervalo anterior si existe
    if (estado.actualizacionTraficoInterval) {
        clearInterval(estado.actualizacionTraficoInterval);
    }

    // Primera actualización inmediata
    simularDatosTrafico();
    actualizarVisualizacionTrafico();

    // Actualizar cada 3 segundos
    estado.actualizacionTraficoInterval = setInterval(() => {
        simularDatosTrafico();
        actualizarVisualizacionTrafico();
    }, 3000);

    console.log('Sistema de tráfico visual inicializado');
}

/**
 * Limpia las líneas de tráfico del mapa
 */
function limpiarTrafico() {
    if (estado.actualizacionTraficoInterval) {
        clearInterval(estado.actualizacionTraficoInterval);
        estado.actualizacionTraficoInterval = null;
    }

    if (estado.capaTrafico) {
        estado.capaTrafico.clearLayers();
    }

    console.log('Tráfico limpiado del mapa');
}

// ==================== MODO OBTENER COORDENADAS ====================
let modoCoordenadasActivo = false;
let marcadorCoordenadas = null;

function toggleCoordMode() {
    modoCoordenadasActivo = !modoCoordenadasActivo;
    const btn = document.getElementById('toggleCoordMode');
    const panel = document.getElementById('coord-panel');
    
    if (modoCoordenadasActivo) {
        btn.textContent = '❌ Desactivar Modo Coordenadas';
        btn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        panel.classList.add('active');
        // mostrarNotificacion('🗺️ Modo coordenadas activo - Haz clic en el mapa', 'info');
        
        // Cambiar cursor del mapa
        if (estado.mapa) {
            estado.mapa.getContainer().style.cursor = 'crosshair';
        }
    } else {
        btn.textContent = '📍 Obtener Coordenadas';
        btn.style.background = 'linear-gradient(135deg, #2563eb, #1d4ed8)';
        panel.classList.remove('active');
        
        // Restaurar cursor
        if (estado.mapa) {
            estado.mapa.getContainer().style.cursor = '';
        }
        
        // Limpiar marcador temporal
        if (marcadorCoordenadas) {
            estado.mapa.removeLayer(marcadorCoordenadas);
            marcadorCoordenadas = null;
        }
    }
}

function cerrarCoordPanel() {
    modoCoordenadasActivo = false;
    const btn = document.getElementById('toggleCoordMode');
    const panel = document.getElementById('coord-panel');
    
    btn.textContent = '📍 Obtener Coordenadas';
    btn.style.background = 'linear-gradient(135deg, #2563eb, #1d4ed8)';
    panel.classList.remove('active');
    
    if (estado.mapa) {
        estado.mapa.getContainer().style.cursor = '';
    }
    
    if (marcadorCoordenadas) {
        estado.mapa.removeLayer(marcadorCoordenadas);
        marcadorCoordenadas = null;
    }
}

function mostrarCoordenadas(lat, lon) {
    document.getElementById('coord-lat').value = lat.toFixed(6);
    document.getElementById('coord-lon').value = lon.toFixed(6);
    document.getElementById('coord-full').value = `lat: ${lat.toFixed(6)}, lon: ${lon.toFixed(6)}`;
    
    // Limpiar marcador anterior
    if (marcadorCoordenadas) {
        estado.mapa.removeLayer(marcadorCoordenadas);
    }
    
    // Crear nuevo marcador temporal
    marcadorCoordenadas = L.marker([lat, lon], {
        icon: L.divIcon({
            html: '<div style="background: #ef4444; color: white; padding: 8px; border-radius: 50%; font-size: 20px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5); border: 3px solid white;">📍</div>',
            className: '',
            iconSize: [40, 40]
        })
    }).addTo(estado.mapa);
}

function copiarCoordenada(tipo) {
    let texto = '';
    
    if (tipo === 'lat') {
        texto = document.getElementById('coord-lat').value;
    } else if (tipo === 'lon') {
        texto = document.getElementById('coord-lon').value;
    } else {
        texto = document.getElementById('coord-full').value;
    }
    
    navigator.clipboard.writeText(texto).then(() => {
        mostrarNotificacion('✅ Coordenada copiada al portapapeles', 'success');
    }).catch(() => {
        mostrarNotificacion('❌ Error al copiar', 'error');
    });
}

// Interceptar clicks en el mapa cuando el modo coordenadas está activo
function setupMapClickForCoords() {
    if (!estado.mapa) return;
    
    estado.mapa.on('click', function(e) {
        if (modoCoordenadasActivo) {
            const lat = e.latlng.lat;
            const lon = e.latlng.lng;
            mostrarCoordenadas(lat, lon);
            console.log('📍 Coordenadas:', lat, lon);
        }
    });
}

// ==================== INICIALIZACIÓN ====================
// Configurar event listeners cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', configurarEventListeners);
} else {
    // El DOM ya está listo, ejecutar inmediatamente
    configurarEventListeners();
}

