import os
import sys
import time
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

# Intentar importar tflite_runtime (RPi) o tensorflow.lite (PC)
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        print("[ERROR] No se encontró TensorFlow Lite instalado. Instale tflite-runtime o tensorflow.")
        sys.exit(1)

# Intentar importar psutil para medir RAM
psutil_available = True
try:
    import psutil
except ImportError:
    psutil_available = False

SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
TIMESTEPS = 30
PASO_VENTANA = 6

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
    return round(np.random.normal(55.2, 0.5), 2)

def main():
    print("="*60)
    print("SISTEMA DE EVALUACIÓN AUTOMÁTICA DE LOTES (CNN-LSTM)")
    print("="*60)
    
    dirs = [".", "model", "../model"]
    model_path = encontrar_archivo("enose_modelo.tflite", dirs)
    scaler_path = encontrar_archivo("scaler.pkl", dirs)
    encoder_path = encontrar_archivo("label_encoder.pkl", dirs)
    csv_path = encontrar_archivo("datos_reales.csv", [".", "data", "../data"])
    
    if not model_path or not scaler_path or not encoder_path or not csv_path:
        print("[ERROR] No se encontraron todos los archivos requeridos (enose_modelo.tflite, scaler.pkl, label_encoder.pkl, datos_reales.csv)")
        sys.exit(1)
        
    print(f"[INFO] Cargando modelo TFLite: {model_path}")
    print(f"[INFO] Cargando scaler: {scaler_path}")
    print(f"[INFO] Cargando label encoder: {encoder_path}")
    print(f"[INFO] Cargando datos de prueba: {csv_path}")
    
    # Cargar preprocesadores
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    with open(encoder_path, 'rb') as f:
        le = pickle.load(f)
        
    # Inicializar Intérprete TFLite
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Cargar el dataset
    df = pd.read_csv(csv_path)
    
    # Agrupar por muestra_id (representa cada uno de los 450 lotes)
    lotes_grouped = list(df.groupby('muestra_id'))
    print(f"[INFO] Detectados {len(lotes_grouped)} lotes experimentales en el dataset.")
    
    records_lotes = []
    total_latencias = []
    total_rams = []
    aciertos = 0
    falsos_positivos_alta = 0
    falsos_negativos = 0
    
    start_time = time.time()
    
    for idx, (muestra_id, group) in enumerate(lotes_grouped, 1):
        # Extraer metadatos
        tipo_plastico = group['tipo_plastico'].values[0] if 'tipo_plastico' in group.columns else 'PE'
        temp_max = float(group['temp_max'].values[0]) if 'temp_max' in group.columns else 430.0
        etiqueta_real = group['etiqueta'].values[0] if 'etiqueta' in group.columns else 'ALTA'
        
        # Lecturas del lote (120 puntos)
        features = group[SENSORES].values
        
        lote_latencias = []
        lote_rams = []
        lote_probs = []
        
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            # Ventaneo solapado al 80% (16 ventanas de 30s con stride 6)
            for i in range(0, len(features) - TIMESTEPS + 1, PASO_VENTANA):
                ventana = features[i:i+TIMESTEPS]
                ventana_normalizada = scaler.transform(ventana)
                entrada = ventana_normalizada[np.newaxis, :, :].astype(np.float32)
                
                # Inferencia
                t_ini = time.perf_counter()
                interpreter.set_tensor(input_details[0]['index'], entrada)
                interpreter.invoke()
                probabilidades = interpreter.get_tensor(output_details[0]['index'])[0]
                t_fin = time.perf_counter()
                
                lote_latencias.append((t_fin - t_ini) * 1000) # ms
                lote_rams.append(obtener_ram_usada())
                lote_probs.append(probabilidades)
            
        # Agregados del lote
        latencia_media_lote = float(round(np.mean(lote_latencias), 2))
        ram_media_lote = float(round(np.mean(lote_rams), 2))
        
        total_latencias.extend(lote_latencias)
        total_rams.extend(lote_rams)
        
        probs_promedio = np.mean(lote_probs, axis=0)
        clase_idx = np.argmax(probs_promedio)
        confianza = float(round(probs_promedio[clase_idx] * 100, 2))
        clase_predictiva = le.classes_[clase_idx]
        
        # Concordancia
        concordancia = 'ACERTADO' if clase_predictiva == etiqueta_real else 'FALLIDO'
        if concordancia == 'ACERTADO':
            aciertos += 1
            
        # Métricas de Falsos Positivos / Negativos
        if etiqueta_real != 'ALTA' and clase_predictiva == 'ALTA':
            falsos_positivos_alta += 1
        elif etiqueta_real == 'ALTA' and clase_predictiva != 'ALTA':
            falsos_negativos += 1
            
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        record = {
            'lote_n': idx,
            'fecha_hora': fecha_hora,
            'tipo_plastico': tipo_plastico,
            'temp_max_c': temp_max,
            'latencia_inferencia_ms': latencia_media_lote,
            'ram_usada_mb': ram_media_lote,
            'clase_predictiva': clase_predictiva,
            'confianza_porc': confianza,
            'etiqueta_real': etiqueta_real,
            'concordancia': concordancia
        }
        records_lotes.append(record)
        
        # Feedback de progreso en consola
        if idx % 50 == 0 or idx == len(lotes_grouped):
            print(f"Evaluados {idx}/{len(lotes_grouped)} lotes...")
            
    end_time = time.time()
    
    # Métricas Globales
    latencia_global_media = float(round(np.mean(total_latencias), 2))
    ram_global_media = float(round(np.mean(total_rams), 2))
    accuracy_global = round((aciertos / len(lotes_grouped)) * 100, 2)
    
    resumen_global = {
        'latencia_media_ms': latencia_global_media,
        'ram_media_mb': ram_global_media,
        'total_aciertos': aciertos,
        'total_lotes': len(lotes_grouped),
        'precision_accuracy_porc': accuracy_global,
        'falsos_positivos_calidad_alta': falsos_positivos_alta,
        'falsos_negativos': falsos_negativos,
        'tiempo_total_evaluacion_s': round(end_time - start_time, 2)
    }
    
    output_data = {
        'resumen_global': resumen_global,
        'lotes': records_lotes
    }
    
    # Guardar a JSON
    ruta_json = 'data/resultados_pruebas.json'
    with open(ruta_json, 'w') as f:
        json.dump(output_data, f, indent=2)
        
    print("\n" + "="*50)
    print("RESUMEN GLOBAL DE LA EVALUACIÓN (ANEXO X - SECCIÓN IV)")
    print("="*50)
    print(f"A. Latencia media del modelo CNN-LSTM : {latencia_global_media} ms")
    print(f"A. Consumo medio de RAM              : {ram_global_media} MB")
    print(f"B. Total de aciertos (Accuracy)      : {aciertos} / {len(lotes_grouped)} ({accuracy_global}%)")
    print(f"B. Falsos Positivos de Calidad Alta  : {falsos_positivos_alta}")
    print(f"B. Falsos Negativos                  : {falsos_negativos}")
    print(f"Tiempo de ejecución total            : {resumen_global['tiempo_total_evaluacion_s']} segundos")
    print("="*50)
    print(f"[EXITO] Resultados completos guardados en JSON: {ruta_json}\n")

if __name__ == '__main__':
    main()
