"""
Verificación HTTP de las mejoras (ciberseguridad + seguridad + trazabilidad)
============================================================================
Requiere el dashboard corriendo (python ejecutar.py -> opción 1).
Uso:  python verificar_demo.py

Solo usa la librería estándar (urllib). Imprime un resumen PASS/FAIL de los
"kill shots" que se mostrarán en la sustentación.
"""

import json
import sys
import urllib.error
import urllib.request

# Consola UTF-8 (Windows/cp1252 no imprime emojis por defecto)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://localhost:8000"


def req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=8) as resp:
            txt = resp.read().decode() or "{}"
            return resp.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode() or "{}")
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    print("=" * 64)
    print("VERIFICACIÓN DE MEJORAS — Sistema de Control Semafórico (PUCP)")
    print("=" * 64)
    print("Servidor:", BASE)

    s, _ = req("GET", "/api/health")
    if s != 200:
        print("\n❌ El dashboard no responde. Arráncalo primero:")
        print("   python ejecutar.py   ->   opción 1 (Iniciar Dashboard)")
        sys.exit(1)

    checks = []

    def chk(nombre, cond):
        checks.append(cond)
        print(("  ✅ " if cond else "  ❌ ") + nombre)

    print("\n[1] Ciberseguridad — autenticación y RBAC")
    s, _ = req("GET", "/api/intersecciones")
    chk("La telemetría exige token (401 sin sesión)", s == 401)

    s, d = req("POST", "/api/auth/login", body={"username": "tecnico", "password": "tecnico123"})
    tok = d.get("access_token")
    chk("Login de técnico emite token JWT", s == 200 and bool(tok))

    s, _ = req("GET", "/api/intersecciones", token=tok)
    chk("Lectura autorizada con token", s == 200)

    s, do = req("POST", "/api/auth/login", body={"username": "operador", "password": "operador123"})
    tok_op = do.get("access_token")
    s, _ = req("PUT", "/api/control/parametros", token=tok_op, body={"t_verde_ns": 45})
    chk("Operador (solo lectura) NO puede enviar comandos (403)", s == 403)

    print("\n[2] Rechazo de comandos peligrosos (protección de la operación)")
    s, d = req("PUT", "/api/control/parametros", token=tok, body={"t_verde_ns": 200})
    motivo = ""
    if isinstance(d.get("detail"), dict):
        errs = d["detail"].get("errores") or []
        motivo = errs[0] if errs else ""
    chk("Verde de 200 s RECHAZADO (422)" + (f" :: {motivo}" if motivo else ""), s == 422)
    s, _ = req("PUT", "/api/control/parametros", token=tok, body={"t_verde_ns": 45})
    chk("Verde de 45 s aceptado (200)", s == 200)

    print("\n[3] Seguridad funcional semafórica")
    s, d = req("GET", "/api/seguridad/demo", token=tok)
    casos_ok = s == 200 and all(c.get("seguro") for c in d.get("casos", []))
    chk("Demo de seguridad: todos los casos seguros", casos_ok)

    print("\n[4] Trazabilidad de la decisión")
    s, d = req("GET", "/api/interseccion/INT-001/explicacion?cola=28&velocidad=12&flujo=22", token=tok)
    chk("Cadena entrada→ICV→reglas→verde disponible", s == 200 and "reglas_disparadas" in d)
    if s == 200:
        print(f"      ICV={d['icv']['valor']} ({d['icv']['nivel']}), "
              f"ΔT={d['delta_t_porcentaje']}%, verde_final={d['verde_final_s']}s")

    print("\n[5] Auditoría")
    s, d = req("GET", "/api/auth/auditoria?limite=50", token=tok)
    n = len(d.get("eventos", []))
    rechazos = sum(1 for e in d.get("eventos", []) if e.get("resultado") == "RECHAZADO")
    chk(f"Bitácora con {n} eventos ({rechazos} rechazos registrados)", s == 200 and n > 0)

    print("\n" + "=" * 64)
    if all(checks):
        print("RESULTADO: ✅ TODO OK — la demo está lista para sustentar")
        sys.exit(0)
    else:
        print("RESULTADO: ❌ HAY FALLOS — revisa los puntos marcados arriba")
        sys.exit(1)


if __name__ == "__main__":
    main()
