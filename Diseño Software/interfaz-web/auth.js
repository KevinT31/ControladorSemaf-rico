/*
 * Ciberseguridad del dashboard (capa de cliente)
 * ==============================================
 * - Envuelve window.fetch para adjuntar el token JWT a TODA llamada /api/*.
 * - Controla el overlay de login (gate de acceso).
 * - Aplica la UI según el rol (operador = solo lectura).
 * - Muestra la bitácora de auditoría (tecnico/admin).
 *
 * Se carga ANTES que app_mejorado.js para que la intercepción de fetch esté
 * activa desde la primera petición.
 */
(function () {
    'use strict';

    var TOKEN_KEY = 'cs_token';
    var USER_KEY = 'cs_user';

    // Los eventos de auditoría contienen datos procedentes de solicitudes de
    // red. Escapar todos sus campos antes de construir las filas HTML.
    function escaparHtml(valor) {
        return String(valor == null ? '' : valor)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ---- 1) Interceptar fetch: adjuntar Authorization a /api/* ----
    var fetchOriginal = window.fetch.bind(window);
    window.fetch = function (input, init) {
        init = init || {};
        try {
            var url = (typeof input === 'string') ? input : (input && input.url) || '';
            var token = localStorage.getItem(TOKEN_KEY);
            if (token && url.indexOf('/api/') !== -1 && url.indexOf('/api/auth/login') === -1) {
                var headers = new Headers(init.headers || (typeof input !== 'string' && input.headers) || {});
                if (!headers.has('Authorization')) {
                    headers.set('Authorization', 'Bearer ' + token);
                }
                init.headers = headers;
            }
        } catch (e) { /* no bloquear la petición por un error del wrapper */ }
        return fetchOriginal(input, init);
    };

    // ---- 2) Login ----
    async function hacerLogin() {
        var u = (document.getElementById('auth-user').value || '').trim();
        var p = document.getElementById('auth-pass').value || '';
        var err = document.getElementById('auth-error');
        err.textContent = '';
        if (!u || !p) { err.textContent = 'Ingrese usuario y contraseña'; return; }
        try {
            var r = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            if (!r.ok) { err.textContent = 'Usuario o contraseña incorrectos'; return; }
            var data = await r.json();
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.usuario || {}));
            location.reload(); // recargar para iniciar todo ya autenticado
        } catch (e) {
            err.textContent = 'No se pudo conectar con el servidor';
        }
    }

    function cerrarSesion() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        location.reload();
    }

    // ---- 3) UI según rol ----
    function aplicarUIporRol(usuario) {
        var rol = (usuario && usuario.rol) || 'operador';
        document.body.classList.remove('rol-operador', 'rol-tecnico', 'rol-admin');
        document.body.classList.add('rol-' + rol);

        var lbl = document.getElementById('auth-user-label');
        if (lbl) lbl.textContent = (usuario && (usuario.username || usuario.nombre)) || '';
        var chip = document.getElementById('auth-rol-chip');
        if (chip) chip.textContent = rol;

        // El botón de auditoría solo para tecnico/admin
        var ba = document.getElementById('btn-auditoria');
        if (ba) ba.style.display = (rol === 'operador') ? 'none' : 'inline-flex';

        // Operador = solo lectura: deshabilitar controles de escritura
        var soloLectura = (rol === 'operador');
        ['#modo-operacion', '#btn-reiniciar-simulador', '#btn-emergencia'].forEach(function (sel) {
            var el = document.querySelector(sel);
            if (el) {
                el.disabled = soloLectura;
                el.style.opacity = soloLectura ? '0.45' : '';
                el.style.cursor = soloLectura ? 'not-allowed' : '';
                if (soloLectura) el.title = 'Acción restringida: rol operador (solo monitoreo)';
            }
        });
    }

    // ---- 4) Bitácora de auditoría ----
    async function abrirAuditoria() {
        var modal = document.getElementById('audit-modal');
        var tb = document.getElementById('audit-tbody');
        if (!modal || !tb) return;
        tb.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
        modal.style.display = 'flex';
        try {
            var r = await fetch('/api/auth/auditoria?limite=200');
            if (!r.ok) { tb.innerHTML = '<tr><td colspan="6">No autorizado</td></tr>'; return; }
            var data = await r.json();
            var ev = (data && data.eventos) || [];
            if (!ev.length) { tb.innerHTML = '<tr><td colspan="6">Sin eventos registrados</td></tr>'; return; }
            tb.innerHTML = ev.map(function (e) {
                var ts = escaparHtml(String(e.timestamp || '').replace('T', ' ').slice(0, 19));
                var usuario = escaparHtml(e.usuario);
                var rol = escaparHtml(e.rol);
                var accion = escaparHtml(e.accion);
                var resultadoRaw = String(e.resultado || '');
                var resultado = escaparHtml(resultadoRaw);
                var resultadoClase = resultadoRaw.replace(/[^A-Za-z0-9_-]/g, '');
                var motivo = escaparHtml(e.motivo);
                return '<tr>' +
                    '<td>' + ts + '</td>' +
                    '<td>' + usuario + '</td>' +
                    '<td>' + rol + '</td>' +
                    '<td>' + accion + '</td>' +
                    '<td class="res-' + resultadoClase + '">' + resultado + '</td>' +
                    '<td>' + motivo + '</td>' +
                    '</tr>';
            }).join('');
        } catch (e) {
            tb.innerHTML = '<tr><td colspan="6">Error al cargar la bitácora</td></tr>';
        }
    }

    function cerrarAuditoria() {
        var m = document.getElementById('audit-modal');
        if (m) m.style.display = 'none';
    }

    // ---- 5) Arranque ----
    function initAuth() {
        var overlay = document.getElementById('auth-overlay');
        var token = localStorage.getItem(TOKEN_KEY);
        if (!token) { if (overlay) overlay.style.display = 'flex'; return; }

        if (overlay) overlay.style.display = 'none'; // optimista: hay token
        var cached = localStorage.getItem(USER_KEY);
        if (cached) { try { aplicarUIporRol(JSON.parse(cached)); } catch (e) { } }

        // Verificar token contra el backend
        fetch('/api/auth/me')
            .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
            .then(function (u) { aplicarUIporRol(u); })
            .catch(function () {
                localStorage.removeItem(TOKEN_KEY);
                localStorage.removeItem(USER_KEY);
                if (overlay) overlay.style.display = 'flex';
            });
    }

    // Exponer funciones usadas por el HTML
    window.hacerLogin = hacerLogin;
    window.cerrarSesion = cerrarSesion;
    window.abrirAuditoria = abrirAuditoria;
    window.cerrarAuditoria = cerrarAuditoria;

    // Conectar eventos cuando el DOM esté disponible
    function conectar() {
        var btn = document.getElementById('auth-login-btn');
        if (btn) btn.addEventListener('click', hacerLogin);
        var form = document.getElementById('auth-form');
        if (form) form.addEventListener('submit', function (e) { e.preventDefault(); hacerLogin(); });
        var pass = document.getElementById('auth-pass');
        if (pass) pass.addEventListener('keydown', function (e) { if (e.key === 'Enter') hacerLogin(); });
        initAuth();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', conectar);
    } else {
        conectar();
    }
})();
