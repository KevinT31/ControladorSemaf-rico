"""
Script para iniciar el servidor backend limpiando el puerto 8000 primero
"""
import os
import sys
import time
import subprocess
import psutil

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def limpiar_puerto_8000():
    """Mata todos los procesos que usen el puerto 8000"""
    print("=" * 60)
    print("   Limpiando puerto 8000...")
    print("=" * 60)

    procesos_terminados = 0

    # Buscar procesos usando el puerto 8000
    for conn in psutil.net_connections():
        if conn.laddr.port == 8000:
            try:
                proceso = psutil.Process(conn.pid)
                nombre = proceso.name()
                print(f"   [!] Terminando proceso: {nombre} (PID: {conn.pid})")
                proceso.kill()
                procesos_terminados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if procesos_terminados > 0:
        print(f"   [OK] {procesos_terminados} proceso(s) terminado(s)")
        print("   Esperando 2 segundos...")
        time.sleep(2)
    else:
        print("   [OK] Puerto 8000 esta libre")

    print()

def iniciar_servidor():
    """Inicia el servidor backend"""
    print("=" * 60)
    print("   Iniciando servidor backend...")
    print("=" * 60)
    print()

    # Cambiar al directorio del servidor
    os.chdir(os.path.join(os.path.dirname(__file__), 'servidor-backend'))

    # Iniciar el servidor
    try:
        subprocess.run([sys.executable, 'main.py'], check=True)
    except KeyboardInterrupt:
        print("\n\n[!] Servidor detenido por el usuario")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        input("Presiona Enter para salir...")

if __name__ == '__main__':
    try:
        limpiar_puerto_8000()
        iniciar_servidor()
    except Exception as e:
        print(f"\n[ERROR FATAL] {e}")
        input("Presiona Enter para salir...")
