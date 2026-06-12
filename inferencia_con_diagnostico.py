import os
import sys
import time
import pickle
import numpy as np

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

# Intentar importar pyserial para modo físico
pyserial_available = True
try:
    import serial
except ImportError:
    pyserial_available = False
    print("[WARN] PySerial no está instalado. El modo puerto físico estará deshabilitado.")

# Reconfigure stdout to use UTF-8 if possible
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Configuración
SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
PASOS_TIEMPO = 30

DIAGNOSTICOS = {
    'MQ7':    ('CO elevado',      'Combustión incompleta o temperatura de pirólisis demasiado baja.'),
    'MQ135':  ('VOCs elevados',   'Presencia excesiva de aromáticos (benceno/tolueno) por pirólisis incompleta.'),
    'MQ4':    ('CH4 elevado',     'Exceso de metano: la temperatura óptima del reactor no ha sido alcanzada.'),
    'MQ2':    ('GLP/Propano alto', 'Fracción gaseosa liviana alta por condensación insuficiente.'),
    'MQ3':    ('Alcoholes altos', 'Posible contaminación de la materia prima por PET o plásticos oxigenados.'),
    'MQ9':    ('Monóxido/Combustibles altos', 'Presencia excesiva de gases combustibles de rango medio.'),
    'temp':   ('Temperatura inestable', 'Revisar control térmico del reactor de pirólisis.'),
    'humedad':('Humedad elevada',  'Interferencia por humedad ambiental. Revisar la trampa de agua/condensador.'),
}

def encontrar_archivo(nombre, directorios_busqueda):
    for d in directorios_busqueda:
        path = os.path.join(d, nombre)
        if os.path.exists(path):
            return path
    return None

def diagnosticar_diferencias(ventana_normalizada, perfil_referencia):
    """
    Compara las lecturas promedio de la ventana normalizada contra el perfil 
    promedio de la gasolina 90 e identifica desviaciones significativas.
    """
    if perfil_referencia is None:
        return ["  [OK] Sin perfil de referencia de gasolina disponible para diagnóstico."]
        
    # Calcular el promedio temporal de la ventana actual para cada sensor
    perfil_actual = np.mean(ventana_normalizada, axis=0) # shape: (8,)
    
    # La diferencia en espacio normalizado equivale a desviaciones estándar (Z-score)
    diferencias = perfil_actual - perfil_referencia
    
    alertas = []
    for i, sensor in enumerate(SENSORES):
        diff = diferencias[i]
        # Desviación mayor a 1.0 estándar se considera significativa
        if abs(diff) > 1.0:
            direccion = 'ALTO' if diff > 0 else 'BAJO'
            if sensor in DIAGNOSTICOS:
                titulo, causa = DIAGNOSTICOS[sensor]
                alertas.append(f"  [ALERTA] {sensor} {direccion} (desviación: {diff:+.2f} std dev)\n     Detalle: {titulo} -> {causa}")
            else:
                alertas.append(f"  [ALERTA] {sensor} {direccion} (desviación: {diff:+.2f} std dev)")
                
    if not alertas:
        return ["  [OK] Perfil sensorial idéntico o muy similar a Gasolina 90. Sin alertas."]
    return alertas

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Script de inferencia con diagnóstico físico-químico SOTA para E-Nose.")
    parser.add_argument("--port", type=str, default="COM3", help="Puerto serial al que está conectado el ESP32.")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate para la conexión serial.")
    parser.add_argument("--sim", action="store_true", help="Forzar el modo simulación usando datos de CSV.")
    parser.add_argument("--test", action="store_true", help="Ejecutar una única inferencia rápida y salir.")
    args = parser.parse_args()
    
    dirs = [".", "model", "../model"]
    model_path = encontrar_archivo("enose_modelo.tflite", dirs)
    scaler_path = encontrar_archivo("scaler.pkl", dirs)
    encoder_path = encontrar_archivo("label_encoder.pkl", dirs)
    ref_path = encontrar_archivo("perfil_referencia.pkl", dirs)
    
    if not model_path or not scaler_path or not encoder_path:
        print("[ERROR] No se encontraron archivos requeridos (enose_modelo.tflite, scaler.pkl, label_encoder.pkl)")
        sys.exit(1)
        
    print(f"[INFO] Cargando modelo: {model_path}")
    print(f"[INFO] Cargando scaler: {scaler_path}")
    print(f"[INFO] Cargando label encoder: {encoder_path}")
    
    # Cargar preprocesadores
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    with open(encoder_path, 'rb') as f:
        le = pickle.load(f)
        
    # Cargar perfil de referencia de gasolina
    perfil_referencia = None
    if ref_path:
        print(f"[INFO] Cargando perfil de referencia de gasolina: {ref_path}")
        with open(ref_path, 'rb') as f:
            perfil_referencia = pickle.load(f)
    else:
        print("[WARN] No se encontró 'perfil_referencia.pkl'. Diagnósticos detallados deshabilitados.")
        
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
            print(f"[INFO] Conectando al ESP32 en el puerto '{args.port}' a {args.baud} baudios...")
            ser = serial.Serial(args.port, args.baud, timeout=2)
            print("[INFO] Conectado exitosamente. Adquiriendo datos...")
        except Exception as e:
            print(f"[WARN] No se pudo abrir el puerto serial '{args.port}': {e}")
            print("[INFO] Activando modo SIMULACIÓN automática leyendo de 'data/datos_etiquetados.csv'")
            usar_simulacion = True
            
    sim_data_idx = 0
    df_sim = None
    if usar_simulacion:
        csv_path = encontrar_archivo("datos_etiquetados.csv", [".", "data", "../data"])
        if csv_path:
            print(f"[INFO] Cargando datos de simulación desde: {csv_path}")
            import pandas as pd
            df_sim = pd.read_csv(csv_path)
        else:
            print("[ERROR] No se encontró 'datos_etiquetados.csv' para simular.")
            sys.exit(1)
            
    buffer = []
    print("\n" + "="*50)
    print("SISTEMA DE INFERENCIA Y DIAGNÓSTICO EN TIEMPO REAL")
    print("="*50)
    print(f"Esperando acumular ventanas de {PASOS_TIEMPO} segundos...")
    
    try:
        while True:
            if usar_simulacion:
                row = df_sim.iloc[sim_data_idx]
                valores = [float(row[s]) for s in SENSORES]
                clase_real = row.get("clase_calidad", "desconocida")
                muestra_id = row.get("muestra_id", "desconocida")
                
                # Simular tiempo de muestreo
                time.sleep(0.01 if args.test else 1.0)
                sim_data_idx = (sim_data_idx + 1) % len(df_sim)
                
                if sim_data_idx % 30 == 0:
                    print(f"\n[SIM] Leyendo secuencia para experimento: {muestra_id} (Etiqueta real: {clase_real})")
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
            sys.stdout.write(f"\rProgreso ventana: {len(buffer)}/{PASOS_TIEMPO}s")
            sys.stdout.flush()
            
            if len(buffer) == PASOS_TIEMPO:
                print("\n[INFO] Ventana de 30s completada. Procesando...")
                
                # Preprocesar
                ventana = np.array(buffer)
                ventana_normalizada = scaler.transform(ventana) # (30, 8)
                
                # Adaptar tensor de entrada (batch_size=1, timesteps=30, channels=8)
                entrada = ventana_normalizada[np.newaxis, :, :].astype(np.float32)
                
                # Ejecutar inferencia
                interpreter.set_tensor(input_details[0]['index'], entrada)
                interpreter.invoke()
                probabilidades = interpreter.get_tensor(output_details[0]['index'])[0]
                
                # Decodificar predicción
                clase_id = np.argmax(probabilidades)
                confianza = probabilidades[clase_id] * 100
                nombre_clase = le.classes_[clase_id]
                
                print("\n" + "#"*50)
                print(f"DIAGNÓSTICO DEL MODELO: {nombre_clase.upper()}")
                print(f"Confianza de clasificación: {confianza:.2f}%")
                print("#"*50)
                print("Probabilidades por clase:")
                for c_idx, c_name in enumerate(le.classes_):
                    print(f"  - {c_name}: {probabilidades[c_idx]*100:.2f}%")
                
                print("\nANÁLISIS DE DESVIACIÓN QUÍMICA (SOTA):")
                alertas = diagnosticar_diferencias(ventana_normalizada, perfil_referencia)
                for alerta in alertas:
                    print(alerta)
                print("#"*50 + "\n")
                
                buffer = []
                if args.test:
                    print("[INFO] Test rápido de inferencia finalizado con éxito.")
                    break
                    
                print("Esperando la siguiente ventana de adquisición...")
                
    except KeyboardInterrupt:
        print("\n\n[INFO] Deteniendo inferencia por interrupción de usuario.")
    finally:
        if ser:
            ser.close()
            print("[INFO] Puerto serial cerrado.")

if __name__ == '__main__':
    main()
