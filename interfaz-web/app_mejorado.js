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
    chartICV: null,
    chartFlujo: null,
    estadisticas: {
        flujoTotal: 0,
        contadorActualizaciones: 0,
        tiempoInicio: Date.now()
    },
    modoActual: 'simulador',
    simulacionInterval: null,
    actualizacionTraficoInterval: null,
    capaTrafico: null,  // Layer group para calles con tráfico
    datosTrafico: {}  // Datos de tráfico por conexión
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Inicializando sistema...');

    try {
        // Inicializar componentes
        console.log('Iniciando partículas...');
        inicializarParticulas();

        console.log('Iniciando mapa...');
        inicializarMapa();

        console.log('Iniciando gráficos...');
        inicializarGraficos();

        console.log('Cargando intersecciones...');
        cargarInterseccionesReales();

        console.log('Configurando eventos...');
        configurarEventListeners();

        console.log('Conectando WebSocket...');
        conectarWebSocket();  // CRITICO: Conectar WebSocket para recibir actualizaciones

        // NO iniciar simulación local automáticamente
        // Solo se iniciará como fallback si el WebSocket no conecta en 5 segundos
        setTimeout(() => {
            if (!estado.backendConectado && estado.modoActual === 'simulador') {
                console.warn('Backend no responde, usando simulación local como fallback');
                iniciarSimulacion();
            }
        }, 5000);

        console.log('Sistema inicializado correctamente');
    } catch (error) {
        console.error('ERROR en la inicialización:', error);
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

    console.log('Mapa inicializado');
}

function agregarMarcadorInterseccion(interseccion) {
    const colorZona = ZONAS_LIMA[interseccion.zona].color;

    // Marcador con etiqueta de ID
    const icono = L.divIcon({
        html: `<div class="marcador-container">
                   <div class="marcador-semaforo" data-zona="${interseccion.zona}">
                       <div class="semaforo-luz luz-activa"></div>
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
}

function dibujarConexiones() {
    // Limpiar líneas existentes
    estado.lineas.forEach(linea => estado.mapa.removeLayer(linea));
    estado.lineas = [];

    CONEXIONES_PRINCIPALES.forEach(conexion => {
        const origen = INTERSECCIONES_LIMA.find(i => i.id === conexion.origen);
        const destino = INTERSECCIONES_LIMA.find(i => i.id === conexion.destino);

        if (origen && destino) {
            const linea = L.polyline(
                [[origen.latitud, origen.longitud], [destino.latitud, destino.longitud]],
                {
                    color: '#4a5568',
                    weight: 2,
                    opacity: 0.4,
                    dashArray: '5, 10'
                }
            ).addTo(estado.mapa);

            linea.bindTooltip(conexion.via, {
                permanent: false,
                direction: 'center',
                className: 'tooltip-ruta'
            });

            estado.lineas.push(linea);
        }
    });

    console.log(`${estado.lineas.length} conexiones dibujadas`);
}

function actualizarColorMarcador(interseccionId, icv) {
    const marcador = estado.marcadores[interseccionId];
    if (!marcador) return;

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

    // Agregar marcadores
    estado.intersecciones.forEach(inter => {
        agregarMarcadorInterseccion(inter);
    });

    // Dibujar conexiones
    dibujarConexiones();

    // Actualizar contador
    document.getElementById('num-intersecciones').textContent = estado.intersecciones.length;

    // Llenar selects
    llenarSelectsEmergencia();

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
}

function generarMetricasSimuladas() {
    const hora = new Date().getHours();
    let factorHora = 1.0;

    // Simular hora pico
    if ((hora >= 7 && hora <= 9) || (hora >= 17 && hora <= 19)) {
        factorHora = 1.8; // Más congestión
    } else if (hora >= 22 || hora <= 6) {
        factorHora = 0.3; // Menos tráfico
    }

    return estado.intersecciones.map(inter => {
        const baseICV = Math.random() * 0.3 + (factorHora > 1.5 ? 0.5 : 0.2);
        const icv = Math.min(baseICV * factorHora, 0.95);

        const numVehiculos = Math.floor(10 + Math.random() * 40 * factorHora);
        const flujo = 15 + Math.random() * 20 * factorHora;
        const velocidad = icv < 0.3 ? (50 + Math.random() * 10) :
                         icv < 0.6 ? (25 + Math.random() * 20) :
                         (10 + Math.random() * 15);
        const cola = icv * 150;

        let color;
        if (icv < 0.3) color = '#10b981';
        else if (icv < 0.6) color = '#f59e0b';
        else color = '#ef4444';

        return {
            interseccion_id: inter.id,
            interseccion_nombre: inter.nombre,
            icv: parseFloat(icv.toFixed(3)),
            num_vehiculos: numVehiculos,
            flujo: parseFloat(flujo.toFixed(1)),
            velocidad: parseFloat(velocidad.toFixed(1)),
            cola: parseFloat(cola.toFixed(1)),
            color: color,
            nivel: icv < 0.3 ? 'Bajo' : icv < 0.6 ? 'Medio' : 'Alto'
        };
    });
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

    // 2. Calcular promedios
    const icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / metricas.length;
    const flujoPromedio = metricas.reduce((sum, m) => sum + m.flujo, 0) / metricas.length;

    // 3. Actualizar cada intersección
    metricas.forEach(metrica => {
        const { interseccion_id, icv, clasificacion, color, flujo, velocidad, cola } = metrica;

        // Actualizar marcador en el mapa
        actualizarColorMarcador(interseccion_id, icv);

        // Actualizar o crear tarjeta de métrica
        actualizarTarjetaMetrica(interseccion_id, {
            icv,
            clasificacion: clasificacion || (icv < 0.3 ? 'Fluido' : icv < 0.6 ? 'Moderado' : 'Congestionado'),
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

    // 6. Actualizar sistema difuso
    actualizarSistemaDifuso(metricas);

    // 7. Actualizar contador de decisiones
    estado.estadisticas.contadorActualizaciones++;
    document.getElementById('decisiones-tomadas').textContent = estado.estadisticas.contadorActualizaciones;

    // 8. Calcular olas verdes activas (intersecciones con alto tráfico)
    const olasActivas = metricas.filter(m => m.icv > 0.6).length;
    document.getElementById('olas-activas').textContent = olasActivas;
}

function actualizarMetricas(metricas) {
    // Función legacy - ahora usa la función unificada
    actualizarDatosInterfaz(metricas, 'local');
}

// FUNCIÓN OBSOLETA - Se mantiene por compatibilidad pero ya no se usa internamente
function actualizarMetricas_OLD(metricas) {
    const container = document.getElementById('metricas-container');

    // Calcular promedios
    const icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / metricas.length;
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

    // NUEVO: Botones de video YOLO
    document.getElementById('btn-toggle-video')?.addEventListener('click', toggleVideoYOLO);
    document.getElementById('btn-expand-video')?.addEventListener('click', toggleExpandVideo);

    // NUEVO: Doble clic en canvas para expandir
    document.getElementById('video-canvas')?.addEventListener('dblclick', toggleExpandVideo);

    // NUEVO: Selector de intersección para cámara
    document.getElementById('selector-interseccion-cam')?.addEventListener('change', seleccionarInterseccionCamara);

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

    console.log('Event listeners configurados');
}

async function cambiarModo(event) {
    const nuevoModo = event.target.value;
    estado.modoActual = nuevoModo;

    console.log(`Cambiando modo a: ${nuevoModo}`);

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
            iniciarSimulacion();
            if (!estado.actualizacionTraficoInterval) {
                iniciarActualizacionTrafico();
            }
            document.getElementById('selector-interseccion-cam').style.display = 'block';
            cargarInterseccionesSimulador();
            break;
        case 'video':
            console.log('Modo video seleccionado');
            limpiarTrafico();
            document.getElementById('selector-interseccion-cam').style.display = 'block';
            await cargarInterseccionesVideo();
            break;
        case 'sumo':
            console.log('Modo SUMO - Cargando visualizacion de trafico');
            limpiarTrafico();
            await cargarYVisualizarCallesSUMO();
            break;
    }
}

// ==================== EMERGENCIAS ====================
function llenarSelectsEmergencia() {
    const origenSelect = document.getElementById('origen-emergencia');
    const destinoSelect = document.getElementById('destino-emergencia');

    estado.intersecciones.forEach(inter => {
        origenSelect.innerHTML += `<option value="${inter.id}">${inter.nombre}</option>`;
        destinoSelect.innerHTML += `<option value="${inter.id}">${inter.nombre}</option>`;
    });
}

function abrirModalEmergencia() {
    document.getElementById('modal-emergencia').style.display = 'flex';
}

function cerrarModalEmergencia() {
    document.getElementById('modal-emergencia').style.display = 'none';
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
    const destino = document.getElementById('destino-emergencia').value;
    const velocidad = parseFloat(document.getElementById('velocidad-emergencia').value);

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

    console.log('Activando ola verde con prioridad:', {
        tipo,
        origen,
        destino,
        velocidad,
        prioridad: prioridad.nivel,
        peso: prioridad.peso
    });

    try {
        // Intentar llamar al backend para calcular ruta óptima con Dijkstra
        const response = await fetch(`${API_URL}/api/emergencia/activar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tipo: tipo,
                origen: origen,
                destino: destino,
                velocidad: velocidad,
                prioridad: prioridad.peso,
                nivel_prioridad: prioridad.nivel
            })
        });

        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status}`);
        }

        const resultado = await response.json();

        console.log('Ruta calculada por backend:', resultado);

        // Verificar que haya una ruta válida
        if (!resultado.ruta || resultado.ruta.length < 2) {
            alert('No se pudo encontrar una ruta entre las intersecciones seleccionadas.');
            return;
        }

        // Usar la función que procesa correctamente la respuesta del backend
        mostrarOlaVerdeActivada(resultado);

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
        const tiempoEstimado = (distanciaTotal / 1000) / (velocidad / 3600); // segundos

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
        mostrarOlaVerdeActivada(resultado);
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
    // Limpiar polyline principal
    if (estado.olaVerdeActiva) {
        estado.mapa.removeLayer(estado.olaVerdeActiva);
        estado.olaVerdeActiva = null;
    }

    // Limpiar marcadores y sombra
    if (estado.marcadoresOlaVerde) {
        estado.marcadoresOlaVerde.forEach(m => {
            try {
                estado.mapa.removeLayer(m);
            } catch (e) {
                console.log('Error limpiando marcador:', e);
            }
        });
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

    console.log('Ola verde desactivada');
}

// Actualizar display de velocidad en el modal
document.getElementById('velocidad-emergencia')?.addEventListener('input', function() {
    document.getElementById('velocidad-display').textContent = this.value + ' km/h';
});

// Actualizar indicador de prioridad cuando cambia el tipo de vehículo
document.getElementById('tipo-emergencia')?.addEventListener('change', function() {
    actualizarIndicadorPrioridad(this.value);
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
            }
        }).addTo(estado.mapa);

        console.log('[OK] Calles visualizadas en el mapa');

        // Iniciar actualización de tráfico cada 2 segundos
        actualizarTraficoSUMO();
        estado.actualizacionTraficoInterval = setInterval(actualizarTraficoSUMO, 2000);

    } catch (error) {
        console.error('Error cargando calles SUMO:', error);
        alert('Error al cargar visualización de calles SUMO');
    }
}

async function actualizarTraficoSUMO() {
    if (estado.modoActual !== 'sumo' || !estado.callesSUMO) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/sumo/trafico`);
        const data = await response.json();

        if (!data.calles || data.calles.length === 0) {
            return;
        }

        // Crear mapa de congestión por ID de calle
        const congestionPorCalle = {};
        data.calles.forEach(calle => {
            congestionPorCalle[calle.id] = calle.congestion;
        });

        // Actualizar colores de las calles
        estado.callesSUMO.eachLayer(function(layer) {
            const feature = layer.feature;
            const idCalle = feature.properties.id;
            const congestion = congestionPorCalle[idCalle];

            if (congestion !== undefined) {
                // Determinar color según nivel de congestión
                let color;
                if (congestion < 0.3) {
                    color = '#10b981';  // Verde - fluido
                } else if (congestion < 0.6) {
                    color = '#f59e0b';  // Amarillo - moderado
                } else {
                    color = '#ef4444';  // Rojo - congestionado
                }

                layer.setStyle({
                    color: color,
                    weight: 3,
                    opacity: 0.7
                });
            }
        });

    } catch (error) {
        console.error('Error actualizando tráfico SUMO:', error);
    }
}

function limpiarCallesSUMO() {
    if (estado.callesSUMO) {
        estado.mapa.removeLayer(estado.callesSUMO);
        estado.callesSUMO = null;
        estado.callesGeoJSON = null;
        console.log('Calles SUMO limpiadas del mapa');
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

    switch (tipo) {
        case 'metricas_actualizadas':
            actualizarMetricasDesdeBackend(datos);
            break;

        case 'ola_verde_activada':
            mostrarOlaVerdeActivada(datos);
            break;

        case 'modo_cambiado':
            console.log(`Modo cambiado a: ${datos.modo}`);
            break;

        default:
            console.log('Mensaje WebSocket desconocido:', tipo);
    }
}

function actualizarMetricasDesdeBackend(metricas) {
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

// ==================== MODO VIDEO CON YOLO ====================

let streamVideo = null;
let procesandoVideo = false;
let intervaloVideo = null;
let intervaloMetricas = null;

async function activarModoVideo(videoIndex) {
    try {
        console.log(`Activando MIR ${String(videoIndex).padStart(3, '0')}...`);

        const canvas = document.getElementById('video-canvas');
        const ctx = canvas.getContext('2d');

        const imgElement = document.createElement('img');
        imgElement.style.display = 'none';
        document.body.appendChild(imgElement);

        let streamUrl;
        const esCamara = (videoIndex === 0);

        if (esCamara) {
            console.log('Conectando a camara de laptop...');
            streamUrl = `${API_URL}/api/video/stream-camera?t=${Date.now()}`;
        } else {
            console.log(`Conectando a video procesado (indice ${videoIndex - 1})...`);
            streamUrl = `${API_URL}/api/video/stream-video-index/${videoIndex - 1}?t=${Date.now()}`;
        }

        console.log('URL del stream:', streamUrl);
        imgElement.src = streamUrl;
        procesandoVideo = true;

        const actualizarCanvas = () => {
            if (!procesandoVideo || estado.modoActual !== 'video') {
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

        const actualizarMetricas = async () => {
            try {
                const response = await fetch(`${API_URL}/api/video/metricas-stream`);
                const metricas = await response.json();

                document.getElementById('video-vehiculos').textContent = metricas.num_vehiculos;
                document.getElementById('video-fps').textContent = metricas.fps;
                document.getElementById('video-icv').textContent = metricas.icv.toFixed(2);
            } catch (error) {
                console.error('Error obteniendo metricas:', error);
            }
        };

        imgElement.onload = () => {
            console.log('Stream conectado exitosamente');
            actualizarCanvas();

            if (esCamara) {
                intervaloMetricas = setInterval(actualizarMetricas, 1000);
            }
        };

        imgElement.onerror = () => {
            console.error('Error conectando al stream');
            console.error('URL intentada:', streamUrl);
            alert('Error al conectar con el stream.\n\nAsegurate de que:\n1. El servidor backend esta corriendo\n2. La URL es correcta: ' + streamUrl);
            detenerModoVideo();
        };

        streamVideo = imgElement;
        console.log('[OK] Modo video activado');

    } catch (error) {
        console.error('Error activando modo video:', error);
        alert('Error al activar el modo video. Ver consola para mas detalles.');
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

        data.videos.forEach((video, index) => {
            const option = document.createElement('option');
            option.value = String(index + 1);
            const mirNumber = String(index + 1).padStart(3, '0');
            option.textContent = `MIR ${mirNumber} - ${video.nombre}`;
            selector.appendChild(option);
        });

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

function mostrarOlaVerdeActivada(datos) {
    console.log('Mostrando ola verde:', datos);

    // Limpiar ola verde anterior si existe
    if (estado.olaVerdeActiva) {
        estado.mapa.removeLayer(estado.olaVerdeActiva);
    }

    // Obtener ruta de la ola verde
    const ruta = datos.ruta || [];
    if (ruta.length < 2) {
        console.log('Ruta de ola verde vacía o inválida');
        return;
    }

    // Convertir IDs a coordenadas
    const coordenadas = ruta.map(id => {
        const inter = INTERSECCIONES_LIMA.find(i => i.id === id);
        return inter ? [inter.latitud, inter.longitud] : null;
    }).filter(c => c !== null);

    if (coordenadas.length < 2) {
        console.log('No se pudieron obtener coordenadas para la ruta');
        return;
    }

    // Dibujar ruta animada con color VERDE (ola verde!)
    estado.olaVerdeActiva = L.polyline(coordenadas, {
        color: '#10b981',  // Verde brillante
        weight: 8,
        opacity: 0.9,
        dashArray: '15, 10',
        lineCap: 'round',
        lineJoin: 'round',
        className: 'ruta-emergencia-animada'
    }).addTo(estado.mapa);

    // Línea de sombra para mejor visibilidad
    const sombraOlaVerde = L.polyline(coordenadas, {
        color: '#000000',
        weight: 10,
        opacity: 0.3,
        dashArray: '15, 10',
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(estado.mapa);

    // Almacenar marcadores para limpieza posterior
    if (!estado.marcadoresOlaVerde) {
        estado.marcadoresOlaVerde = [];
    }

    // Limpiar marcadores anteriores
    estado.marcadoresOlaVerde.forEach(m => estado.mapa.removeLayer(m));
    estado.marcadoresOlaVerde = [];

    // Agregar marcadores en origen y destino
    const origen = coordenadas[0];
    const destino = coordenadas[coordenadas.length - 1];

    const markerOrigen = L.marker(origen, {
        icon: L.divIcon({
            html: '<div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 8px; border-radius: 50%; font-size: 24px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.5); border: 3px solid white;">🚦</div>',
            className: '',
            iconSize: [50, 50]
        })
    }).addTo(estado.mapa).bindPopup('<b style="color: #10b981;">Origen</b>');

    const markerDestino = L.marker(destino, {
        icon: L.divIcon({
            html: '<div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 8px; border-radius: 50%; font-size: 24px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5); border: 3px solid white;">🏁</div>',
            className: '',
            iconSize: [50, 50]
        })
    }).addTo(estado.mapa).bindPopup('<b style="color: #ef4444;">Destino</b>');

    estado.marcadoresOlaVerde.push(markerOrigen, markerDestino, sombraOlaVerde);

    // Centrar mapa en la ruta
    estado.mapa.fitBounds(coordenadas);

    // Actualizar panel de olas verdes
    const container = document.getElementById('olas-verdes-container');
    container.innerHTML = `
        <div class="ola-verde-activa">
            <div class="ola-header">
                <i class="fas fa-ambulance"></i>
                <strong>Ola Verde Activa</strong>
            </div>
            <div class="ola-info">
                <p><strong>Vehículo:</strong> ${datos.vehiculo?.tipo || 'Emergencia'}</p>
                <p><strong>Intersecciones:</strong> ${ruta.length}</p>
                <p><strong>Distancia:</strong> ${(datos.distancia_total || 0).toFixed(0)} m</p>
                <p><strong>Tiempo estimado:</strong> ${(datos.tiempo_estimado || 0).toFixed(0)} s</p>
            </div>
        </div>
    `;

    // Desactivar automáticamente después de cierto tiempo
    setTimeout(() => {
        desactivarOlaVerde();
    }, (datos.tiempo_estimado || 30) * 1000);
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

// Toggle activar/desactivar video YOLO
function toggleVideoYOLO() {
    const btn = document.getElementById('btn-toggle-video');
    const icon = btn.querySelector('i');
    const indicator = document.querySelector('.camera-mode-indicator');
    const texto = document.getElementById('modo-camara-texto');

    if (estadoVideo.activo) {
        estadoVideo.activo = false;
        icon.classList.remove('fa-stop');
        icon.classList.add('fa-play');
        btn.title = 'Activar Cámara';
        indicator.classList.remove('active');
        texto.textContent = 'Desactivado';

        if (estado.modoActual === 'video') {
            detenerModoVideo();
            const selector = document.getElementById('selector-interseccion-cam');
            selector.value = '';
        } else {
            detenerSimulacionVideoInterseccion();
        }

        console.log('Video desactivado');
    } else {
        if (estado.modoActual === 'video') {
            alert('Por favor selecciona una opcion MIR del selector');
        } else {
            if (estado.modoActual === 'video') {
                detenerModoVideo();
            }

            estadoVideo.activo = true;
            icon.classList.remove('fa-play');
            icon.classList.add('fa-stop');
            btn.title = 'Desactivar Cámara';
            indicator.classList.add('active');
            texto.textContent = 'Activo';

            window.motorGiratorioAnimacion.anguloObjetivo = estadoVideo.ptz.pan;
            iniciarSimulacionVideoInterseccion();

            console.log('Video activado');
        }
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

    const icon = btn.querySelector('i');
    if (!icon) {
        console.error('Ícono del botón expandir no encontrado');
        return;
    }

    // Toggle estado
    estadoVideo.expandido = !estadoVideo.expandido;

    if (estadoVideo.expandido) {
        // Expandir panel
        panel.classList.add('expanded');
        icon.classList.remove('fa-expand');
        icon.classList.add('fa-compress');
        btn.title = 'Contraer (ESC)';
        document.body.style.overflow = 'hidden';
        console.log('Panel de video expandido');
    } else {
        // Contraer panel
        panel.classList.remove('expanded');
        icon.classList.remove('fa-compress');
        icon.classList.add('fa-expand');
        btn.title = 'Expandir';
        document.body.style.overflow = '';
        console.log('Panel de video contraído');
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

    if (!interseccionId) {
        estadoVideo.interseccionSeleccionada = null;
        return;
    }

    estadoVideo.interseccionSeleccionada = interseccionId;
    const interseccion = INTERSECCIONES_LIMA.find(i => i.id === interseccionId);

    if (interseccion) {
        console.log(`Intersección seleccionada: ${interseccion.nombre}`);

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
    if (!estadoVideo.interseccionSeleccionada) {
        console.warn('No hay intersección seleccionada para simular video');
        return;
    }

    const canvas = document.getElementById('video-canvas');
    const ctx = canvas.getContext('2d');

    // Simular video con datos de la intersección
    estado.simulacionVideoInterval = setInterval(() => {
        if (!estadoVideo.activo) {
            clearInterval(estado.simulacionVideoInterval);
            return;
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

    console.log('Simulación de video de intersección iniciada');
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

    // Añadir nuevos vehículos aleatoriamente
    if (Math.random() < 0.15 && window.vehiculosAnimados.length < 12) {
        const direccion = ['norte', 'sur', 'este', 'oeste'][Math.floor(Math.random() * 4)];
        const pista = Math.random() > 0.5 ? 0 : 1; // 0 = pista izquierda/superior, 1 = pista derecha/inferior

        const vehiculo = {
            direccion: direccion,
            pista: pista,
            color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][Math.floor(Math.random() * 5)],
            velocidad: 60 + Math.random() * 40, // píxeles por segundo
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
    // En implementación real, esto consultaría las métricas reales
    // Por ahora, retornamos valores simulados
    return {
        vehiculos: Math.floor(Math.random() * 15) + 5,
        fps: 5,
        icv: (Math.random() * 0.6 + 0.2).toFixed(2)
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
    // Inicializar sistema de tráfico (SIN vehículos animados)
    setTimeout(() => {
        inicializarCapaTrafico();
        iniciarActualizacionTrafico();
    }, 1000);
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
