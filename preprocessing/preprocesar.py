import os
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

def load_and_preprocess_data(csv_path="data/datos_etiquetados.csv", model_dir="model"):
    # Crear carpeta model si no existe
    os.makedirs(model_dir, exist_ok=True)
    
    # Cargar CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el dataset en '{csv_path}'. Por favor ejecute data/analizar_similitud.py primero.")
        
    df = pd.read_csv(csv_path)
    
    # Columnas
    sensores = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
    
    # 1. Ajustar StandardScaler y transformar las lecturas
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[sensores])
    
    # Guardar scaler
    scaler_path = os.path.join(model_dir, "scaler.pkl")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    # 2. Codificar etiquetas usando clase_calidad (calidad real: ALTA, MEDIA, BAJA)
    le = LabelEncoder()
    df['clase_calidad'] = df['clase_calidad'].astype(str)
    encoded_labels = le.fit_transform(df['clase_calidad'])
    
    # Guardar label encoder
    le_path = os.path.join(model_dir, "label_encoder.pkl")
    with open(le_path, 'wb') as f:
        pickle.dump(le, f)
        
    # Crear un array temporal de características escaladas
    df_scaled = pd.DataFrame(scaled_features, columns=sensores)
    df_scaled['muestra_id'] = df['muestra_id'].values
    df_scaled['label_num'] = encoded_labels
    
    # 3. Ventaneo con solapamiento del 80% (Sliding Window, paso de 6 pts)
    # Tamaño de ventana: 30 segundos, paso/stride: 6 segundos
    X_list = []
    y_list = []
    
    for mid, group in df_scaled.groupby('muestra_id'):
        features = group[sensores].values
        label = group['label_num'].values[0]
        
        # Extraer ventanas de tamaño 30 con paso 6 (80% solapamiento)
        # Para 120s da exactamente 16 ventanas
        for i in range(0, len(features) - 30 + 1, 6):
            X_list.append(features[i:i+30])
            y_list.append(label)
            
    X = np.array(X_list)
    y = np.array(y_list)
    
    # 4. Split del dataset en: 70% Train, 15% Val, 15% Test
    # Usamos stratified split para asegurar proporciones balanceadas de clases
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=42
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=15/85, stratify=y_train_val, random_state=42
    )
    
    return X_train, X_val, X_test, y_train, y_val, y_test, le

if __name__ == "__main__":
    print("Iniciando preprocesamiento...")
    X_train, X_val, X_test, y_train, y_val, y_test, le = load_and_preprocess_data()
    
    print("\nPreprocesamiento completado exitosamente.")
    print(f"Dimensiones de entrenamiento: X_train = {X_train.shape}, y_train = {y_train.shape}")
    print(f"Dimensiones de validación:    X_val   = {X_val.shape}, y_val   = {y_val.shape}")
    print(f"Dimensiones de prueba:        X_test  = {X_test.shape}, y_test  = {y_test.shape}")
    print("\nClases codificadas:")
    for idx, class_name in enumerate(le.classes_):
        print(f"  {idx} -> {class_name}")
    print("\nPreprocesadores guardados en la carpeta 'model/'.")
