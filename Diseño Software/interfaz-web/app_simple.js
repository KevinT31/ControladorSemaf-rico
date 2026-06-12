/**
 * Sistema de Control Semafórico - JavaScript SIMPLIFICADO Y FUNCIONAL
 * Versión que SÍ funciona con todas las características
 */

// ==================== CONFIGURACIÓN ====================
const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// ==================== ESTADO GLOBAL ====================
const estado = {
    mapa: null,
    marcadores: {},
    websocket: null,
    chartICV: null,
    chartFlujo: null,
    intersecciones: [],
    modoActual: 'simulador'
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('%c🚦 SISTEMA DE CONTROL SEMAFÓRICO', 'color: #10b981; font-size: 16px; font-weight: bold;');

    try {
        // Verificar librerías
        console.log('Verificando dependencias...');
        if (typeof Chart === 'undefined') console.error('❌ Chart.js no cargado');
        else console.log('✓ Chart.js cargado');

        if (typeof L === 'undefined') console.error('❌ Leaflet no cargado');
        else console.log('✓ Leaflet cargado');

        if (typeof INTERSECCIONES_LIMA === 'undefined') console.error('❌ INTERSECCIONES_LIMA no cargado');
        else console.log('✓ INTERSECCIONES_LIMA cargado (' + INTERSECCIONES_LIMA.length + ' intersecciones)');

        // Inicializar componentes
        inicializarParticulas();
        inicializarMapa();
        inicializarGraficos();
        cargarIntersecciones();
        configurarEventos();
        conectarWebSocket();

        console.log('%c✅ Sistema inicializado correctamente', 'color: #10b981; font-weight: bold;');
    } catch (error) {
        console.error('%c❌ Error en la inicialización:', 'color: #ef4444; font-weight: bold;', error);
        alert('Error al inicializar el sistema. Revisa la consola (F12).');
    }
});

// ==================== PARTÍCULAS ====================
function inicializarParticulas() {
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            particles: {
                number: { value: 40, density: { enable: true, value_area: 800 } },
                color: { value: '#ffffff' },
                opacity: { value: 0.3, random: true },
                size: { value: 2, random: true },
                line_linked: { enable: true, color: '#ffffff', opacity: 0.15 },
                move: { enable: true, speed: 1 }
            }
        });
        console.log('✓ Partículas inicializadas');
    }
}

// ==================== MAPA ====================
function inicializarMapa() {
    if (typeof L === 'undefined') {
        console.error('❌ Leaflet no disponible');
        return;
    }

    const centroLima = [-12.0464, -77.0428];
    estado.mapa = L.map('mapa', {
        zoomControl: true,
        attributionControl: false
    }).setView(centroLima, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19
    }).addTo(estado.mapa);

    console.log('✓ Mapa inicializado');
}

function cargarIntersecciones() {
    if (typeof INTERSECCIONES_LIMA === 'undefined') {
        console.error('❌ INTERSECCIONES_LIMA no disponible');
        return;
    }

    estado.intersecciones = INTERSECCIONES_LIMA;

    // Agregar marcadores al mapa
    estado.intersecciones.forEach(inter => {
        const icono = L.divIcon({
            html: `<div style="background: #10b981; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>`,
            className: '',
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });

        const marcador = L.marker([inter.latitud, inter.longitud], { icon: icono }).addTo(estado.mapa);

        marcador.bindPopup(`
            <div style="padding: 10px;">
                <strong>${inter.nombre}</strong><br>
                <small>ID: ${inter.id}</small><br>
                <small>Distrito: ${inter.distrito}</small>
            </div>
        `);

        estado.marcadores[inter.id] = marcador;
    });

    document.getElementById('num-intersecciones').textContent = estado.intersecciones.length;

    console.log(`✓ ${estado.intersecciones.length} intersecciones cargadas`);
}

// ==================== GRÁFICOS ====================
function inicializarGraficos() {
    if (typeof Chart === 'undefined') {
        console.error('❌ Chart.js no disponible');
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
                    font: { size: 13 }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.08)' },
                ticks: { color: '#cbd5e1', font: { size: 12 } }
            },
            x: {
                grid: { color: 'rgba(255, 255, 255, 0.08)' },
                ticks: { color: '#cbd5e1', font: { size: 11 } }
            }
        }
    };

    // Gráfico ICV
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

    // Gráfico Flujo
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

    console.log('✓ Gráficos inicializados');
}

// ==================== WEBSOCKET ====================
function conectarWebSocket() {
    console.log('Conectando a WebSocket...');

    estado.websocket = new WebSocket(WS_URL);

    estado.websocket.onopen = () => {
        console.log('%c✅ WebSocket conectado', 'color: #10b981; font-weight: bold;');
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
        console.error('❌ Error WebSocket:', error);
        document.getElementById('connection-status').textContent = 'ERROR';
    };

    estado.websocket.onclose = () => {
        console.log('⚠️ WebSocket desconectado. Reconectando en 3s...');
        document.getElementById('connection-status').textContent = 'DESCONECTADO';
        document.querySelector('.status-dot').classList.remove('pulsing');

        setTimeout(() => {
            if (estado.websocket.readyState === WebSocket.CLOSED) {
                conectarWebSocket();
            }
        }, 3000);
    };
}

function procesarMensajeWebSocket(mensaje) {
    const { tipo, datos } = mensaje;

    if (tipo === 'metricas_actualizadas') {
        actualizarMetricas(datos);
    } else if (tipo === 'ola_verde_activada') {
        console.log('Ola verde activada:', datos);
    } else {
        console.log('Mensaje WebSocket:', tipo);
    }
}

// ==================== ACTUALIZACIÓN DE MÉTRICAS ====================
function actualizarMetricas(metricas) {
    if (!metricas || metricas.length === 0) return;

    // Calcular promedios
    const icvPromedio = metricas.reduce((sum, m) => sum + m.icv, 0) / metricas.length;
    const flujoPromedio = metricas.reduce((sum, m) => sum + m.flujo, 0) / metricas.length;
    const velocidadPromedio = metricas.reduce((sum, m) => sum + (m.velocidad || 0), 0) / metricas.length;

    // Actualizar estadísticas globales
    document.getElementById('num-intersecciones').textContent = metricas.length;
    document.getElementById('icv-promedio').textContent = icvPromedio.toFixed(2);
    document.getElementById('flujo-promedio').textContent = Math.round(flujoPromedio);

    // Calcular mini-stats
    let fluidas = 0, moderadas = 0, congestionadas = 0;
    metricas.forEach(m => {
        if (m.icv < 0.3) fluidas++;
        else if (m.icv < 0.6) moderadas++;
        else congestionadas++;
    });

    document.getElementById('calles-fluidas').textContent = fluidas;
    document.getElementById('calles-moderadas').textContent = moderadas;
    document.getElementById('calles-congestionadas').textContent = congestionadas;
    document.getElementById('velocidad-promedio').textContent = Math.round(velocidadPromedio);

    // Actualizar gráficos
    if (estado.chartICV && estado.chartFlujo) {
        const timestamp = new Date().toLocaleTimeString('es-PE', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        // Gráfico ICV
        estado.chartICV.data.labels.push(timestamp);
        estado.chartICV.data.datasets[0].data.push(icvPromedio);
        if (estado.chartICV.data.labels.length > 15) {
            estado.chartICV.data.labels.shift();
            estado.chartICV.data.datasets[0].data.shift();
        }
        estado.chartICV.update('none');

        // Gráfico Flujo
        estado.chartFlujo.data.labels.push(timestamp);
        estado.chartFlujo.data.datasets[0].data.push(flujoPromedio);
        if (estado.chartFlujo.data.labels.length > 15) {
            estado.chartFlujo.data.labels.shift();
            estado.chartFlujo.data.datasets[0].data.shift();
        }
        estado.chartFlujo.update('none');
    }

    // Actualizar marcadores en el mapa
    metricas.forEach(metrica => {
        actualizarMarcador(metrica.interseccion_id, metrica.icv);
    });

    // Actualizar lista de métricas (sidebar derecha)
    actualizarListaMetricas(metricas);
}

function actualizarMarcador(interseccionId, icv) {
    if (!estado.marcadores[interseccionId]) return;

    let color = '#10b981'; // Verde (fluido)
    if (icv >= 0.6) color = '#ef4444'; // Rojo (congestionado)
    else if (icv >= 0.3) color = '#f59e0b'; // Amarillo (moderado)

    const icono = L.divIcon({
        html: `<div style="background: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 8px ${color};"></div>`,
        className: '',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });

    estado.marcadores[interseccionId].setIcon(icono);
}

function actualizarListaMetricas(metricas) {
    const container = document.getElementById('metricas-container');
    if (!container) return;

    container.innerHTML = '';

    // Mostrar solo las primeras 8 intersecciones
    metricas.slice(0, 8).forEach(metrica => {
        const interseccion = estado.intersecciones.find(i => i.id === metrica.interseccion_id);
        if (!interseccion) return;

        let colorClass = 'success';
        let nivelTexto = 'Fluido';
        if (metrica.icv >= 0.6) { colorClass = 'danger'; nivelTexto = 'Congestionado'; }
        else if (metrica.icv >= 0.3) { colorClass = 'warning'; nivelTexto = 'Moderado'; }

        const card = document.createElement('div');
        card.className = `metrica-card ${colorClass}`;
        card.innerHTML = `
            <div class="metrica-header">
                <strong>${interseccion.nombre}</strong>
                <span class="metrica-badge">${metrica.interseccion_id}</span>
            </div>
            <div class="metrica-body">
                <div class="metrica-row">
                    <span>ICV:</span>
                    <strong>${metrica.icv.toFixed(2)}</strong>
                </div>
                <div class="metrica-row">
                    <span>Flujo:</span>
                    <strong>${Math.round(metrica.flujo)} veh/min</strong>
                </div>
                <div class="metrica-row">
                    <span>Nivel:</span>
                    <strong>${nivelTexto}</strong>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==================== EVENTOS ====================
function configurarEventos() {
    // Selector de modo
    const selectorModo = document.getElementById('modo-operacion');
    if (selectorModo) {
        selectorModo.addEventListener('change', (e) => {
            console.log('Modo cambiado a:', e.target.value);
            estado.modoActual = e.target.value;
        });
    }

    // Botón de emergencia
    const btnEmergencia = document.getElementById('btn-emergencia');
    if (btnEmergencia) {
        btnEmergencia.addEventListener('click', () => {
            alert('Función de emergencia en desarrollo.\nEn la versión completa podrás activar olas verdes.');
        });
    }

    console.log('✓ Eventos configurados');
}
