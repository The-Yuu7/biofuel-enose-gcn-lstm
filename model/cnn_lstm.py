import numpy as np
import tensorflow as tf
import keras

TIMESTEPS = 30
N_FEATURES = 8

def build_cnn_lstm_model(input_shape=(TIMESTEPS, N_FEATURES), num_classes=3):
    """
    Construye y compila el modelo funcional CNN-LSTM para la Nariz Electrónica.
    La CNN (Conv1D) extrae características espaciales del arreglo de sensores en cada timestep,
    y la LSTM modela la dinámica temporal de la acumulación de gases.
    """
    inputs = keras.Input(shape=input_shape, name="input_sensor_sequence")
    
    # 1. Capa de Convolución 1D para extraer características y correlaciones de los sensores (espaciales)
    x = keras.layers.Conv1D(filters=32, kernel_size=3, padding="same", activation="relu", name="conv1d_spatial_1")(inputs)
    x = keras.layers.BatchNormalization(name="batch_norm_1")(x)
    
    x = keras.layers.Conv1D(filters=64, kernel_size=3, padding="same", activation="relu", name="conv1d_spatial_2")(x)
    x = keras.layers.BatchNormalization(name="batch_norm_2")(x)
    
    # 2. Capas LSTM para patrones temporales de adsorción de gases
    # Usamos unroll=True para simplificar la compatibilidad con microcontroladores / Raspberry Pi (TFLite)
    x = keras.layers.LSTM(64, return_sequences=True, unroll=True, name="lstm_temporal_1")(x)
    x = keras.layers.Dropout(0.3, name="dropout_1")(x)
    
    x = keras.layers.LSTM(32, return_sequences=False, unroll=True, name="lstm_temporal_2")(x)
    x = keras.layers.Dropout(0.3, name="dropout_2")(x)
    
    # 3. Clasificación de calidad
    x = keras.layers.Dense(32, activation='relu', name="dense_dense")(x)
    outputs = keras.layers.Dense(num_classes, activation='softmax', name="softmax_output")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="CNN_LSTM_ENOSE")
    return model

if __name__ == "__main__":
    print("Inicializando modelo CNN-LSTM para prueba de arquitectura...")
    model = build_cnn_lstm_model()
    model.summary()
