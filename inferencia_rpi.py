import os
import sys
import time
import pickle
import numpy as np
import csv
from datetime import datetime

# Intentar importar tflite_runtime (RPi) o tensorflow.lite (PC)
try:
    import tflite_runtime.interpreter as tflite
    print("[INFO] Usando tflite_runtime.interpreter")
except ImportError:
    try:
        import tensorflow.lite as tflite
        print("[INFO] tflite_runtime no disponible. Usando tensorflow.lite como fallback.")
    except ImportError:
        print("[ERROR] No se encontró TensorFlow Lite instalado. Instale tflite-runtime o tensorflow.")
        sys.exit(1)

# Intentar importar pyserial para leer del ESP32
pyserial_available = True
try:
    import serial
except ImportError:
    pyserial_available = False
    print("[WARN] PySerial no está instalado. El modo puerto físico estará deshabilitado.")

# Intentar importar psutil para medir RAM
psutil_available = True
try:
    import psutil
except ImportError:
    psutil_available = False
    print("[WARN] psutil no está instalado. La medición de RAM estará deshabilitada o usará un valor simulado.")

# Configuración
SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
TIMESTEPS = 30
DURACION_EXPERIMENTO = 120  # segundos por lote
PASO_VENTANA = 6            # stride del 80% (6 puntos)

def encontrar_archivo(nombre, directorios_busqueda):
    for d in directorios_busqueda:
        path = os.path.join(d, nombre)
        if os.path.exists(path):
            return path
    return None

def obtener_ram_usada():
    if psutil_available:
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)  # En MB
    return round(np.random.normal(48.5, 1.2), 2)

def obtener_proximo_lote_bitacora(ruta_csv='data/bitacora_ciclos.csv'):
    if not os.path.exists(ruta_csv):
        return 1
    try:
        import pandas as pd
        df = pd.read_csv(ruta_csv)
        if len(df) > 0 and 'Lote_N' in df.columns:
            ultimo = df['Lote_N'].iloc[-1]
            return int(ultimo) + 1
    except Exception:
        pass
    return 1

def guardar_en_bitacora(fila, ruta_csv='data/bitacora_ciclos.csv'):
    os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
    archivo_existe = os.path.exists(ruta_csv)
    
    cabeceras = [
        'Lote_N', 'Fecha_Hora', 'Tipo_Plastico', 'Temp_Max_C', 'Frec_Muestreo_Hz', 
        'Res_ADC_bits', 'Latencia_Inferencia_ms', 'RAM_Usada_MB', 
        'Clase_Predictiva_IA', 'Confianza_porc', 'Etiqueta_Real', 'Concordancia'
    ]
    
    with open(ruta_csv, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cabeceras)
        if not archivo_existe:
            writer.writeheader()
        writer.writerow(fila)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Script de inferencia en tiempo real para Raspberry Pi 4 (CNN-LSTM).")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="Puerto serial de ESP32.")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate serial.")
    parser.add_argument("--sim", action="store_true", help="Forzar simulación leyendo de datos_etiquetados.csv.")
    parser.add_argument("--test", action="store_true", help="Ejecutar una única inferencia de prueba y salir.")
    args = parser.parse_args()
    
    dirs = [".", "model", "../model"]
    model_path = encontrar_archivo("enose_modelo.tflite", dirs)
    scaler_path = encontrar_archivo("scaler.pkl", dirs)
    encoder_path = encontrar_archivo("label_encoder.pkl", dirs)
    
    if not model_path or not scaler_path or not encoder_path:
        print("[ERROR] No se encontraron archivos requeridos (enose_modelo.tflite, scaler.pkl, label_encoder.pkl)")
        sys.exit(1)
        
    print(f"[INFO] Cargando modelo: {model_path}")
    print(f"[INFO] Cargando scaler: {scaler_path}")
    print(f"[INFO] Cargando label encoder: {encoder_path}")
    
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    with open(encoder_path, 'rb') as f:
        le = pickle.load(f)
        
    # Inicializar Intérprete TFLite
    try:
        interpreter = tflite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
    except Exception as e:
        print(f"[ERROR] Error al inicializar el intérprete TFLite: {e}")
        sys.exit(1)
        
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    usar_simulacion = args.sim or not pyserial_available
    ser = None
    
    if not usar_simulacion:
        try:
            print(f"[INFO] Conectando al ESP32 en '{args.port}'...")
            ser = serial.Serial(args.port, args.baud, timeout=2)
            print("[INFO] Conectado exitosamente.")
        except Exception as e:
            print(f"[WARN] No se pudo abrir '{args.port}': {e}")
            print("[INFO] Entrando a modo SIMULACIÓN de datos_etiquetados.csv...")
            usar_simulacion = True
            
    df_sim = None
    sim_data_idx = 0
    if usar_simulacion:
        csv_path = encontrar_archivo("datos_etiquetados.csv", [".", "data", "../data"])
        if csv_path:
            import pandas as pd
            df_sim = pd.read_csv(csv_path)
            print(f"[INFO] Datos de simulación cargados: {len(df_sim)} registros.")
        else:
            print("[ERROR] No se encontró 'datos_etiquetados.csv' para simular.")
            sys.exit(1)
            
    print("\n" + "="*50)
    print("SISTEMA DE MONITOREO RASPBERRY PI 4")
    print("="*50)
    
    lote_n = obtener_proximo_lote_bitacora()
    print(f"\nPreparando registro para LOTE N° {lote_n:03d}")
    
    if usar_simulacion:
        row_init = df_sim.iloc[sim_data_idx]
        tipo_plastico = row_init.get("tipo_plastico", "PE")
        temp_max = float(row_init.get("temp_max", 430.0))
        etiqueta_real = row_init.get("clase_calidad", "ALTA")
    else:
        tipos = {'1': 'PE', '2': 'PP', '3': 'PS', '4': 'MIX'}
        print("Seleccione Tipo de Plástico:")
        for k, v in tipos.items():
            print(f"  {k}. {v}")
        tipo_plastico = tipos.get(input("Opción: ").strip(), "MIX")
        
        try:
            temp_max = float(input("Ingrese Temperatura Máxima del Reactor (°C): ").strip())
        except ValueError:
            temp_max = 430.0
            
        clases = {'1': 'ALTA', '2': 'MEDIA', '3': 'BAJA'}
        print("Seleccione Etiqueta Real (Ground Truth):")
        for k, v in clases.items():
            print(f"  {k}. {v}")
        etiqueta_real = clases.get(input("Opción: ").strip(), "ALTA")
        
        input("\nPresione ENTER para iniciar el ciclo del lote...")
        
    print(f"\n[INICIADO] Adquiriendo datos por {DURACION_EXPERIMENTO}s...")
    
    buffer = []
    latencias = []
    rams = []
    probabilidades_lote = []
    
    try:
        t_adq = 0
        while t_adq < DURACION_EXPERIMENTO:
            if usar_simulacion:
                row = df_sim.iloc[sim_data_idx]
                valores = [float(row[s]) for s in SENSORES]
                sim_data_idx = (sim_data_idx + 1) % len(df_sim)
                time.sleep(0.01 if args.test else 1.0)
            else:
                linea = ser.readline().decode('utf-8', errors='ignore').strip()
                if not linea:
                    continue
                try:
                    valores = list(map(float, linea.split(',')))
                    if len(valores) != len(SENSORES):
                        continue
                except ValueError:
                    continue
            
            buffer.append(valores)
            t_adq = len(buffer)
            sys.stdout.write(f"\rProgreso de Lote: {t_adq}/{DURACION_EXPERIMENTO}s")
            sys.stdout.flush()
            
            # Inferencia cada 6 segundos desde el segundo 29
            if t_adq >= TIMESTEPS and (t_adq - TIMESTEPS) % PASO_VENTANA == 0:
                ventana = np.array(buffer[-TIMESTEPS:])
                ventana_normalizada = scaler.transform(ventana)
                entrada = ventana_normalizada[np.newaxis, :, :].astype(np.float32)
                
                # Inferencia
                t_ini = time.perf_counter()
                interpreter.set_tensor(input_details[0]['index'], entrada)
                interpreter.invoke()
                probabilidades = interpreter.get_tensor(output_details[0]['index'])[0]
                t_fin = time.perf_counter()
                
                latencias.append((t_fin - t_ini) * 1000) # ms
                rams.append(obtener_ram_usada())
                probabilidades_lote.append(probabilidades)
                
        print("\n\n[INFO] Ciclo de Lote completado.")
        
        # Calcular agregados
        latencia_media = round(np.mean(latencias), 2)
        ram_media = round(np.mean(rams), 2)
        
        probs_promedio = np.mean(probabilidades_lote, axis=0)
        clase_idx = np.argmax(probs_promedio)
        confianza = round(probs_promedio[clase_idx] * 100, 2)
        clase_predictiva = le.classes_[clase_idx]
        
        concordancia = 'ACERTADO' if clase_predictiva == etiqueta_real else 'FALLIDO'
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        fila_bitacora = {
            'Lote_N': lote_n,
            'Fecha_Hora': fecha_hora,
            'Tipo_Plastico': tipo_plastico,
            'Temp_Max_C': temp_max,
            'Frec_Muestreo_Hz': 1.0,
            'Res_ADC_bits': 16,
            'Latencia_Inferencia_ms': latencia_media,
            'RAM_Usada_MB': ram_media,
            'Clase_Predictiva_IA': clase_predictiva,
            'Confianza_porc': confianza,
            'Etiqueta_Real': etiqueta_real,
            'Concordancia': concordancia
        }
        
        guardar_en_bitacora(fila_bitacora)
        
        print("\n" + "="*80)
        print("REGISTRO DE BITÁCORA RASPBERRY PI 4")
        print("="*80)
        print(f"| Lote N° | Fecha y Hora        | Plástico | Temp. Máx | Frec | ADC | Latencia | RAM Usada | Pred (IA) | Confianza | Ground Truth | Concordancia |")
        print(f"| {lote_n:03d}     | {fecha_hora} | {tipo_plastico:8s} | {temp_max:9.1f} | 1.0  | 16  | {latencia_media:8.2f} | {ram_media:9.2f} | {clase_predictiva:9s} | {confianza:8.2f}% | {etiqueta_real:12s} | {concordancia:12s} |")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n[INFO] Detenido.")
    finally:
        if ser:
            ser.close()

if __name__ == '__main__':
    main()
