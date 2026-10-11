"""
Script para iniciar el servidor backend limpiando el puerto 8000 primero
"""
import sys
import subprocess
from pathlib import Path

from utilidades_proceso import liberar_puerto_backend


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / 'servidor-backend'

# Configurar encoding para Windows
if sys.platform == 'win32':
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure:
            reconfigure(encoding='utf-8', errors='replace')

def limpiar_puerto_8000():
    """Libera el puerto solo si lo ocupa una instancia previa del backend."""
    print("=" * 60)
    print("   Limpiando puerto 8000...")
    print("=" * 60)

    disponible = liberar_puerto_backend(8000)
    print()
    return disponible

def iniciar_servidor():
    """Inicia el servidor backend"""
    print("=" * 60)
    print("   Iniciando servidor backend...")
    print("=" * 60)
    print()

    # Iniciar el servidor
    try:
        subprocess.run(
            [sys.executable, str(BACKEND_DIR / 'main.py')],
            cwd=BACKEND_DIR,
            check=True,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n[!] Servidor detenido por el usuario")
        return 0
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"\n[ERROR] {e}")
        return 1

if __name__ == '__main__':
    try:
        if not limpiar_puerto_8000():
            raise SystemExit(1)
        raise SystemExit(iniciar_servidor())
    except Exception as e:
        print(f"\n[ERROR FATAL] {e}")
        raise SystemExit(1) from e
