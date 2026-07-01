import os
import sys
import time
import random
import pandas as pd
import requests

# Configuración por defecto
DEFAULT_SERVER = "http://localhost:8000"
base_dir = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(base_dir, "data", "datos_reales.csv")

def main():
    print("======================================================================")
    print("        STREAMER DE DATASETS E-NOSE (Simulador de Cliente Laptop)")
    print("======================================================================")
    
    # 1. Configurar servidor de destino
    server = input(f"Ingrese la URL de la API (Presione Enter para {DEFAULT_SERVER}): ").strip()
    if not server:
        server = DEFAULT_SERVER
    
    # Auto-completar puerto 8000 si no se especifica
    host_part = server.replace("http://", "").replace("https://", "")
    if ":" not in host_part:
        server = server + ":8000"
        
    if not server.startswith("http://") and not server.startswith("https://"):
        server = "http://" + server

    # Validar conexión
    print(f"\n[INFO] Validando conexión con el servidor en {server}/health...")
    try:
        r = requests.get(f"{server}/health", timeout=3)
        if r.status_code == 200:
            print("  [OK] Conexión establecida exitosamente.")
    except Exception as e:
        print(f"  [ERROR] No se pudo conectar al servidor en {server}.")
        print("  Asegúrese de que el servidor FastAPI esté corriendo y la IP sea correcta.")
        print(f"  Detalle del error: {e}")
        sys.exit(1)

    # 2. Cargar Dataset
    if not os.path.exists(DATASET_PATH):
        print(f"\n[ERROR] No se encontró el dataset en {DATASET_PATH}")
        sys.exit(1)

    print(f"\n[INFO] Cargando dataset de pruebas desde {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)
    lotes_grouped = list(df.groupby('muestra_id'))
    total_lotes = len(lotes_grouped)
    print(f"  [OK] Se cargaron {total_lotes} lotes experimentales de gasolina.")

    while True:
        print("\n" + "="*50)
        print(" SELECCIONE EL LOTE EXPERIMENTAL A TRANSMITIR:")
        print("--------------------------------------------------")
        print("  * Muestra 1 a 150  : Perfiles de GRADO A (Conforme)")
        print("  * Muestra 151 a 300: Perfiles de GRADO B (Desviación)")
        print("  * Muestra 301 a 450: Perfiles de GRADO C (Fuera de especificaciones)")
        print("--------------------------------------------------")
        print("  [r] Seleccionar un lote aleatorio")
        print("  [s] Salir")
        print("="*50)
        
        opcion = input("Ingrese el número de lote (1-450) o una opción: ").strip().lower()
        
        if opcion == 's':
            print("\nFinalizando streamer de datos. ¡Hasta luego!")
            break
            
        lote_idx = None
        if opcion == 'r':
            lote_idx = random.randint(1, total_lotes)
            print(f"[INFO] Seleccionado lote aleatorio: {lote_idx}")
        else:
            try:
                val = int(opcion)
                if 1 <= val <= total_lotes:
                    lote_idx = val
                else:
                    print(f"[ADVERTENCIA] Por favor ingrese un número entre 1 y {total_lotes}.")
                    continue
            except ValueError:
                print("[ADVERTENCIA] Entrada no válida.")
                continue

        # Extraer lote seleccionado
        muestra_id, group = lotes_grouped[lote_idx - 1]
        etiqueta_real = group['etiqueta'].values[0] if 'etiqueta' in group.columns else 'ALTA'
        tipo_plastico = group['tipo_plastico'].values[0] if 'tipo_plastico' in group.columns else 'PE'
        temp_max = group['temp_max'].values[0] if 'temp_max' in group.columns else 430.0
        
        # Mapear etiqueta a términos formales de tesis
        dictamen_esperado = ""
        if etiqueta_real == "ALTA":
            dictamen_esperado = "Grado A (Conforme)"
        elif etiqueta_real == "MEDIA":
            dictamen_esperado = "Grado B (Desviado)"
        else:
            dictamen_esperado = "Grado C (No Conforme)"

        print(f"\n[INFORMACIÓN DEL LOTE {lote_idx}]")
        print(f"  - Dictamen Real Esperado: {dictamen_esperado}")
        print(f"  - Reactor Temp Máx: {temp_max}°C")
        print(f"  - Tipo de materia prima: {tipo_plastico}")
        print(f"  - Filas de lecturas de sensores: {len(group)}")

        # 3. Seleccionar Velocidad
        print("\nVELOCIDAD DE TRANSMISIÓN:")
        print("  [1] Tiempo Real (1 lectura por segundo - dura 30s para llenar búfer)")
        print("  [2] Cámara Rápida (0.1 segundos entre lecturas - dura 3s para llenar búfer)")
        speed_opt = input("Seleccione velocidad (1 o 2, Enter para 2): ").strip()
        delay = 0.2
        if speed_opt == "1":
            delay = 1.0
            print("[INFO] Modo Tiempo Real activado. (1.0s por lectura)")
        else:
            print("[INFO] Modo Cámara Rápida activado. (0.2s por lectura)")

        # 4. Purgar el búfer del servidor (Inicio de Ciclo Limpio)
        print(f"\n[INFO] Enviando señal de purga (/clear_buffer) a {server}...")
        try:
            r_clear = requests.post(f"{server}/clear_buffer", timeout=3)
            if r_clear.status_code == 200:
                print("  [PURGA] Búfer del servidor limpio y reiniciado.")
            else:
                print(f"  [ADVERTENCIA] El servidor respondió con código {r_clear.status_code}. Continuando...")
        except Exception as e:
            print(f"  [ADVERTENCIA] No se pudo purgar el búfer: {e}. Continuando...")

        # 5. Transmitir las lecturas de los sensores fila por fila
        print("\n[TRANSMISIÓN] Iniciando envío de telemetría de gases...")
        
        SENSORES = ["MQ2", "MQ4", "MQ135", "MQ3", "MQ7", "MQ9", "temp", "humedad"]
        features = group[SENSORES].values
        
        total_filas = len(features)
        
        try:
            for i, row in enumerate(features, 1):
                payload = {
                    "MQ2": float(row[0]),
                    "MQ4": float(row[1]),
                    "MQ135": float(row[2]),
                    "MQ3": float(row[3]),
                    "MQ7": float(row[4]),
                    "MQ9": float(row[5]),
                    "temp": float(row[6]),
                    "humedad": float(row[7])
                }
                
                # Enviar fila individual
                r_post = requests.post(f"{server}/sensor_data", json=payload, timeout=5)
                
                if r_post.status_code == 200:
                    buffer_size = r_post.json().get("buffer_size", 0)
                    print(
                        f"\r  -> Enviado {i:03d}/{total_filas} | Búfer actual: {buffer_size}/30s | "
                        f"Temp: {payload['temp']}°C", end=""
                    )
                else:
                    print(f"\n  [Error] API respondió {r_post.status_code} en la fila {i}")
                    
                time.sleep(delay)
                
            print(f"\n\n[ÉXITO] Transmisión del Lote {lote_idx} finalizada.")
            print(f"[DIAGNOSTICO] Abre el panel web en {server}/ y observa el dictamen de calidad.")
            input("\nPresiona Enter para volver al menú de selección...")
            
        except KeyboardInterrupt:
            print("\n\n[TRANSMISIÓN] Envío cancelado por el usuario.")
            input("Presiona Enter para continuar...")

if __name__ == "__main__":
    main()
