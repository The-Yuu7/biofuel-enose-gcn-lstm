import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "registros_gasolina_50.csv")

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Rutas de salida para los artefactos reales
MODEL_DIR = os.path.join(BASE_DIR, "modelo_exportado")
os.makedirs(MODEL_DIR, exist_ok=True)

SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
PERFIL_PATH = os.path.join(MODEL_DIR, "perfil_referencia.pkl")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
TFLITE_PATH = os.path.join(MODEL_DIR, "enose_modelo.tflite")

SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']

def entrenar_y_generar_perfil_real():
    print("======================================================================")
    print("   GENERADOR DE PERFIL DE REFERENCIA REAL Y ENTRENAMIENTO DE MODELO")
    print("======================================================================")
    
    csv_files = [
        os.path.join(BASE_DIR, "registros_grifo_1.csv"),
        os.path.join(BASE_DIR, "registros_grifo_2.csv"),
        os.path.join(BASE_DIR, "registros_grifo_3.csv"),
        CSV_FILE
    ]

    dfs = []
    for cf in csv_files:
        if os.path.exists(cf) and os.path.getsize(cf) > 50:
            try:
                temp_df = pd.read_csv(cf)
                if not temp_df.empty:
                    dfs.append(temp_df)
            except Exception:
                pass

    if not dfs:
        print(f"❌ [ERROR] No se encontraron archivos de muestras válidos en {BASE_DIR}.")
        print("   Ejecute primero 'python capturar_muestra_real.py' para registrar las muestras.")
        return

    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    if df.empty:
        print("❌ [ERROR] El dataset de registros está vacío.")
        return

    muestras_unicas = df['muestra_id'].unique()
    total_muestras = len(muestras_unicas)

    print(f"📊 Leídas {len(df)} filas correspondientes a {total_muestras} muestras reales.")

    # Conteo por grifo
    if 'origen_grifo' in df.columns:
        conteo_grifos = df.groupby('origen_grifo')['muestra_id'].nunique()
        print("\n  Desglose por origen:")
        for g, count in conteo_grifos.items():
            print(f"    - {g}: {count} muestras")

    if total_muestras < 5:
        print(f"\n⚠️ [ADVERTENCIA] Se recomiendan al menos 50 muestras. Actualmente hay solo {total_muestras}.")
        resp = input("¿Desea continuar la generación con las muestras actuales? (s/n): ").strip().lower()
        if resp != 's':
            print("Operación cancelada.")
            return

    # Extraer matrices (N_muestras, 30 timesteps, 8 canales)
    matrices = []
    for m_id in muestras_unicas:
        sub_df = df[df['muestra_id'] == m_id].sort_values('timestep')
        vals = sub_df[SENSORES].values
        if len(vals) == 30:
            matrices.append(vals)
        else:
            print(f"⚠️ Muestra {m_id} incompleta ({len(vals)}/30 timesteps). Ignorando...")

    if not matrices:
        print("❌ [ERROR] Ninguna muestra contiene los 30 timesteps completos.")
        return

    matrices = np.array(matrices) # Shape: (N, 30, 8)
    print(f"\n✅ Matriz acumulada de calibración: {matrices.shape} (Muestras x 30s x 8 sensores)")

    # 1. Crear y ajustar el Escalador StandardScaler con los datos físicos reales
    flat_data = matrices.reshape(-1, 8)
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(flat_data)
    matrices_scaled = data_scaled.reshape(matrices.shape)

    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"💾 [1/4] Escalador físico guardado en: {SCALER_PATH}")

    # 2. Calcular el Perfil de Referencia Óptimo (Promedio de las 50 muestras de gasolina comercial)
    perfil_referencia = np.mean(matrices_scaled, axis=0) # Shape: (30, 8)
    with open(PERFIL_PATH, 'wb') as f:
        pickle.dump(perfil_referencia, f)
    print(f"💾 [2/4] Perfil de referencia (Gasolina Comercial) guardado en: {PERFIL_PATH}")

    # 3. Label Encoder genérico para las 3 clases de calidad
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.fit(['ALTA', 'MEDIA', 'BAJA'])
    with open(LABEL_ENCODER_PATH, 'wb') as f:
        pickle.dump(le, f)
    print(f"💾 [3/4] Label Encoder guardado en: {LABEL_ENCODER_PATH}")

    # 4. Exportar / Copiar el modelo TFLite
    # Copiar el modelo base entrenado a la carpeta de salida
    root_model_tflite = os.path.join(BASE_DIR, "..", "model", "enose_modelo.tflite")
    if os.path.exists(root_model_tflite):
        import shutil
        shutil.copy(root_model_tflite, TFLITE_PATH)
        print(f"💾 [4/4] Modelo TFLite de inferencia guardado en: {TFLITE_PATH}")
    else:
        print("⚠️ No se encontró el binario .tflite base en /model/. Copie manualmente enose_modelo.tflite.")

    # Resumen de lecturas promediadas
    raw_means = np.mean(flat_data, axis=0)
    print("\n======================================================================")
    print("        RESUMEN DE FIRMA QUÍMICA PATRÓN DE LA GASOLINA COMERCIAL")
    print("======================================================================")
    for i, s in enumerate(SENSORES):
        unit = "ADC" if i < 6 else ("°C" if s == "temp" else "%")
        print(f"  - {s:<8}: {raw_means[i]:>10.2f} {unit}")
    print("======================================================================")
    print("🎉 ¡PROCESO DE CALIBRACIÓN COMPLETADO CON ÉXITO!")
    print(f"  Copie la carpeta '{MODEL_DIR}' a su Raspberry Pi en:")
    print("  ~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/model/")
    print("======================================================================")

if __name__ == "__main__":
    entrenar_y_generar_perfil_real()
