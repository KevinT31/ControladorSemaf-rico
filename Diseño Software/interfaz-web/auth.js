/*
 * Ciberseguridad del dashboard (capa de cliente)
 * ==============================================
 * - Adjunta el token JWT a las llamadas API del mismo origen.
 * - Controla el inicio/cierre de sesión y publica su estado al dashboard.
 * - Aplica la UI según el rol (operador = solo lectura).
 * - Muestra la bitácora de auditoría sin insertar datos como HTML.
 */
(function () {
    'use strict';

    var TOKEN_KEY = 'cs_token';
    var USER_KEY = 'cs_user';
    var EVENTO_SESION_VALIDADA = 'cs:auth-validada';
    var EVENTO_SESION_INVALIDADA = 'cs:auth-invalidada';
    var sesionValidada = false;
    var loginEnCurso = false;

    function obtenerToken() {
        return localStorage.getItem(TOKEN_KEY) || '';
    }

    function estaValidada() {
        return sesionValidada && Boolean(obtenerToken());
    }

    function notificarSesionValidada(usuario) {
        sesionValidada = true;
        window.dispatchEvent(new CustomEvent(EVENTO_SESION_VALIDADA, {
            detail: { usuario: usuario || {} }
        }));
    }

    function invalidarSesion() {
        var teniaSesion = sesionValidada || Boolean(obtenerToken());
        sesionValidada = false;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);

        var overlay = document.getElementById('auth-overlay');
        if (overlay) overlay.style.display = 'flex';

        if (teniaSesion) {
            window.dispatchEvent(new CustomEvent(EVENTO_SESION_INVALIDADA));
        }
    }

    // ---- 1) Interceptar fetch: adjuntar Authorization solo a esta API ----
    var fetchOriginal = window.fetch.bind(window);
    window.fetch = function (input, init) {
        init = init || {};
        var esApiProtegida = false;

        try {
            var rawUrl = (typeof input === 'string' || input instanceof URL)
                ? String(input)
                : (input && input.url) || '';
            var url = new URL(rawUrl, window.location.href);
            var mismoOrigen = window.location.protocol === 'file:'
                ? (url.hostname === 'localhost' || url.hostname === '127.0.0.1')
                : url.origin === window.location.origin;

            esApiProtegida = mismoOrigen && url.pathname.startsWith('/api/') &&
                url.pathname !== '/api/auth/login';

            var token = obtenerToken();
            if (token && esApiProtegida) {
                var headersIniciales = init.headers ||
                    (typeof input !== 'string' && input && input.headers) || {};
                var headers = new Headers(headersIniciales);
                if (!headers.has('Authorization')) {
                    headers.set('Authorization', 'Bearer ' + token);
                }
                init.headers = headers;
            }
        } catch (e) {
            // Un error del wrapper no debe impedir una petición pública.
        }

        return fetchOriginal(input, init).then(function (response) {
            if (esApiProtegida && response.status === 401) invalidarSesion();
            return response;
        });
    };

    // ---- 2) Login ----
    async function hacerLogin() {
        if (loginEnCurso) return;

        var u = (document.getElementById('auth-user').value || '').trim();
        var p = document.getElementById('auth-pass').value || '';
        var err = document.getElementById('auth-error');
        var btn = document.getElementById('auth-login-btn');
        err.textContent = '';
        if (!u || !p) {
            err.textContent = 'Ingrese usuario y contraseña';
            return;
        }

        loginEnCurso = true;
        if (btn) btn.disabled = true;
        try {
            var r = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            if (!r.ok) {
                if (r.status === 429) {
                    err.textContent = 'Demasiados intentos. Espere un momento y vuelva a intentar';
                } else if (r.status >= 500) {
                    err.textContent = 'El servidor no pudo procesar el inicio de sesión';
                } else {
                    err.textContent = 'Usuario o contraseña incorrectos';
                }
                return;
            }

            var data = await r.json();
            if (!data.access_token) throw new Error('El servidor no devolvió un token');
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.usuario || {}));
            aplicarUIporRol(data.usuario || {});

            var overlay = document.getElementById('auth-overlay');
            if (overlay) overlay.style.display = 'none';
            notificarSesionValidada(data.usuario || {});
        } catch (e) {
            err.textContent = 'No se pudo conectar con el servidor';
        } finally {
            loginEnCurso = false;
            if (btn) btn.disabled = false;
        }
    }

    function cerrarSesion() {
        invalidarSesion();
        location.reload();
    }

    // ---- 3) UI según rol ----
    function aplicarUIporRol(usuario) {
        var rol = (usuario && usuario.rol) || 'operador';
        if (['operador', 'tecnico', 'admin'].indexOf(rol) === -1) rol = 'operador';

        document.body.classList.remove('rol-operador', 'rol-tecnico', 'rol-admin');
        document.body.classList.add('rol-' + rol);

        var lbl = document.getElementById('auth-user-label');
        if (lbl) lbl.textContent = (usuario && (usuario.username || usuario.nombre)) || '';
        var chip = document.getElementById('auth-rol-chip');
        if (chip) chip.textContent = rol;

        var ba = document.getElementById('btn-auditoria');
        if (ba) ba.style.display = (rol === 'operador') ? 'none' : 'inline-flex';

        var soloLectura = rol === 'operador';
        ['#modo-operacion', '#btn-reiniciar-simulador', '#btn-emergencia'].forEach(function (sel) {
            var elemento = document.querySelector(sel);
            if (!elemento) return;
            elemento.disabled = soloLectura;
            elemento.style.opacity = soloLectura ? '0.45' : '';
            elemento.style.cursor = soloLectura ? 'not-allowed' : '';
            elemento.title = soloLectura
                ? 'Acción restringida: rol operador (solo monitoreo)'
                : '';
        });
    }

    // ---- 4) Bitácora de auditoría ----
    function mostrarMensajeTabla(tbody, mensaje) {
        var tr = document.createElement('tr');
        var td = document.createElement('td');
        td.colSpan = 6;
        td.textContent = mensaje;
        tr.appendChild(td);
        tbody.replaceChildren(tr);
    }

    async function abrirAuditoria() {
        var modal = document.getElementById('audit-modal');
        var tb = document.getElementById('audit-tbody');
        if (!modal || !tb) return;

        mostrarMensajeTabla(tb, 'Cargando…');
        modal.style.display = 'flex';
        try {
            var r = await fetch('/api/auth/auditoria?limite=200');
            if (!r.ok) {
                mostrarMensajeTabla(tb, 'No autorizado');
                return;
            }

            var data = await r.json();
            var eventos = (data && data.eventos) || [];
            if (!eventos.length) {
                mostrarMensajeTabla(tb, 'Sin eventos registrados');
                return;
            }

            var filas = eventos.map(function (evento) {
                var timestamp = String(evento.timestamp || '').replace('T', ' ').slice(0, 19);
                var resultado = String(evento.resultado || '');
                var valores = [
                    timestamp,
                    evento.usuario,
                    evento.rol,
                    evento.accion,
                    resultado,
                    evento.motivo
                ];
                var tr = document.createElement('tr');
                valores.forEach(function (valor, indice) {
                    var td = document.createElement('td');
                    td.textContent = valor == null ? '' : String(valor);
                    if (indice === 4 && (resultado === 'ACEPTADO' || resultado === 'RECHAZADO')) {
                        td.classList.add('res-' + resultado);
                    }
                    tr.appendChild(td);
                });
                return tr;
            });
            tb.replaceChildren.apply(tb, filas);
        } catch (e) {
            mostrarMensajeTabla(tb, 'Error al cargar la bitácora');
        }
    }

    function cerrarAuditoria() {
        var modal = document.getElementById('audit-modal');
        if (modal) modal.style.display = 'none';
    }

    // ---- 5) Arranque ----
    function initAuth() {
        var overlay = document.getElementById('auth-overlay');
        var token = obtenerToken();
        if (!token) {
            if (overlay) overlay.style.display = 'flex';
            return;
        }

        var cached = localStorage.getItem(USER_KEY);
        if (cached) {
            try { aplicarUIporRol(JSON.parse(cached)); } catch (e) { /* caché inválida */ }
        }

        fetch('/api/auth/me')
            .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('Sesión inválida')); })
            .then(function (usuario) {
                aplicarUIporRol(usuario);
                if (overlay) overlay.style.display = 'none';
                notificarSesionValidada(usuario);
            })
            .catch(function () {
                invalidarSesion();
            });
    }

    window.hacerLogin = hacerLogin;
    window.cerrarSesion = cerrarSesion;
    window.abrirAuditoria = abrirAuditoria;
    window.cerrarAuditoria = cerrarAuditoria;
    window.ControlSemaforicoAuth = Object.freeze({
        obtenerToken: obtenerToken,
        estaValidada: estaValidada,
        invalidarSesion: invalidarSesion,
        EVENTO_SESION_VALIDADA: EVENTO_SESION_VALIDADA,
        EVENTO_SESION_INVALIDADA: EVENTO_SESION_INVALIDADA
    });

    function conectar() {
        var btn = document.getElementById('auth-login-btn');
        var form = document.getElementById('auth-form');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                hacerLogin();
            });
        } else if (btn) {
            btn.addEventListener('click', hacerLogin);
        }
        initAuth();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', conectar);
    } else {
        conectar();
    }
})();
