/*
 * Trazabilidad y Seguridad funcional (capa de cliente, Fase C)
 * ============================================================
 * - Panel de trazabilidad: muestra la cadena Entrada → ICV → reglas difusas
 *   disparadas → ΔT → verde final (con corrección de seguridad).
 * - Panel de seguridad: demuestra la autoridad de seguridad funcional.
 * - Banner de fuente de datos: etiqueta explícitamente si los datos son reales
 *   (SUMO/visión) o sintéticos (simulador) — nunca datos falsos sin avisar.
 */
(function () {
    'use strict';

    function escaparHtml(valor) {
        return String(valor == null ? '' : valor).replace(/[&<>"']/g, function (caracter) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[caracter];
        });
    }

    function colorSeguro(valor) {
        return /^#[0-9a-f]{3,8}$/i.test(String(valor || '')) ? valor : '#2563eb';
    }

    // ---------- Trazabilidad ----------
    function abrirTrazabilidad() {
        var m = document.getElementById('traza-modal');
        if (m) { m.style.display = 'flex'; recalcularTraza(); }
    }
    function cerrarTrazabilidad() {
        var m = document.getElementById('traza-modal');
        if (m) m.style.display = 'none';
    }

    async function recalcularTraza() {
        var id = (document.getElementById('traza-id').value || 'INT-001').trim();
        var cola = document.getElementById('traza-cola').value;
        var vel = document.getElementById('traza-vel').value;
        var flujo = document.getElementById('traza-flujo').value;
        var ev = document.getElementById('traza-ev').checked ? 1 : 0;
        var cont = document.getElementById('traza-result');
        cont.innerHTML = 'Calculando…';
        var q = new URLSearchParams({
            cola: cola,
            velocidad: vel,
            flujo: flujo,
            ev: String(ev)
        }).toString();
        try {
            var r = await fetch('/api/interseccion/' + encodeURIComponent(id) + '/explicacion?' + q);
            if (!r.ok) { cont.innerHTML = '<p style="color:#dc2626">No autorizado o error (' + r.status + ')</p>'; return; }
            cont.innerHTML = renderTraza(await r.json());
        } catch (e) {
            cont.innerHTML = '<p style="color:#dc2626">Error de conexión</p>';
        }
    }

    function renderTraza(d) {
        d = d || {};
        var entrada = d.entrada || {};
        var icv = d.icv || {};
        var limites = d.limites || {};
        var reglas = (d.reglas_disparadas || []).filter(Boolean).map(function (x) {
            return '<li><b>P' + escaparHtml(x.prioridad) + '</b> ' + escaparHtml(x.descripcion) +
                ' → <b>' + escaparHtml(x.consecuente) + '</b> <span style="color:#64748b">(α=' +
                Number(x.grado).toFixed(2) + ')</span></li>';
        }).join('') || '<li>(ninguna regla activa → mantener)</li>';

        var seg = d.seguridad || {};
        var corr = (seg.correcciones || []).filter(Boolean).map(function (c) {
            return escaparHtml(c.campo) + ': ' + escaparHtml(c.solicitado) + '→' +
                escaparHtml(c.aplicado) + ' (' + escaparHtml(c.motivo) + ')';
        }).join('<br>') || 'sin correcciones';
        var nivelColor = colorSeguro(icv.color);
        var emer = entrada.emergencia ? ' · 🚑 EMERGENCIA' : '';
        var modoSeguro = seg.modo_seguro ? '<span class="traza-seguro">⚠ MODO SEGURO</span>' : '';

        return '' +
            '<div class="traza-chain">' +
            '  <div class="traza-step"><span class="traza-tag">1 · Entrada de tráfico</span>' +
            'Cola ' + escaparHtml(entrada.cola_m) + ' m · Vel ' + escaparHtml(entrada.velocidad_kmh) +
            ' km/h · Flujo ' + escaparHtml(entrada.flujo_veh_min) + ' · SC≈' +
            escaparHtml(entrada.stopped_count_aprox) + emer +
            '<div class="traza-fuente">fuente: ' + escaparHtml(d.fuente_datos) + '</div></div>' +
            '  <div class="traza-arrow">▼</div>' +
            '  <div class="traza-step"><span class="traza-tag">2 · ICV (Cap 6.2.3) y PI</span>' +
            '<b style="color:' + nivelColor + '">ICV = ' + escaparHtml(icv.valor) + '</b> — nivel <b>' +
            escaparHtml(icv.nivel) + '</b> · PI = ' + escaparHtml(d.pi) + '</div>' +
            '  <div class="traza-arrow">▼</div>' +
            '  <div class="traza-step"><span class="traza-tag">3 · Reglas difusas disparadas (Mamdani)</span>' +
            '<ul class="traza-reglas">' + reglas + '</ul></div>' +
            '  <div class="traza-arrow">▼</div>' +
            '  <div class="traza-step"><span class="traza-tag">4 · Ajuste difuso</span>' +
            'ΔT verde = <b>' + escaparHtml(d.delta_t_porcentaje) + '%</b> · base ' +
            escaparHtml(d.verde_base_s) + 's → bruto ' + escaparHtml(d.verde_bruto_s) + 's</div>' +
            '  <div class="traza-arrow">▼</div>' +
            '  <div class="traza-step traza-final"><span class="traza-tag">5 · Verde final (tras seguridad funcional)</span>' +
            '<b style="font-size:18px">' + escaparHtml(d.verde_final_s) + ' s</b>' + modoSeguro +
            '<div class="traza-fuente">seguridad: ' + corr + ' · límites ' +
            escaparHtml(limites.t_verde_min) + '–' + escaparHtml(limites.t_verde_max) + 's</div></div>' +
            '</div>';
    }

    // ---------- Seguridad funcional ----------
    async function abrirSeguridadDemo() {
        var m = document.getElementById('seg-modal');
        if (m) m.style.display = 'flex';
        var cont = document.getElementById('seg-result');
        cont.innerHTML = 'Ejecutando pruebas de seguridad…';
        try {
            var r = await fetch('/api/seguridad/demo');
            if (!r.ok) { cont.innerHTML = '<p style="color:#dc2626">No autorizado (' + r.status + ')</p>'; return; }
            var d = await r.json();
            cont.innerHTML = '<p style="color:#475569;font-size:13px;margin-top:0">' +
                escaparHtml(d.descripcion || '') + '</p>' +
                (d.casos || []).map(function (c) {
                    var ic = c.seguro ? '✅' : '⛔';
                    return '<div class="seg-caso"><span class="seg-ic">' + ic + '</span>' +
                        '<div><b>' + escaparHtml(c.caso) + '</b><br><span style="color:#475569">' +
                        escaparHtml(c.resultado) + '</span></div></div>';
                }).join('');
        } catch (e) {
            cont.innerHTML = '<p style="color:#dc2626">Error de conexión</p>';
        }
    }
    function cerrarSeguridad() {
        var m = document.getElementById('seg-modal');
        if (m) m.style.display = 'none';
    }

    // ---------- Banner de fuente de datos ----------
    async function actualizarBanner() {
        var el = document.getElementById('data-source-banner');
        if (!el) return;
        // Solo tiene sentido si hay sesión iniciada
        if (!localStorage.getItem('cs_token')) { el.style.display = 'none'; return; }
        el.style.display = 'block';
        try {
            var r = await fetch('/api/estado');
            if (!r.ok) { el.textContent = '🔴 Sin acceso a datos'; el.className = 'ds-off'; return; }
            var d = await r.json();
            var modo = d.modo;
            if (modo === 'sumo') {
                el.textContent = '🟢 SUMO en vivo — tráfico real (TraCI)';
                el.className = 'ds-real';
            } else if (modo === 'video') {
                el.textContent = '🟢 Visión por computadora — video real';
                el.className = 'ds-real';
            } else {
                el.textContent = '🟡 Simulador determinístico — NO es tráfico real';
                el.className = 'ds-sim';
            }
        } catch (e) {
            el.textContent = '🔴 Sin conexión con el backend';
            el.className = 'ds-off';
        }
    }

    // Exponer al HTML
    window.abrirTrazabilidad = abrirTrazabilidad;
    window.cerrarTrazabilidad = cerrarTrazabilidad;
    window.recalcularTraza = recalcularTraza;
    window.abrirSeguridadDemo = abrirSeguridadDemo;
    window.cerrarSeguridad = cerrarSeguridad;

    function init() {
        actualizarBanner();
        setInterval(actualizarBanner, 4000);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
