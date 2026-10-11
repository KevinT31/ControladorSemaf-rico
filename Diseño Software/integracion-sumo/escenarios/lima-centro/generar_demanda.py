"""Regenera la demanda vehicular de la red lima-centro con semilla fija.

Las salidas versionadas (lima_centro_media.rou.xml.gz y
lima_centro_alta.rou.xml.gz) son las que usa la campaña de la tesis; este
script documenta cómo se obtuvieron y permite regenerarlas. Cada nivel de
demanda es una invocación de randomTrips.py con la misma red, la misma semilla
(42) y distinta densidad de inserción.

Uso:  python generar_demanda.py [--salida DIRECTORIO]
Requiere SUMO instalado y la variable de entorno SUMO_HOME.
"""
import argparse
import gzip
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RED = AQUI / "lima_centro.net.xml.gz"
NIVELES = {"media": 24, "alta": 60}  # densidad de inserción (veh/km/h)
SEMILLA = 42

VIAS = ("highway.motorway,highway.motorway_link,highway.trunk_link,"
        "highway.primary_link,highway.secondary_link,highway.tertiary_link")


def generar(nivel: str, densidad: int, salida: Path) -> Path:
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        sys.exit("Defina SUMO_HOME (carpeta de instalación de SUMO).")
    random_trips = Path(sumo_home) / "tools" / "randomTrips.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        trips, rutas = tmp / "trips.xml", tmp / "rutas.rou.xml"
        subprocess.run([
            sys.executable, str(random_trips), "-n", str(RED),
            "--fringe-factor", "5", "--insertion-density", str(densidad),
            "-o", str(trips), "-r", str(rutas), "-b", "0", "-e", "3600",
            "--trip-attributes", 'departLane="best"',
            "--fringe-start-attributes", 'departSpeed="max"',
            "--validate", "--remove-loops", "--via-edge-types", VIAS,
            "--vehicle-class", "passenger", "--vclass", "passenger",
            "--prefix", "veh", "--min-distance", "300",
            "--min-distance.fringe", "10", "--allow-fringe.min-length", "1000",
            "--lanes", "--seed", str(SEMILLA),
        ], check=True)
        destino = salida / f"lima_centro_{nivel}.rou.xml.gz"
        # randomTrips escribe un comentario inicial con rutas locales de la
        # máquina; se elimina para que la salida sea idéntica en cualquier equipo.
        datos = re.sub(rb"<!--.*?-->\s*", b"", rutas.read_bytes(), flags=re.S)
        with open(destino, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                               mtime=0, compresslevel=9) as g:
                g.write(datos)
    return destino


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=AQUI)
    args = ap.parse_args()
    for nivel, densidad in NIVELES.items():
        print(generar(nivel, densidad, args.salida))
