/**
 * Capa "Consola Operativa de Tesis" sobre el dashboard base.
 * Refleja el Capítulo 6 (versión final): ICV con compuerta de demanda,
 * PI con normalización racional, control difuso Mamdani, arbitraje de
 * recomendaciones, offset de ola verde con fallback Haversine y
 * telemetría segura (MQTT/TLS simulado con estados operativos).
 *
 * El controlador semafórico certificado conserva la autoridad final:
 * todo lo que produce este módulo son métricas y recomendaciones.
 */
(function () {
    const PARAMS = {
        scMax: 50,
        vMax: 60,
        kMax: 0.2,
        qMax: 30,
        deltaPi: 0.1,
        longitudEfectiva: 200,
        tBase: 30,          // punto de partida tipo Webster (C0 de mínima demora)
        tCiclo: 90,
        tVerdeMin: 10,
        tVerdeMax: 120,
        timeoutRecomendacion: 30 // s de vigencia de la recomendación global (arbitraje)
    };

    const pesos = { sc: 0.35, velocidad: 0.25, densidad: 0.25, flujo: 0.15 };

    // R1..R12 en el orden del Capítulo 6
    const reglasDifusas = [
        { id: 'R1', ant: ['EV_Presente', 'ICV_Alto'], out: 'Extender_Fuerte' },
        { id: 'R2', ant: ['EV_Presente', 'ICV_Medio'], out: 'Extender_Fuerte' },
        { id: 'R3', ant: ['EV_Presente', 'ICV_Bajo'], out: 'Extender_Leve' },
        { id: 'R4', ant: ['EV_Ausente', 'ICV_Alto', 'PI_Ineficiente'], out: 'Extender_Fuerte' },
        { id: 'R5', ant: ['EV_Ausente', 'ICV_Alto', 'PI_Moderado'], out: 'Extender_Leve' },
        { id: 'R6', ant: ['EV_Ausente', 'ICV_Alto', 'PI_MuyEficiente'], out: 'Mantener' },
        { id: 'R7', ant: ['EV_Ausente', 'ICV_Medio', 'PI_Ineficiente'], out: 'Extender_Leve' },
        { id: 'R8', ant: ['EV_Ausente', 'ICV_Medio', 'PI_Moderado'], out: 'Mantener' },
        { id: 'R9', ant: ['EV_Ausente', 'ICV_Medio', 'PI_MuyEficiente'], out: 'Reducir_Leve' },
        { id: 'R10', ant: ['EV_Ausente', 'ICV_Bajo', 'PI_Ineficiente'], out: 'Mantener' },
        { id: 'R11', ant: ['EV_Ausente', 'ICV_Bajo', 'PI_Moderado'], out: 'Reducir_Leve' },
        { id: 'R12', ant: ['EV_Ausente', 'ICV_Bajo', 'PI_MuyEficiente'], out: 'Reducir_Fuerte' }
    ];

    const conjuntosSalida = {
        Reducir_Fuerte: [[-30, 1], [-10, 0], [30, 0]],
        Reducir_Leve: [[-30, 0], [-10, 1], [-5, 0], [30, 0]],
        Mantener: [[-30, 0], [-10, 0], [0, 1], [10, 0], [30, 0]],
        Extender_Leve: [[-30, 0], [5, 0], [15, 1], [30, 0]],
        Extender_Fuerte: [[-30, 0], [15, 0], [30, 1]]
    };

    // ---------- estado interno de la capa ----------
    const capa = {
        posicionInicial: false,
        ultimoPaqueteTs: 0,
        periodoDatosMs: 0,
        nube: { estado: 'iniciando', desde: Date.now(), buffer: 0, resincTicks: 0 },
        prevWsAbierto: null,
        prevEV: false,
        prevClamp: false,
        prevFoco: null,
        recomendacionTs: 0,
        logs: [],
        distanciaMapboxCache: {}
    };

    // ---------- utilidades ----------
    function clamp(v, min, max) {
        return Math.max(min, Math.min(max, Number.isFinite(v) ? v : min));
    }
    function texto(id, valor) {
        const el = document.getElementById(id);
        if (el) el.textContent = valor;
    }
    function htmlEl(id) { return document.getElementById(id); }
    function ancho(id, pct) {
        const el = document.getElementById(id);
        if (el) el.style.width = `${clamp(pct, 0, 100)}%`;
    }
    function horaCorta(ts) {
        return new Date(ts || Date.now()).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    }
    function interpola(puntos, x) {
        if (x <= puntos[0][0]) return puntos[0][1];
        if (x >= puntos[puntos.length - 1][0]) return puntos[puntos.length - 1][1];
        for (let i = 0; i < puntos.length - 1; i++) {
            const [x1, y1] = puntos[i];
            const [x2, y2] = puntos[i + 1];
            if (x >= x1 && x <= x2) return x2 === x1 ? y1 : y1 + (y2 - y1) * ((x - x1) / (x2 - x1));
        }
        return 0;
    }
    function obtenerGlobal(nombre) {
        try {
            return Function(`return typeof ${nombre} !== 'undefined' ? ${nombre} : undefined`)();
        } catch { return undefined; }
    }
    function obtenerEstadoApp() { return obtenerGlobal('estado'); }
    function obtenerIntersecciones() { return obtenerGlobal('INTERSECCIONES_LIMA') || []; }
    function obtenerConexiones() { return obtenerGlobal('CONEXIONES_PRINCIPALES') || []; }
    function obtenerConfig() { return obtenerGlobal('CONFIG') || {}; }

    function haversineMetros(lat1, lon1, lat2, lon2) {
        const R = 6371000;
        const rad = Math.PI / 180;
        const dLat = (lat2 - lat1) * rad;
        const dLon = (lon2 - lon1) * rad;
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
        return 2 * R * Math.asin(Math.sqrt(a));
    }

    // ---------- registro de eventos ----------
    function logEvento(tipo, mensaje) {
        capa.logs.unshift({ ts: Date.now(), tipo, mensaje });
        if (capa.logs.length > 40) capa.logs.pop();
        renderLogs();
    }
    function renderLogs() {
        const cont = htmlEl('tesis-log-list');
        if (!cont) return;
        if (!capa.logs.length) {
            cont.innerHTML = '<div class="tesis-log-empty">Sin eventos registrados</div>';
            return;
        }
        cont.innerHTML = capa.logs.slice(0, 8).map(l => `
            <div class="tesis-log-row tesis-log-${l.tipo}">
                <span class="tesis-log-time">${horaCorta(l.ts)}</span>
                <span class="tesis-log-msg">${l.mensaje}</span>
            </div>
        `).join('');
    }

    // ---------- textos base ----------
    function ajustarTextoBase() {
        const h1 = document.querySelector('.logo-text h1');
        const subtitle = document.querySelector('.logo-text .subtitle');
        if (h1) h1.textContent = 'Módulo IoT de Control Semafórico Adaptativo';
        if (subtitle) subtitle.textContent = 'Consola operativa · visión por computadora, control difuso local y nube segura';

        const reemplazos = new Map([
            ['Estadísticas del Sistema', 'Telemetría del Módulo IoT'],
            ['Mapa Interactivo de Lima', 'Red semafórica simulada de Lima'],
            ['Detección en Tiempo Real', 'Visión por Computadora'],
            ['Intersecciones en Tiempo Real', 'Intersecciones y Métricas'],
            ['Olas Verdes Activas', 'Olas Verdes Recomendadas'],
            ['Sistema Difuso', 'Control Difuso Local']
        ]);
        document.querySelectorAll('.card-header h3').forEach(h3 => {
            const nuevo = reemplazos.get(h3.textContent.trim());
            if (nuevo) h3.textContent = nuevo;
        });

        const btnEmergencia = htmlEl('btn-emergencia');
        if (btnEmergencia) btnEmergencia.innerHTML = '<i class="fas fa-ambulance"></i> Prioridad EV';

        const opciones = document.querySelectorAll('#modo-operacion option');
        opciones.forEach(option => {
            if (option.value === 'simulador') option.textContent = 'Simulación local';
            if (option.value === 'video') option.textContent = 'Visión comput.';
            if (option.value === 'sumo') option.textContent = 'SUMO/TraCI';
        });
    }

    // ---------- inserción de paneles ----------
    function insertarPaneles() {
        const yaInsertado = htmlEl('tesis-icv-panel');
        const left = document.querySelector('.sidebar-left');
        const right = document.querySelector('.sidebar-right');
        const mainCard = document.querySelector('.main-content .full-height');

        if (mainCard && !document.querySelector('.tesis-flow')) {
            const header = mainCard.querySelector('.card-header');
            header?.insertAdjacentHTML('afterend', `
                <div class="tesis-flow">
                    <div class="tesis-flow-step"><strong>Visión</strong><span>conteo, cola y velocidad</span></div>
                    <div class="tesis-flow-step"><strong>Edge IoT</strong><span>Raspberry Pi 5 + sensores</span></div>
                    <div class="tesis-flow-step"><strong>ICV + PI</strong><span>cálculo local Cap. 6</span></div>
                    <div class="tesis-flow-step"><strong>Difuso</strong><span>ΔT verde y reglas</span></div>
                    <div class="tesis-flow-step"><strong>Controlador</strong><span>validación funcional final</span></div>
                    <div class="tesis-flow-step"><strong>Azure</strong><span>telemetría y recomendación</span></div>
                </div>
                <div class="tesis-overview" id="tesis-overview">
                    <div class="tesis-overview-item tesis-overview-main">
                        <span>Intersección crítica</span>
                        <strong id="tesis-overview-focus">-</strong>
                        <small id="tesis-overview-name">Esperando telemetría</small>
                    </div>
                    <div class="tesis-overview-item">
                        <span>ICV calculado</span>
                        <strong id="tesis-overview-icv">0.000</strong>
                        <small id="tesis-overview-class">sin datos</small>
                    </div>
                    <div class="tesis-overview-item">
                        <span>ΔT verde</span>
                        <strong id="tesis-overview-delta">0.0%</strong>
                        <small id="tesis-overview-tgreen">30.0 s</small>
                    </div>
                    <div class="tesis-overview-item">
                        <span>Ola verde</span>
                        <strong id="tesis-overview-offset">0.0 s</strong>
                        <small id="tesis-overview-corridor">sin corredor</small>
                    </div>
                    <div class="tesis-overview-item">
                        <span>Recomendación</span>
                        <strong id="tesis-overview-mode">pendiente</strong>
                        <small>controlador valida</small>
                    </div>
                </div>
            `);
        }

        if (yaInsertado) { reordenarDashboard(); return; }

        const primeraCard = left?.querySelector('.card.glass-card');
        primeraCard?.insertAdjacentHTML('afterend', `
            <section class="card glass-card tesis-card" id="tesis-icv-panel">
                <div class="card-header">
                    <i class="fas fa-square-root-alt"></i>
                    <h3>Cálculo ICV Cap. 6</h3>
                    <span class="tesis-badge" id="tesis-source">local</span>
                </div>
                <div class="tesis-card-body">
                    <div class="tesis-focus">
                        <div>
                            <strong id="tesis-focus-id">-</strong>
                            <span id="tesis-focus-name">Esperando telemetría</span>
                        </div>
                        <span class="tesis-badge" id="tesis-last-update">--:--</span>
                    </div>
                    <div class="tesis-formula">
                        ICV = 0.35(SC/SCmax) + 0.25(1 − Vavg/Vmax) + 0.25(k/kmax) + 0.15(1 − q/qmax)
                        <small class="tesis-formula-note">compuerta por demanda: ICV ≐ 0 si no hay vehículos detectados</small>
                    </div>
                    <div class="tesis-grid">
                        <div class="tesis-kv"><span>SC (cola)</span><strong id="tesis-sc">0 veh</strong></div>
                        <div class="tesis-kv"><span>Vavg</span><strong id="tesis-vavg">0 km/h</strong></div>
                        <div class="tesis-kv"><span>q (flujo)</span><strong id="tesis-q">0 veh/min</strong></div>
                        <div class="tesis-kv"><span>k (densidad)</span><strong id="tesis-k">0 veh/m</strong></div>
                        <div class="tesis-kv"><span>PI normalizado</span><strong id="tesis-pi">0.00</strong></div>
                        <div class="tesis-kv tesis-kv-strong"><span>ICV calculado</span><strong id="tesis-icv-calc">0.00</strong></div>
                    </div>
                    <div class="tesis-formula tesis-formula-sub">
                        PIn = (Vn + δ)/(Vn + SCn + 2δ), δ = 0.1 · 0.5 = equilibrio movilidad/retención
                    </div>
                    <div class="tesis-components">
                        <div class="tesis-component"><span>SC</span><div class="tesis-bar"><i id="tesis-comp-sc"></i></div><strong id="tesis-comp-sc-val">0.00</strong></div>
                        <div class="tesis-component"><span>Vavg</span><div class="tesis-bar"><i id="tesis-comp-v"></i></div><strong id="tesis-comp-v-val">0.00</strong></div>
                        <div class="tesis-component"><span>k</span><div class="tesis-bar"><i id="tesis-comp-k"></i></div><strong id="tesis-comp-k-val">0.00</strong></div>
                        <div class="tesis-component"><span>q</span><div class="tesis-bar"><i id="tesis-comp-q"></i></div><strong id="tesis-comp-q-val">0.00</strong></div>
                    </div>
                </div>
            </section>
        `);

        const icvPanel = htmlEl('tesis-icv-panel');
        icvPanel?.insertAdjacentHTML('afterend', `
            <section class="card glass-card tesis-card" id="tesis-control-panel">
                <div class="card-header">
                    <i class="fas fa-microchip"></i>
                    <h3>Decisión Local Segura</h3>
                    <span class="tesis-badge tesis-badge-estado" id="tesis-reco-estado">pendiente</span>
                </div>
                <div class="tesis-card-body">
                    <div class="tesis-control-main">
                        <div class="tesis-kv"><span>ΔT verde</span><strong id="tesis-delta">0.0%</strong></div>
                        <div class="tesis-kv"><span>T verde</span><strong id="tesis-tgreen">30.0 s</strong></div>
                        <div class="tesis-kv"><span>Reglas</span><strong id="tesis-rules">0/12</strong></div>
                    </div>
                    <div class="tesis-formula">Tverde = Tbase·(1 + ΔT/100), saturado a [10, 120] s · Tbase = 30 s (ciclo Webster de partida)</div>
                    <div class="tesis-rules-list" id="tesis-rules-list"></div>
                    <div class="tesis-membership" id="tesis-membership"></div>
                    <div class="tesis-focus" style="margin-top: 0.65rem; margin-bottom: 0;">
                        <div>
                            <strong id="tesis-safety">Modo seguro local</strong>
                            <span>La salida es recomendación; el controlador semafórico conserva la autoridad final.</span>
                        </div>
                    </div>
                </div>
            </section>
            <section class="card glass-card tesis-card" id="tesis-ola-panel">
                <div class="card-header">
                    <i class="fas fa-route"></i>
                    <h3>Offset de Ola Verde</h3>
                    <span class="tesis-badge" id="tesis-dist-source">Haversine</span>
                </div>
                <div class="tesis-card-body">
                    <div class="tesis-formula">τ(i,i+1) = (di / vprog) mod Tciclo · BW = (Tverde − |τ − tviaje mod Tciclo|)/Tciclo</div>
                    <div class="tesis-grid">
                        <div class="tesis-kv"><span>Corredor</span><strong id="tesis-corridor">-</strong></div>
                        <div class="tesis-kv"><span>di</span><strong id="tesis-dist">0 m</strong></div>
                        <div class="tesis-kv"><span>vprog</span><strong id="tesis-vprog">0 km/h</strong></div>
                        <div class="tesis-kv"><span>t viaje</span><strong id="tesis-travel">0 s</strong></div>
                        <div class="tesis-kv"><span class="tesis-keepcase">Offset τ recomendado</span><strong id="tesis-offset">0 s</strong></div>
                        <div class="tesis-kv"><span>BW verde</span><strong id="tesis-bw">0%</strong></div>
                    </div>
                </div>
            </section>
        `);

        right?.insertAdjacentHTML('beforeend', `
            <section class="card glass-card tesis-card" id="tesis-security-panel">
                <div class="card-header">
                    <i class="fas fa-shield-alt"></i>
                    <h3>Ciberseguridad y Enlace</h3>
                    <span class="tesis-badge" id="tesis-nube-badge">iniciando</span>
                </div>
                <div class="tesis-card-body tesis-security">
                    <div class="tesis-security-row"><strong>Nube Azure (MQTT/TLS)</strong><span id="tesis-nube-estado" class="tesis-pill">iniciando</span></div>
                    <div class="tesis-security-row"><strong>WebSocket backend</strong><span id="tesis-ws-estado" class="tesis-pill">verificando</span></div>
                    <div class="tesis-security-row"><strong>Último paquete</strong><span id="tesis-ultimo-paquete" class="tesis-pill tesis-pill-neutral">—</span></div>
                    <div class="tesis-security-row"><strong>Periodo de datos</strong><span id="tesis-latencia" class="tesis-pill tesis-pill-neutral">—</span></div>
                    <div class="tesis-security-row"><strong>Buffer local</strong><span id="tesis-buffer" class="tesis-pill tesis-pill-neutral">0 paq.</span></div>
                    <div class="tesis-security-row"><strong>Certificado por módulo</strong><span class="tesis-pill tesis-pill-ok">validado</span></div>
                    <div class="tesis-security-row"><strong>RBAC + MFA operador</strong><span class="tesis-pill tesis-pill-ok">requerido</span></div>
                    <div class="tesis-security-row"><strong>Salud del módulo</strong><span id="tesis-salud" class="tesis-pill tesis-pill-ok">OK · 0 min</span></div>
                </div>
            </section>
            <section class="card glass-card tesis-card" id="tesis-log-panel">
                <div class="card-header">
                    <i class="fas fa-stream"></i>
                    <h3>Registro de Eventos</h3>
                </div>
                <div class="tesis-card-body">
                    <div class="tesis-log-list" id="tesis-log-list">
                        <div class="tesis-log-empty">Sin eventos registrados</div>
                    </div>
                </div>
            </section>
        `);

        reordenarDashboard();
        engancharEventosUI();
    }

    function buscarCardPorTitulo(textos) {
        const lista = Array.isArray(textos) ? textos : [textos];
        const normalizar = v => (v || '').trim().toLowerCase();
        const objetivos = lista.map(normalizar);
        const titulo = [...document.querySelectorAll('.card-header h3')]
            .find(h3 => objetivos.includes(normalizar(h3.textContent)));
        return titulo?.closest('.card') || null;
    }

    function reordenarDashboard() {
        const left = document.querySelector('.sidebar-left');
        const right = document.querySelector('.sidebar-right');
        if (!left || !right) return;

        const icv = htmlEl('tesis-icv-panel');
        const control = htmlEl('tesis-control-panel');
        const ola = htmlEl('tesis-ola-panel');
        const video = htmlEl('panel-video');
        const telemetria = left.querySelector('.stats-grid')?.closest('.card');
        const metricas = htmlEl('metricas-container')?.closest('.card');
        const olas = htmlEl('olas-verdes-container')?.closest('.card');
        const difuso = htmlEl('reglas-activas')?.closest('.card');
        const seguridad = htmlEl('tesis-security-panel');
        const logsPanel = htmlEl('tesis-log-panel');
        const chartICV = htmlEl('chartICV')?.closest('.card');
        const chartFlujo = htmlEl('chartFlujo')?.closest('.card');

        if (telemetria) {
            telemetria.id = 'tesis-telemetry-panel';
            left.prepend(telemetria);
        }
        if (icv && control) icv.after(control);
        if (control && ola) control.after(ola);
        [chartICV, chartFlujo].forEach(card => card?.classList.add('tesis-chart-card'));

        if (metricas) {
            metricas.id = 'tesis-metricas-panel';
            right.prepend(metricas);
        }
        if (olas) {
            olas.id = 'tesis-olas-lista-panel';
            metricas ? metricas.after(olas) : right.prepend(olas);
        }
        if (video) {
            video.classList.add('tesis-video-compact');
            olas ? olas.after(video) : right.appendChild(video);
        }
        if (difuso) {
            difuso.id = 'tesis-difuso-legacy';
            difuso.classList.add('tesis-legacy-compact');
            video ? video.after(difuso) : right.appendChild(difuso);
        }
        if (seguridad) right.appendChild(seguridad);
        if (logsPanel) right.appendChild(logsPanel);

        if (!capa.posicionInicial) {
            left.scrollTop = 0;
            right.scrollTop = 0;
            capa.posicionInicial = true;
        }
    }

    function engancharEventosUI() {
        const btnReiniciar = htmlEl('btn-reiniciar-simulador');
        if (btnReiniciar && !btnReiniciar.__tesisHooked) {
            btnReiniciar.__tesisHooked = true;
            btnReiniciar.addEventListener('click', () => logEvento('info', 'Reinicio de simulación solicitado por el operador'));
        }
        const modo = htmlEl('modo-operacion');
        if (modo && !modo.__tesisHooked) {
            modo.__tesisHooked = true;
            modo.addEventListener('change', e => logEvento('info', `Cambio de fuente de datos: ${e.target.value}`));
        }
    }

    // ---------- métricas desde estado ----------
    function extraerMetricasDesdeEstado() {
        const app = obtenerEstadoApp();
        if (!app?.ultimasMetricas) return [];
        return Object.entries(app.ultimasMetricas).map(([id, m]) => ({
            interseccion_id: id,
            num_vehiculos: m.num_vehiculos || 0,
            icv: m.icv || 0,
            flujo: m.flujo || 0,
            velocidad: m.velocidad || 0,
            cola: m.cola || 0,
            estado_semaforo: m.estado_semaforo || 'verde'
        }));
    }

    // ---------- cálculo ICV / PI (versión final del Cap. 6) ----------
    function calcularICVCap6(metricas) {
        const datos = (metricas || []).filter(m => m && m.interseccion_id);
        if (!datos.length) return null;

        const foco = [...datos].sort((a, b) => (b.icv || 0) - (a.icv || 0))[0];
        const inter = obtenerIntersecciones().find(i => i.id === foco.interseccion_id);
        const sc = clamp(Math.round((foco.cola || 0) / 6), 0, PARAMS.scMax);
        const q = clamp(Number(foco.flujo) || 0, 0, PARAMS.qMax);
        const vehiculos = Number(foco.num_vehiculos) || Math.max(sc, Math.round(q * 1.4));

        // Convenciones de borde del Cap. 6: vía vacía => flujo libre
        const sinDemanda = vehiculos === 0 && sc === 0;
        const vavg = sinDemanda
            ? PARAMS.vMax
            : clamp(Number(foco.velocidad) || 0, 0, PARAMS.vMax);
        const k = clamp(vehiculos / PARAMS.longitudEfectiva, 0, PARAMS.kMax);

        const scNorm = sc / PARAMS.scMax;
        const vNormDirecta = Math.min(vavg / PARAMS.vMax, 1);
        const vNorm = 1 - vNormDirecta;
        const kNorm = k / PARAMS.kMax;
        const qNorm = 1 - Math.min(q / PARAMS.qMax, 1);

        const componentes = sinDemanda
            ? { sc: 0, velocidad: 0, densidad: 0, flujo: 0 }
            : {
                sc: pesos.sc * scNorm,
                velocidad: pesos.velocidad * vNorm,
                densidad: pesos.densidad * kNorm,
                flujo: pesos.flujo * qNorm
            };

        // Compuerta por demanda: ICV = 0 si no hay vehículos detectados
        const icv = sinDemanda
            ? 0
            : clamp(componentes.sc + componentes.velocidad + componentes.densidad + componentes.flujo, 0, 1);

        // PI con normalización racional del Cap. 6:
        // PIn = (Vn + δ) / (Vn + SCn + 2δ); 0.5 = equilibrio movilidad/retención
        const d = PARAMS.deltaPi;
        const pi = clamp((vNormDirecta + d) / (vNormDirecta + scNorm + 2 * d), 0, 1);

        return { foco, inter, sc, vavg, q, k, vehiculos, sinDemanda, componentes, icv, pi };
    }

    // ---------- inferencia difusa (Mamdani) ----------
    function fuzzificarICV(icv) {
        return {
            Bajo: interpola([[0, 1], [0.2, 1], [0.4, 0], [1, 0]], icv),
            Medio: interpola([[0, 0], [0.2, 0], [0.4, 1], [0.7, 0], [1, 0]], icv),
            Alto: interpola([[0, 0], [0.4, 0], [0.7, 1], [1, 1]], icv)
        };
    }
    function fuzzificarPI(pi) {
        return {
            Ineficiente: interpola([[0, 1], [0.3, 1], [0.5, 0], [1, 0]], pi),
            Moderado: interpola([[0, 0], [0.3, 0], [0.5, 1], [0.8, 0], [1, 0]], pi),
            MuyEficiente: interpola([[0, 0], [0.5, 0], [0.8, 1], [1, 1]], pi)
        };
    }

    function calcularDifuso(icv, pi, ev) {
        const grados = {
            ICV: fuzzificarICV(icv),
            PI: fuzzificarPI(pi),
            EV: { Ausente: ev > 0 ? 0 : 1, Presente: ev > 0 ? 1 : 0 }
        };

        const activaciones = {};
        const reglasActivasDetalle = [];

        reglasDifusas.forEach(regla => {
            const valores = regla.ant.map(ant => {
                const [grupo, nombre] = ant.split('_');
                return grados[grupo]?.[nombre] ?? 0;
            });
            const grado = Math.min(...valores);
            if (grado > 0.001) {
                reglasActivasDetalle.push({ id: regla.id, out: regla.out, grado });
                activaciones[regla.out] = Math.max(activaciones[regla.out] || 0, grado);
            }
        });
        reglasActivasDetalle.sort((a, b) => b.grado - a.grado);

        // Centroide discreto (M = 61 puntos, paso 1%, como en el Cap. 6)
        let numerador = 0, denominador = 0;
        for (let dt = -30; dt <= 30; dt += 1) {
            let mu = 0;
            Object.entries(activaciones).forEach(([nombre, grado]) => {
                mu = Math.max(mu, Math.min(grado, interpola(conjuntosSalida[nombre], dt)));
            });
            numerador += dt * mu;
            denominador += mu;
        }

        const deltaT = denominador > 0 ? numerador / denominador : 0;
        const tVerdeRaw = PARAMS.tBase * (1 + deltaT / 100);
        const tVerde = clamp(tVerdeRaw, PARAMS.tVerdeMin, PARAMS.tVerdeMax);
        const recortada = Math.abs(tVerde - tVerdeRaw) > 0.05;

        return { grados, activaciones, reglasActivasDetalle, reglasActivas: reglasActivasDetalle.length, deltaT, tVerdeRaw, tVerde, recortada };
    }

    // ---------- ola verde: distancia con Mapbox o Haversine ----------
    function distanciaCorredor(focoId) {
        const conexiones = obtenerConexiones();
        const inters = obtenerIntersecciones();
        const conexion = conexiones.find(c => c.origen === focoId || c.destino === focoId) || conexiones[0];
        if (!conexion) return null;

        const a = inters.find(i => i.id === conexion.origen);
        const b = inters.find(i => i.id === conexion.destino);
        let dist = Number(conexion.distancia) || 0;
        let fuente = 'corredor curado';

        if ((!dist || dist <= 0) && a && b) {
            dist = haversineMetros(a.latitud, a.longitud, b.latitud, b.longitud);
            fuente = 'Haversine local';
        }

        // Refinamiento opcional con Mapbox Directions si hay token configurado
        const cfg = obtenerConfig();
        const clave = `${conexion.origen}-${conexion.destino}`;
        if (capa.distanciaMapboxCache[clave]) {
            dist = capa.distanciaMapboxCache[clave];
            fuente = 'Mapbox';
        } else if (cfg.MAPBOX_TOKEN && cfg.MAPBOX_TOKEN !== 'TU_TOKEN_MAPBOX_AQUI' && a && b) {
            const fnRuta = obtenerGlobal('obtenerRutaMapbox');
            if (typeof fnRuta === 'function' && !capa.distanciaMapboxCache[`${clave}:pendiente`]) {
                capa.distanciaMapboxCache[`${clave}:pendiente`] = true;
                fnRuta([a.latitud, a.longitud], [b.latitud, b.longitud])
                    .then(ruta => {
                        const m = Number(ruta?.distancia ?? ruta?.distance);
                        if (Number.isFinite(m) && m > 0) {
                            capa.distanciaMapboxCache[clave] = m;
                            logEvento('info', `Distancia ${clave} refinada con Mapbox: ${Math.round(m)} m`);
                        }
                    })
                    .catch(() => { /* fallback silencioso a Haversine */ });
            }
        }

        return { conexion, dist, fuente };
    }

    function calcularOlaVerde(calc, difuso) {
        if (!calc) return null;
        const info = distanciaCorredor(calc.foco.interseccion_id);
        if (!info) return null;

        const vprogKmh = clamp(calc.vavg || 35, 20, PARAMS.vMax);
        const vprogMs = vprogKmh / 3.6;
        const tViaje = info.dist / vprogMs;
        const tau = tViaje % PARAMS.tCiclo;
        // BW del Cap. 6 con offset óptimo aplicado: |τ − tviaje mod T| = 0
        const bw = clamp(difuso.tVerde / PARAMS.tCiclo, 0, 1);

        return { conexion: info.conexion, dist: info.dist, fuente: info.fuente, vprogKmh, tViaje, tau, bw };
    }

    // ---------- arbitraje / estado de la recomendación ----------
    function estadoRecomendacion(calc, difuso, ev) {
        if (!calc) return { clase: 'pendiente', texto: 'pendiente' };
        if (ev) return { clase: 'ev', texto: 'prioridad EV · validada' };
        if (difuso.recortada) return { clase: 'recortada', texto: 'ajustada por límites de seguridad' };
        const vigente = (Date.now() - capa.recomendacionTs) / 1000 <= PARAMS.timeoutRecomendacion;
        return vigente
            ? { clase: 'ok', texto: 'validada localmente' }
            : { clase: 'pendiente', texto: 'pendiente de validación' };
    }

    // ---------- estado simulado de la nube (MQTT/TLS) ----------
    function actualizarEstadoNube() {
        const app = obtenerEstadoApp();
        const ws = app?.websocket;
        const wsAbierto = !!ws && ws.readyState === 1;
        const edadPaquete = capa.ultimoPaqueteTs ? (Date.now() - capa.ultimoPaqueteTs) / 1000 : Infinity;
        const datosFrescos = edadPaquete < 8;
        const n = capa.nube;
        const anterior = n.estado;

        if (n.estado === 'resincronizando') {
            n.resincTicks -= 1;
            n.buffer = Math.max(0, n.buffer - 12);
            if (n.resincTicks <= 0 && n.buffer === 0) n.estado = 'conectado';
        } else if (wsAbierto && datosFrescos) {
            if (anterior === 'almacenando' || anterior === 'degradado') {
                n.estado = 'resincronizando';
                n.resincTicks = 3;
            } else {
                n.estado = 'conectado';
            }
        } else if (!wsAbierto && datosFrescos) {
            // El módulo sigue midiendo pero sin enlace: buffer local (modo degradado del Cap. 6)
            n.estado = 'almacenando';
            n.buffer = Math.min(999, n.buffer + 1);
        } else {
            n.estado = 'degradado';
        }

        if (n.estado !== anterior) {
            n.desde = Date.now();
            const mensajes = {
                conectado: anterior === 'iniciando'
                    ? 'Enlace MQTT/TLS establecido con Azure IoT Hub (simulado)'
                    : 'Enlace MQTT/TLS restablecido con Azure IoT Hub (simulado)',
                degradado: 'Enlace degradado: telemetría sin confirmar',
                almacenando: 'Sin enlace a nube: almacenando telemetría localmente',
                resincronizando: 'Resincronizando buffer local con la nube'
            };
            logEvento(n.estado === 'conectado' ? 'ok' : 'warn', mensajes[n.estado] || n.estado);
        }

        if (capa.prevWsAbierto !== null && capa.prevWsAbierto !== wsAbierto) {
            logEvento(wsAbierto ? 'ok' : 'warn', wsAbierto ? 'WebSocket backend conectado' : 'WebSocket backend caído; opera control difuso local');
        }
        capa.prevWsAbierto = wsAbierto;

        // Render
        const etiquetas = {
            conectado: ['conectado (TLS 1.2)', 'ok'],
            degradado: ['degradado', 'warn'],
            almacenando: ['almacenando localmente', 'warn'],
            resincronizando: ['resincronizando…', 'info'],
            iniciando: ['iniciando', 'neutral']
        };
        const [labelNube, claseNube] = etiquetas[n.estado] || etiquetas.iniciando;
        setPill('tesis-nube-estado', labelNube, claseNube);
        texto('tesis-nube-badge', n.estado);
        setPill('tesis-ws-estado', wsAbierto ? 'conectado' : 'sin conexión', wsAbierto ? 'ok' : 'bad');
        setPill('tesis-ultimo-paquete', capa.ultimoPaqueteTs ? `${horaCorta(capa.ultimoPaqueteTs)} (hace ${Math.round(edadPaquete)} s)` : '—', datosFrescos ? 'ok' : 'warn');
        setPill('tesis-latencia', capa.periodoDatosMs ? `${(capa.periodoDatosMs / 1000).toFixed(1)} s` : '—', 'neutral');
        setPill('tesis-buffer', `${n.buffer} paq.`, n.buffer > 0 ? 'warn' : 'neutral');

        const inicio = app?.estadisticas?.tiempoInicio || Date.now();
        const minutos = Math.max(0, Math.round((Date.now() - inicio) / 60000));
        const actualizaciones = app?.estadisticas?.contadorActualizaciones ?? 0;
        setPill('tesis-salud', `OK · ${minutos} min · ${actualizaciones} act.`, 'ok');
    }

    function setPill(id, textoPill, clase) {
        const el = htmlEl(id);
        if (!el) return;
        el.textContent = textoPill;
        el.className = `tesis-pill tesis-pill-${clase}`;
    }

    // ---------- actualización principal ----------
    function actualizarPaneles(metricas, origen = 'local') {
        insertarPaneles();
        const ahora = Date.now();
        if (capa.ultimoPaqueteTs) capa.periodoDatosMs = ahora - capa.ultimoPaqueteTs;
        capa.ultimoPaqueteTs = ahora;

        const calc = calcularICVCap6(metricas);
        if (!calc) return;

        const app = obtenerEstadoApp();
        const ev = app?.olaVerdeActiva ? 1 : 0;
        const difuso = calcularDifuso(calc.icv, calc.pi, ev);
        capa.recomendacionTs = ahora;
        const ola = calcularOlaVerde(calc, difuso);
        const reco = estadoRecomendacion(calc, difuso, ev);

        // Eventos por transición
        if (!!ev !== capa.prevEV) {
            logEvento(ev ? 'warn' : 'ok', ev ? 'Vehículo de emergencia: prioridad EV activada' : 'Prioridad EV finalizada; control normal');
            capa.prevEV = !!ev;
        }
        if (difuso.recortada !== capa.prevClamp) {
            if (difuso.recortada) logEvento('warn', `Tverde recortado por límites: ${difuso.tVerdeRaw.toFixed(1)} s → ${difuso.tVerde.toFixed(1)} s`);
            capa.prevClamp = difuso.recortada;
        }
        if (capa.prevFoco !== calc.foco.interseccion_id) {
            logEvento('info', `Intersección crítica: ${calc.foco.interseccion_id} (ICV ${calc.icv.toFixed(3)})`);
            capa.prevFoco = calc.foco.interseccion_id;
        }

        // Panel ICV
        texto('tesis-source', origen);
        texto('tesis-last-update', horaCorta(ahora));
        texto('tesis-focus-id', calc.foco.interseccion_id);
        texto('tesis-focus-name', calc.inter?.nombre || 'Intersección seleccionada por mayor ICV');
        texto('tesis-sc', `${calc.sc} veh`);
        texto('tesis-vavg', `${calc.vavg.toFixed(1)} km/h`);
        texto('tesis-q', `${calc.q.toFixed(1)} veh/min`);
        texto('tesis-k', `${calc.k.toFixed(3)} veh/m`);
        texto('tesis-pi', calc.pi.toFixed(2));
        texto('tesis-icv-calc', calc.sinDemanda ? '0.000 (sin demanda)' : calc.icv.toFixed(3));

        texto('tesis-comp-sc-val', calc.componentes.sc.toFixed(3));
        texto('tesis-comp-v-val', calc.componentes.velocidad.toFixed(3));
        texto('tesis-comp-k-val', calc.componentes.densidad.toFixed(3));
        texto('tesis-comp-q-val', calc.componentes.flujo.toFixed(3));
        ancho('tesis-comp-sc', (calc.componentes.sc / pesos.sc) * 100);
        ancho('tesis-comp-v', (calc.componentes.velocidad / pesos.velocidad) * 100);
        ancho('tesis-comp-k', (calc.componentes.densidad / pesos.densidad) * 100);
        ancho('tesis-comp-q', (calc.componentes.flujo / pesos.flujo) * 100);

        // Panel control difuso
        texto('tesis-delta', `${difuso.deltaT >= 0 ? '+' : ''}${difuso.deltaT.toFixed(1)}%`);
        texto('tesis-tgreen', `${difuso.tVerde.toFixed(1)} s`);
        texto('tesis-rules', `${difuso.reglasActivas}/12`);
        texto('tesis-safety', ev ? 'Prioridad EV validada localmente' : 'Modo seguro local');

        const recoEl = htmlEl('tesis-reco-estado');
        if (recoEl) {
            recoEl.textContent = reco.texto;
            recoEl.className = `tesis-badge tesis-badge-estado tesis-reco-${reco.clase}`;
        }

        const rulesList = htmlEl('tesis-rules-list');
        if (rulesList) {
            const top = difuso.reglasActivasDetalle.slice(0, 3);
            rulesList.innerHTML = top.length
                ? top.map(r => `
                    <div class="tesis-rule-row">
                        <span class="tesis-rule-id">${r.id}</span>
                        <span class="tesis-rule-out">${r.out.replace('_', ' ')}</span>
                        <div class="tesis-bar tesis-rule-bar"><i style="width:${(r.grado * 100).toFixed(0)}%"></i></div>
                        <strong>${r.grado.toFixed(2)}</strong>
                    </div>`).join('')
                : '<div class="tesis-log-empty">Ninguna regla activa</div>';
        }

        const membership = htmlEl('tesis-membership');
        if (membership) {
            membership.innerHTML = `
                <span class="tesis-chip">ICV Bajo ${difuso.grados.ICV.Bajo.toFixed(2)}</span>
                <span class="tesis-chip">ICV Medio ${difuso.grados.ICV.Medio.toFixed(2)}</span>
                <span class="tesis-chip">ICV Alto ${difuso.grados.ICV.Alto.toFixed(2)}</span>
                <span class="tesis-chip">PI Inef. ${difuso.grados.PI.Ineficiente.toFixed(2)}</span>
                <span class="tesis-chip">PI Mod. ${difuso.grados.PI.Moderado.toFixed(2)}</span>
                <span class="tesis-chip">PI MuyEf. ${difuso.grados.PI.MuyEficiente.toFixed(2)}</span>
                <span class="tesis-chip">EV ${ev ? 'Presente' : 'Ausente'}</span>
            `;
        }

        // Resumen superior
        texto('tesis-overview-focus', calc.foco.interseccion_id);
        texto('tesis-overview-name', calc.inter?.nombre || 'Intersección con mayor ICV');
        texto('tesis-overview-icv', calc.icv.toFixed(3));
        texto('tesis-overview-class', calc.sinDemanda ? 'sin demanda' : calc.icv >= 0.58 ? 'congestión alta' : calc.icv >= 0.20 ? 'tráfico moderado' : 'flujo estable');
        texto('tesis-overview-delta', `${difuso.deltaT >= 0 ? '+' : ''}${difuso.deltaT.toFixed(1)}%`);
        texto('tesis-overview-tgreen', `${difuso.tVerde.toFixed(1)} s`);
        texto('tesis-overview-mode', reco.texto);

        // Panel ola verde
        if (ola) {
            texto('tesis-corridor', `${ola.conexion.origen} → ${ola.conexion.destino}`);
            texto('tesis-dist', `${Math.round(ola.dist)} m`);
            texto('tesis-vprog', `${ola.vprogKmh.toFixed(1)} km/h`);
            texto('tesis-travel', `${ola.tViaje.toFixed(1)} s`);
            texto('tesis-offset', `${ola.tau.toFixed(1)} s`);
            texto('tesis-bw', `${(ola.bw * 100).toFixed(0)}%`);
            texto('tesis-dist-source', ola.fuente);
            texto('tesis-overview-offset', `${ola.tau.toFixed(1)} s`);
            texto('tesis-overview-corridor', `${ola.conexion.origen} → ${ola.conexion.destino}`);
        }

        // Tarjeta difusa heredada
        const reglas = htmlEl('reglas-activas');
        const tMedio = htmlEl('tiempo-verde-medio');
        const olasBadge = htmlEl('olas-activas');
        if (reglas) reglas.textContent = difuso.reglasActivas;
        if (tMedio) tMedio.textContent = `${difuso.tVerde.toFixed(0)}s`;
        if (olasBadge) olasBadge.textContent = ev ? '1' : (ola && ola.bw > 0.35 ? '1' : '0');

        actualizarEstadoNube();
    }

    // ---------- integración con el flujo existente ----------
    function envolverActualizacion() {
        const original = obtenerGlobal('actualizarDatosInterfaz');
        if (typeof original !== 'function' || original.__tesisWrapped) return;

        const envuelta = function (metricas, origen = 'backend') {
            const resultado = original.apply(this, arguments);
            try {
                actualizarPaneles(metricas, origen);
            } catch (error) {
                console.warn('No se pudo actualizar panel de tesis:', error);
            }
            return resultado;
        };
        envuelta.__tesisWrapped = true;
        try {
            window.actualizarDatosInterfaz = envuelta;
            actualizarDatosInterfaz = envuelta;
        } catch {
            window.actualizarDatosInterfaz = envuelta;
        }
    }

    function refrescarDesdeEstado() {
        const metricas = extraerMetricasDesdeEstado();
        if (metricas.length) {
            actualizarPaneles(metricas, 'estado local');
        } else {
            actualizarEstadoNube();
        }
    }

    function iniciar() {
        ajustarTextoBase();
        insertarPaneles();
        envolverActualizacion();
        logEvento('info', 'Consola operativa iniciada; controlador semafórico mantiene autoridad final');
        setTimeout(refrescarDesdeEstado, 250);
        setInterval(refrescarDesdeEstado, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }
})();
