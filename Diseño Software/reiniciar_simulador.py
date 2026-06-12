#!/usr/bin/env python3
"""
Script para reinicializar el simulador con las 47 intersecciones
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def reiniciar_simulador():
    """Reinicia el simulador"""
    try:
        print("📡 Enviando solicitud de reinicio al servidor...")
        response = requests.post(
            f"{BASE_URL}/api/simulacion/reiniciar",
            params={"escenario": "hora_pico_manana"}
        )
        
        if response.status_code == 200:
            print("✅ Simulador reiniciado correctamente")
            print(f"Respuesta: {response.json()}")
        else:
            print(f"❌ Error al reiniciar: {response.status_code}")
            print(f"Detalle: {response.text}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("Asegúrate de que el servidor está corriendo en http://localhost:8000")

if __name__ == "__main__":
    reiniciar_simulador()
