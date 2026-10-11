#!/usr/bin/env python3
"""Reinicia el simulador local mediante la API autenticada."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://localhost:8000"


def _validar_base_url(base_url: str) -> str:
    partes = urllib.parse.urlsplit(base_url)
    if (partes.scheme not in ("http", "https") or not partes.hostname
            or partes.username is not None or partes.password is not None
            or partes.query or partes.fragment):
        raise ValueError("base-url debe ser una URL http(s) válida sin credenciales")
    return base_url.rstrip("/")


def _solicitar_json(
    base_url: str,
    metodo: str,
    ruta: str,
    *,
    token: str | None = None,
    cuerpo: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    request = urllib.request.Request(
        base_url.rstrip("/") + ruta,
        data=datos,
        method=metodo,
    )
    request.add_header("Accept", "application/json")
    if cuerpo is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        # La base se restringe a http(s) antes de construir la petición.
        with urllib.request.urlopen(  # nosec B310
                request, timeout=10) as response:
            contenido = response.read().decode("utf-8")
            return response.status, json.loads(contenido or "{}")
    except urllib.error.HTTPError as exc:
        contenido = exc.read().decode("utf-8", errors="replace")
        try:
            detalle = json.loads(contenido or "{}")
        except json.JSONDecodeError:
            detalle = {"detail": contenido}
        return exc.code, detalle


def _iniciar_sesion(base_url: str, username: str) -> str:
    password = os.environ.get("SEMAFORO_PASSWORD")
    if password is None:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "La API exige autenticación. Define SEMAFORO_PASSWORD para "
                "ejecutar el reinicio sin una consola interactiva."
            )
        password = getpass.getpass(f"Contraseña para {username}: ")

    estado, respuesta = _solicitar_json(
        base_url,
        "POST",
        "/api/auth/login",
        cuerpo={"username": username, "password": password},
    )
    token = respuesta.get("access_token")
    if estado != 200 or not isinstance(token, str) or not token:
        detalle = respuesta.get("detail", "credenciales rechazadas")
        raise RuntimeError(f"No se pudo iniciar sesión (HTTP {estado}): {detalle}")
    return token


def reiniciar_simulador(
    base_url: str,
    escenario: str,
    username: str,
) -> bool:
    """Reinicia el escenario y devuelve si la operación terminó correctamente."""
    base_url = _validar_base_url(base_url)
    ruta = "/api/simulacion/reiniciar?" + urllib.parse.urlencode(
        {"escenario": escenario}
    )
    token = os.environ.get("SEMAFORO_TOKEN")

    print(f"📡 Enviando solicitud de reinicio a {base_url}...")
    estado, respuesta = _solicitar_json(base_url, "POST", ruta, token=token)

    if estado in (401, 403):
        token = _iniciar_sesion(base_url, username)
        estado, respuesta = _solicitar_json(base_url, "POST", ruta, token=token)

    if estado == 200:
        print("✅ Simulador reiniciado correctamente")
        print(json.dumps(respuesta, ensure_ascii=False, indent=2))
        return True

    detalle = respuesta.get("detail", respuesta)
    print(f"❌ Error al reiniciar (HTTP {estado}): {detalle}")
    return False


def _crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SEMAFORO_BASE_URL", DEFAULT_BASE_URL),
        help="URL del backend (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--escenario",
        default="hora_pico_manana",
        help="Escenario que cargará el simulador",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("SEMAFORO_USERNAME", "tecnico"),
        help="Usuario técnico o administrador (por defecto: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _crear_parser().parse_args(argv)
    try:
        correcto = reiniciar_simulador(args.base_url, args.escenario, args.username)
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"❌ No se pudo reiniciar el simulador: {exc}")
        return 1
    return 0 if correcto else 1


if __name__ == "__main__":
    raise SystemExit(main())
