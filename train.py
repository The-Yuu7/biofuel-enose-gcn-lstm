import os
import matplotlib
matplotlib.use('Agg')  # Evitar problemas de visualización en ejecución sin GUI
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import keras
import pickle

from preprocessing.preprocesar import load_and_preprocess_data
from model.cnn_lstm import build_cnn_lstm_model

def main():
    print("Fase 4: Entrenamiento y Evaluación del Modelo CNN-LSTM (ADS1115 16-bit)\n")
    
    # 1. Cargar y preprocesar los datos
    csv_path = "data/datos_etiquetados.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Primero ejecuta data/analizar_similitud.py para etiquetar los datos reales en '{csv_path}'")
        
    print("Cargando y dividiendo el dataset...")
    X_train, X_val, X_test, y_train, y_val, y_test, le = load_and_preprocess_data(csv_path=csv_path)
    print(f"Set de Entrenamiento: {X_train.shape[0]} muestras")
    print(f"Set de Validación:    {X_val.shape[0]} muestras")
    print(f"Set de Prueba:        {X_test.shape[0]} muestras\n")
    
    # Determinar el número de clases dinámicamente (debe ser 3: ALTA, MEDIA, BAJA)
    num_classes = len(le.classes_)
    print(f"Número de clases detectadas: {num_classes} -> {list(le.classes_)}\n")
    
    # Exportar perfil de referencia (promedio de la clase 'ALTA' - combustión limpia)
    try:
        ref_class_idx = list(le.classes_).index('ALTA')
        ref_windows = X_train[y_train == ref_class_idx]
        if len(ref_windows) > 0:
            # Promediar sobre todas las ventanas y pasos de tiempo
            perfil_referencia = np.mean(ref_windows, axis=(0, 1))
            perfil_ref_path = os.path.join("model", "perfil_referencia.pkl")
            with open(perfil_ref_path, 'wb') as f:
                pickle.dump(perfil_referencia, f)
            print(f"Perfil de referencia (ALTA) guardado en '{perfil_ref_path}'")
        else:
            print("[WARN] No se encontraron ventanas para la clase 'ALTA' en el conjunto de entrenamiento.")
    except ValueError:
        print("[WARN] No se encontró la clase 'ALTA' en las etiquetas. No se pudo exportar el perfil de referencia.")
    
    # 2. Construir la arquitectura del modelo CNN-LSTM
    print("\nConstruyendo el modelo CNN-LSTM...")
    model = build_cnn_lstm_model(input_shape=(30, 8), num_classes=num_classes)
    
    # Compilar el modelo
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # 3. Definir Callbacks para el entrenamiento
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    # 4. Entrenar el modelo
    print("Iniciando entrenamiento del modelo...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=60,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )
    
    # 5. Evaluar en el conjunto de prueba
    print("\nEvaluando modelo en el conjunto de prueba...")
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Pérdida en Test:  {test_loss:.4f}")
    print(f"Precisión (Accuracy) en Test: {test_acc * 100:.2f}%")
    
    # Reporte de Clasificación detallado y cálculo de F1-Score y AUC-ROC
    from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
    
    y_pred_prob = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_prob, axis=1)
    
    # F1-Score (macro average)
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    # AUC-ROC (One-vs-Rest, macro average)
    auc_roc = roc_auc_score(y_test, y_pred_prob, multi_class='ovr', average='macro')
    
    print("\n" + "="*50)
    print("MÉTRICAS DE LA MATRIZ DE OPERACIONALIZACIÓN (Dimensión 3)")
    print(f"  * Precisión / Accuracy: {test_acc * 100:.2f}%")
    print(f"  * F1-Score (Macro):      {macro_f1 * 100:.2f}%")
    print(f"  * AUC-ROC:               {auc_roc:.4f}")
    print("="*50 + "\n")
    
    print("Reporte de Clasificación:")
    target_names = list(le.classes_)
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    print("Matriz de Confusión:")
    print(confusion_matrix(y_test, y_pred))
    
    # Guardar métricas en un txt para verificación directa
    metrics_path = os.path.join("model", "metricas_evaluacion.txt")
    with open(metrics_path, 'w') as f:
        f.write(f"Accuracy: {test_acc * 100:.2f}%\n")
        f.write(f"F1-Score (Macro): {macro_f1 * 100:.2f}%\n")
        f.write(f"AUC-ROC: {auc_roc:.4f}\n")
    print(f"Métricas textuales guardadas en '{metrics_path}'")
    
    # 6. Graficar y guardar curvas de entrenamiento
    print("\nGraficando curvas de entrenamiento...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Pérdida
    ax1.plot(history.history['loss'], label='Entrenamiento', color='#1f77b4', linewidth=2)
    ax1.plot(history.history['val_loss'], label='Validación', color='#ff7f0e', linewidth=2)
    ax1.set_title('Pérdida (Loss) del Modelo', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Época')
    ax1.set_ylabel('Pérdida')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend()
    
    # Precisión
    ax2.plot(history.history['accuracy'], label='Entrenamiento', color='#2ca02c', linewidth=2)
    ax2.plot(history.history['val_accuracy'], label='Validación', color='#d62728', linewidth=2)
    ax2.set_title('Precisión (Accuracy) del Modelo', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Época')
    ax2.set_ylabel('Precisión')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend()
    
    plt.tight_layout()
    plot_path = "model/curvas_entrenamiento.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"Gráficas de curvas de entrenamiento guardadas en '{plot_path}'")
    
    # 7. Guardar el modelo entrenado en formato nativo Keras
    model_keras_path = "model/mejor_modelo.keras"
    model.save(model_keras_path)
    print(f"Modelo completo guardado en '{model_keras_path}'")
    
    # 8. Exportar a formato TensorFlow Lite
    print("\nExportando modelo a TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    model_tflite_path = "model/enose_modelo.tflite"
    with open(model_tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"Modelo TFLite guardado en '{model_tflite_path}'")
    
    print("\nFase 4 completada con éxito.")

if __name__ == "__main__":
    main()
