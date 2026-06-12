import os
import sys
import time
import pickle
import numpy as np

# Intentar importar tflite_runtime (estándar en RPi) o tensorflow.lite (desarrollo en PC)
try:
    import tflite_runtime.interpreter as tflite
    print("[INFO] Usando tflite_runtime.interpreter")
except ImportError:
    try:
        import tensorflow.lite as tflite
        print("[INFO] tflite_runtime no disponible. Usando tensorflow.lite como fallback.")
    except ImportError:
        print("[ERROR] No se encontró TensorFlow Lite instalado. Por favor instale tflite-runtime o tensorflow.")
        sys.exit(1)

# Intentar importar pyserial para leer del ESP32
pyserial_available = True
try:
    import serial
except ImportError:
    pyserial_available = False
    print("[WARN] PySerial no está instalado. El modo puerto físico estará deshabilitado.")

# Configuración
SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
PASOS_TIEMPO = 30
CLASES = {0: 'ALTA CALIDAD', 1: 'BAJA CALIDAD', 2: 'MEDIA CALIDAD'}

def encontrar_archivo(nombre, directorios_busqueda):
    """Busca un archivo en varios directorios."""
    for d in directorios_busqueda:
        path = os.path.join(d, nombre)
        if os.path.exists(path):
            return path
    return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Script de inferencia en tiempo real para E-Nose.")
    parser.add_argument("--port", type=str, default="/dev/ttyUSB0", help="Puerto serial al que está conectado el ESP32.")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate para la conexión serial.")
    parser.add_argument("--sim", action="store_true", help="Forzar el modo simulación usando datos de CSV.")
    parser.add_argument("--test", action="store_true", help="Ejecutar una única inferencia rápida y salir.")
    args = parser.parse_args()
    
    # Buscar modelos y preprocesadores
    dirs = [".", "model", "../model"]
    model_path = encontrar_archivo("enose_modelo.tflite", dirs)
    scaler_path = encontrar_archivo("scaler.pkl", dirs)
    encoder_path = encontrar_archivo("label_encoder.pkl", dirs)
    
    if not model_path or not scaler_path or not encoder_path:
        print("[ERROR] No se encontraron los archivos necesarios (enose_modelo.tflite, scaler.pkl, label_encoder.pkl) en los directorios de búsqueda.")
        sys.exit(1)
        
    print(f"[INFO] Cargando modelo TFLite: {model_path}")
    print(f"[INFO] Cargando scaler: {scaler_path}")
    print(f"[INFO] Cargando label encoder: {encoder_path}")
    
    # Inicializar Intérprete TFLite
    # Habilitar delegados Flex ya que el modelo usa operaciones de TensorFlow para LSTM (Select TF Ops)
    try:
        # En RPi con tflite-runtime, si se usaron SELECT_TF_OPS, se requiere cargar el flex delegate si corresponde,
        # o ejecutar bajo tf.lite normal. En sistemas x86/ARM con la versión completa, corre directo.
        interpreter = tflite.Interpreter(model_path=model_path)
    except Exception as e:
        print(f"[ERROR] Error al inicializar el intérprete: {e}")
        print("[SUGERENCIA] Si estás en Raspberry Pi, asegúrate de tener instalada una versión de tflite-runtime compatible con Select TF Ops.")
        sys.exit(1)
        
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Cargar preprocesadores
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    with open(encoder_path, 'rb') as f:
        le = pickle.load(f)
        
    # Determinar si usamos modo simulación o físico
    usar_simulacion = args.sim or not pyserial_available
    ser = None
    
    if not usar_simulacion:
        try:
            print(f"[INFO] Intentando conectar al ESP32 en el puerto '{args.port}' a {args.baud} baudios...")
            ser = serial.Serial(args.port, args.baud, timeout=2)
            print("[INFO] Conectado exitosamente. Esperando datos del ESP32...")
        except Exception as e:
            print(f"[WARN] No se pudo abrir el puerto serial '{args.port}': {e}")
            print("[INFO] Entrando a modo SIMULACIÓN automática leyendo de 'data/datos_sensores.csv'")
            usar_simulacion = True
            
    # Configurar simulación
    sim_data_idx = 0
    df_sim = None
    if usar_simulacion:
        csv_path = encontrar_archivo("datos_sensores.csv", [".", "data", "../data"])
        if csv_path:
            print(f"[INFO] Cargando datos de simulación desde: {csv_path}")
            import pandas as pd
            df_sim = pd.read_csv(csv_path)
        else:
            print("[ERROR] No se pudo encontrar 'datos_sensores.csv' para simular lecturas.")
            sys.exit(1)
            
    buffer = []
    print("\n--- Sistema de Inferencia Iniciado ---")
    print(f"Acumulando ventanas de {PASOS_TIEMPO} segundos...")
        
    try:
        while True:
            if usar_simulacion:
                # Obtener la fila actual de simulación
                row = df_sim.iloc[sim_data_idx]
                valores = [float(row[s]) for s in SENSORES]
                clase_real = row.get("etiqueta", "desconocida")
                
                # Simular retraso de 1 segundo (o rápido si es test)
                time.sleep(0.01 if args.test else 1.0)
                
                # Avanzar índice de simulación
                sim_data_idx = (sim_data_idx + 1) % len(df_sim)
                if sim_data_idx % 30 == 0:
                    print(f"\n[SIM] Iniciando lectura de muestra real etiquetada como: {clase_real}")
            else:
                linea = ser.readline().decode('utf-8').strip()
                if not linea:
                    continue
                try:
                    # Espera recibir: mq2,mq4,mq135,mq3,mq7,mq9,temp,humedad
                    valores = list(map(float, linea.split(',')))
                    if len(valores) != len(SENSORES):
                        print(f"[WARN] Ignorando línea corrupta: {linea}")
                        continue
                except ValueError:
                    print(f"[WARN] Ignorando línea no numérica: {linea}")
                    continue
                    
            # Acumular en el buffer
            buffer.append(valores)
            sys.stdout.write(f"\rProgreso de ventana: {len(buffer)}/{PASOS_TIEMPO} segundos")
            sys.stdout.flush()
            
            # Realizar inferencia al completar la ventana
            if len(buffer) == PASOS_TIEMPO:
                print("\n[INFO] Ventana completada. Ejecutando clasificación...")
                
                # Convertir a numpy array y normalizar
                ventana = np.array(buffer)  # (30, 8)
                ventana_normalizada = scaler.transform(ventana)  # (30, 8)
                
                # Agregar dimensión de lote: (1, 30, 8)
                entrada = ventana_normalizada[np.newaxis, :, :].astype(np.float32)
                
                # Ejecutar modelo TFLite
                interpreter.set_tensor(input_details[0]['index'], entrada)
                interpreter.invoke()
                probabilidades = interpreter.get_tensor(output_details[0]['index'])[0]
                
                # Clasificar
                clase_id = np.argmax(probabilidades)
                confianza = probabilidades[clase_id] * 100
                nombre_clase = CLASES[clase_id]
                
                print(f"==================================================")
                print(f"DIAGNÓSTICO: {nombre_clase}")
                print(f"Confianza:   {confianza:.2f}%")
                print(f"Detalles:    ALTA: {probabilidades[0]*100:.1f}% | BAJA: {probabilidades[1]*100:.1f}% | MEDIA: {probabilidades[2]*100:.1f}%")
                print(f"==================================================")
                
                # Limpiar buffer para la siguiente muestra
                buffer = []
                if args.test:
                    print("\n[TEST] Inferencia de prueba completada exitosamente. Saliendo.")
                    break
                print("\nEsperando la siguiente ventana de adquisición...")
                
    except KeyboardInterrupt:
        print("\n\n[INFO] Deteniendo inferencia por el usuario.")
        if ser:
            ser.close()
            print("[INFO] Puerto serial cerrado.")

if __name__ == "__main__":
    main()
