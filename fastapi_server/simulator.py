import os
import sys
import time
import random
import requests

# Asynchronous keypress detection for Windows
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    WINDOWS = False

API_URL = "http://localhost:8000/sensor_data"

# Profiles definitions matching the real dataset distributions
PRESETS = {
    "1": ("ALTA (Calidad Óptima)", {
        "MQ2": 23231.72, "MQ4": 17268.26, "MQ135": 12320.02, "MQ3": 8474.87,
        "MQ7": 7553.57, "MQ9": 15570.25, "temp": 22.51, "humedad": 59.04
    }),
    "2": ("MEDIA (Temperatura Baja)", {
        "MQ2": 18201.34, "MQ4": 11044.69, "MQ135": 16804.19, "MQ3": 13796.67,
        "MQ7": 20913.72, "MQ9": 14929.37, "temp": 21.99, "humedad": 60.01
    }),
    "3": ("BAJA (Interferencia Humedad)", {
        "MQ2": 12243.10, "MQ4": 7337.01, "MQ135": 41209.19, "MQ3": 14674.02,
        "MQ7": 27708.89, "MQ9": 12053.11, "temp": 22.18, "humedad": 61.06
    }),
    "4": ("BAJA (Contaminación Plástico)", {
        "MQ2": 12351.64, "MQ4": 7639.55, "MQ135": 44349.42, "MQ3": 18576.00,
        "MQ7": 25359.63, "MQ9": 11130.48, "temp": 22.19, "humedad": 61.03
    })
}

def main():
    print("=" * 70)
    print("      SIMULADOR DE MONITOREO DE SENSORES EN VIVO (E-NOSE)")
    print("=" * 70)
    print("Este script simula un módulo ESP32 transmitiendo datos de sensores.")
    print("\nPresione las teclas numéricas en su teclado para cambiar el perfil en vivo:")
    for k, (name, _) in PRESETS.items():
        print(f"  [{k}] Cambiar a: {name}")
    print("  [q] Salir del simulador")
    print("=" * 70)
    
    import argparse
    parser = argparse.ArgumentParser(description="Simulador de sensores E-Nose.")
    parser.add_argument("-p", "--profile", type=str, default="1", choices=["1", "2", "3", "4"],
                        help="Perfil inicial a simular (1=ALTA, 2=MEDIA, 3=BAJA_HUMEDAD, 4=BAJA_PLASTICO)")
    args = parser.parse_args()
    
    current_key = args.profile
    
    # Wait for the API to be ready
    print("Verificando conexión con el servidor FastAPI...")
    try:
        r = requests.get("http://localhost:8000/health")
        if r.status_code == 200:
            print("¡Conexión establecida con éxito!")
    except Exception:
        print("\n[ERROR] No se pudo conectar a la API en http://localhost:8000.")
        print("Por favor, asegúrese de iniciar primero el servidor FastAPI (uvicorn).")
        sys.exit(1)
        
    step = 0
    try:
        while True:
            # Check for keypress on Windows (non-blocking)
            if WINDOWS and msvcrt.kbhit():
                char = msvcrt.getch().decode('utf-8', errors='ignore').strip()
                if char.lower() == 'q':
                    print("\nSaliendo del simulador...")
                    break
                elif char in PRESETS:
                    current_key = char
                    print(f"\n[CAMBIO] Perfil del reactor modificado a: {PRESETS[char][0]}")
                    
            profile_name, base_values = PRESETS[current_key]
            
            # Generate simulated reading with 2% fluctuation noise
            payload = {}
            for k, val in base_values.items():
                noise = 1 + (random.random() * 0.04 - 0.02)
                payload[k] = round(val * noise, 2)
                
            # Send step data to FastAPI
            try:
                response = requests.post(API_URL, json=payload, timeout=2)
                if response.status_code == 200:
                    step += 1
                    buffer_size = response.json().get("buffer_size", 0)
                    print(
                        f"\r[Paso {step:03d}] Enviando... | Búfer: {buffer_size}/30s | "
                        f"Perfil: {profile_name[:12]}... | Temp: {payload['temp']}°C | "
                        f"Hum: {payload['humedad']}%", end=""
                    )
                else:
                    print(f"\n[Error API] Código de estado: {response.status_code}")
            except Exception as e:
                print(f"\n[Error Conexión] Falló el envío de datos: {e}")
                
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nSimulador detenido por el usuario.")

if __name__ == "__main__":
    main()
