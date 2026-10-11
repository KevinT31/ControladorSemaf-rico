"""
Genera tráfico visible desde el inicio del escenario ``lima-amplio``.

Las herramientas se resuelven mediante ``SUMO_HOME`` o ``PATH`` y todos los
archivos se escriben junto a este script, con independencia del directorio de
trabajo desde el que se invoque.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


ESCENARIO_DIR = Path(__file__).resolve().parent


def _sumo_home_desde_path() -> Optional[Path]:
    ejecutable = shutil.which("sumo") or shutil.which("sumo-gui")
    if not ejecutable:
        return None
    # Instalación estándar: <SUMO_HOME>/bin/sumo(.exe).
    return Path(ejecutable).resolve().parent.parent


def localizar_herramientas_sumo() -> Tuple[Path, Path]:
    """Devuelve las rutas a ``randomTrips.py`` y ``duarouter``."""
    home_env = os.environ.get("SUMO_HOME")
    sumo_home = Path(home_env).expanduser().resolve() if home_env else _sumo_home_desde_path()

    random_trips = sumo_home / "tools" / "randomTrips.py" if sumo_home else None
    duarouter_path = shutil.which("duarouter")
    duarouter = (
        Path(duarouter_path).resolve()
        if duarouter_path
        else (sumo_home / "bin" / ("duarouter.exe" if os.name == "nt" else "duarouter")
              if sumo_home else None)
    )

    if random_trips is None or not random_trips.is_file():
        raise FileNotFoundError(
            "No se encontró tools/randomTrips.py. Define SUMO_HOME o agrega SUMO a PATH."
        )
    if duarouter is None or not duarouter.is_file():
        raise FileNotFoundError(
            "No se encontró duarouter. Define SUMO_HOME o agrega SUMO/bin a PATH."
        )
    return random_trips, duarouter


def generar_trafico(seed: int = 42) -> Path:
    """Genera viajes y rutas reproducibles; devuelve el archivo ``.rou.xml``."""
    red = ESCENARIO_DIR / "lima_amplio.net.xml"
    viajes = ESCENARIO_DIR / "lima_amplio_inmediato.trips.xml"
    rutas = ESCENARIO_DIR / "lima_amplio_inmediato.rou.xml"
    if not red.is_file():
        raise FileNotFoundError(f"No se encontró la red del escenario: {red}")

    random_trips, duarouter = localizar_herramientas_sumo()
    print("🚗 Generando tráfico inmediato para pruebas...")

    cmd_viajes = [
        sys.executable,
        str(random_trips),
        "-n", str(red),
        "-o", str(viajes),
        "--fringe-factor", "5",
        "--min-distance", "500",
        "-p", "1.8",  # ~2000 vehículos/hora
        "-b", "0",
        "-e", "3600",
        "--seed", str(int(seed)),
    ]
    resultado = subprocess.run(
        cmd_viajes,
        cwd=ESCENARIO_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"randomTrips.py falló:\n{resultado.stderr.strip()}")

    print("✅ Viajes generados")
    print("🔨 Calculando rutas con duarouter...")
    cmd_router = [
        str(duarouter),
        "-n", str(red),
        "-r", str(viajes),
        "-o", str(rutas),
        "--ignore-errors",
        "--repair",
        "--max-alternatives", "3",
        "--routing-threads", "4",
    ]
    resultado = subprocess.run(
        cmd_router,
        cwd=ESCENARIO_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if resultado.returncode != 0 or not rutas.is_file():
        detalle = resultado.stderr.strip() or resultado.stdout.strip()
        raise RuntimeError(f"duarouter falló:\n{detalle}")

    contenido = rutas.read_text(encoding="utf-8")
    print("✅ Rutas calculadas exitosamente")
    print(f"📊 Total de vehículos: {contenido.count('<vehicle')}")
    print(f"💾 Archivo generado: {rutas}")
    return rutas


def main() -> int:
    try:
        generar_trafico()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
