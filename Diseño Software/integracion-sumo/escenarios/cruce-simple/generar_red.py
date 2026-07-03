"""
Reconstruye cruce.net.xml desde las fuentes versionadas (.nod.xml / .edg.xml).

La red generada trae un programa semafórico estático canónico:
  verde NS (30s) -> amarillo (3s) -> todo-rojo (2s) -> verde EO (30s) -> amarillo (3s) -> todo-rojo (2s)
que es el punto de partida de TODOS los controladores (comparación justa).

Uso:  python generar_red.py
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent


def construir() -> Path:
    try:
        import sumolib
        netconvert = sumolib.checkBinary('netconvert')
    except Exception:
        netconvert = 'netconvert'

    salida = AQUI / 'cruce.net.xml'
    cmd = [
        netconvert,
        '--node-files', str(AQUI / 'cruce.nod.xml'),
        '--edge-files', str(AQUI / 'cruce.edg.xml'),
        '-o', str(salida),
        '--no-turnarounds', 'true',
        # ciclo implícito = 2*(verde 30 + amarillo 3 + todo-rojo 2) = 70 s
        '--tls.green.time', '30',
        '--tls.yellow.time', '3',
        '--tls.allred.time', '2',
    ]
    print('[generar_red]', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print(f'[generar_red] OK -> {salida}')
    return salida


if __name__ == '__main__':
    try:
        construir()
    except FileNotFoundError:
        print('ERROR: netconvert no encontrado. Instala eclipse-sumo (pip install eclipse-sumo).')
        sys.exit(1)
