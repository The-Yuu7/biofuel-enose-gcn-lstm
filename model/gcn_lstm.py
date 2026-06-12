import numpy as np
import tensorflow as tf
import keras

# Definición de parámetros estáticos del grafo de sensores
N_NODES = 8
TIMESTEPS = 30
CHANNELS_GCN = 4  # Canales de salida por nodo en la convolución del grafo

def compute_normalized_adjacency():
    """
    Construye y normaliza la matriz de adyacencia según el diseño físico-químico:
    Nodos:
      0: MQ2, 1: MQ4, 2: MQ135, 3: MQ3, 4: MQ7, 5: MQ9, 6: temp, 7: humedad
    """
    A = np.zeros((N_NODES, N_NODES), dtype=np.float32)
    connections = [
        (0, 1), (1, 5), # MQ2 -- MQ4 -- MQ9
        (4, 1),         # MQ7 -- MQ4
        (2, 3),         # MQ135 -- MQ3
        # temp afecta a MQ2, MQ4, MQ135, MQ7
        (6, 0), (6, 1), (6, 2), (6, 4),
        # humedad afecta a MQ2, MQ135
        (7, 0), (7, 2)
    ]
    for i, j in connections:
        A[i, j] = 1.0
        A[j, i] = 1.0
        
    # Añadir self-loops
    A_tilde = A + np.eye(N_NODES, dtype=np.float32)
    
    # Calcular matriz de grados D_tilde
    degrees = np.sum(A_tilde, axis=1)
    
    # D_tilde^-0.5
    d_inv_sqrt = np.power(degrees, -0.5)
    d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.0
    D_inv_sqrt = np.diag(d_inv_sqrt)
    
    # A_hat = D^-0.5 * A_tilde * D^-0.5
    A_hat = D_inv_sqrt.dot(A_tilde).dot(D_inv_sqrt).astype(np.float32)
    return A_hat

# Generar la matriz normalizada A_hat para pasársela a la capa
A_HAT_CONST = compute_normalized_adjacency()

@keras.saving.register_keras_serializable(package="E_Nose_Layers")
class StaticGCNConv(keras.layers.Layer):
    """
    Capa de Convolución en Grafos estática nativa de Keras 3.
    Realiza la operación: Z = A_hat * X * W + b
    """
    def __init__(self, channels, A_hat, activation=None, **kwargs):
        super().__init__(**kwargs)
        self.channels = channels
        self.A_hat = tf.constant(A_hat, dtype=tf.float32)
        self.dense = keras.layers.Dense(channels, use_bias=True)
        self.activation = keras.activations.get(activation)

    def call(self, inputs):
        # inputs shape: (batch_size * timesteps, N_NODES, features)
        # 1. Transformación lineal de características por cada nodo (X * W)
        h = self.dense(inputs)  # (batch_size * timesteps, N_NODES, channels)
        # 2. Multiplicación de la matriz de adyacencia normalizada por la izquierda
        # tf.matmul propaga sobre el primer eje (batch_size * timesteps) automáticamente
        out = tf.matmul(self.A_hat, h)  # (batch_size * timesteps, N_NODES, channels)
        
        if self.activation is not None:
            out = self.activation(out)
        return out

    def get_config(self):
        config = super().get_config()
        config.update({
            "channels": self.channels,
            "A_hat": self.A_hat.numpy().tolist()
        })
        return config

@keras.saving.register_keras_serializable(package="E_Nose_Layers")
class GCNPrepLayer(keras.layers.Layer):
    """
    Capa auxiliar para aplanar la dimensión temporal al formato esperado por el GCN.
    Reshapes (batch, 30, 8) -> (batch * 30, 8, 1)
    """
    def call(self, inputs):
        shape = tf.shape(inputs)
        batch_size = shape[0]
        # X_input tiene 8 sensores por timestep, lo tratamos como 8 nodos con 1 característica cada uno
        return tf.reshape(inputs, (batch_size * TIMESTEPS, N_NODES, 1))

@keras.saving.register_keras_serializable(package="E_Nose_Layers")
class GCNPostLayer(keras.layers.Layer):
    """
    Capa auxiliar para restaurar el formato secuencial tras el GCN para la capa LSTM.
    Reshapes (batch * 30, 8, channels) -> (batch, 30, 8 * channels)
    """
    def call(self, inputs):
        shape = tf.shape(inputs)
        # El batch size original se recupera dividiendo por el número de timesteps
        batch_size = shape[0] // TIMESTEPS
        return tf.reshape(inputs, (batch_size, TIMESTEPS, N_NODES * CHANNELS_GCN))

def build_gcn_lstm_model(input_shape=(TIMESTEPS, N_NODES), num_classes=3):
    """
    Construye y compila el modelo funcional GCN-LSTM.
    """
    inputs = keras.Input(shape=input_shape, name="input_sensor_sequence")
    
    # 1. Adaptar secuencia para GCN
    x = GCNPrepLayer()(inputs)
    
    # 2. Capa GCN (Aprende correlaciones espaciales/químicas en cada paso temporal)
    x = StaticGCNConv(channels=CHANNELS_GCN, A_hat=A_HAT_CONST, activation='relu')(x)
    
    # 3. Restaurar dimensión secuencial para la LSTM
    x = GCNPostLayer()(x)
    
    # 4. Capas LSTM para patrones temporales
    x = keras.layers.LSTM(64, return_sequences=True, unroll=True, name="lstm_temporal_1")(x)
    x = keras.layers.Dropout(0.3, name="dropout_1")(x)
    
    x = keras.layers.LSTM(32, return_sequences=False, unroll=True, name="lstm_temporal_2")(x)
    x = keras.layers.Dropout(0.3, name="dropout_2")(x)
    
    # 5. Capa Densa y salida de clasificación
    x = keras.layers.Dense(32, activation='relu', name="dense_dense")(x)
    outputs = keras.layers.Dense(num_classes, activation='softmax', name="softmax_output")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs, name="GCN_LSTM_ENOSE")
    return model

if __name__ == "__main__":
    print("Inicializando modelo GCN-LSTM para prueba de arquitectura...")
    model = build_gcn_lstm_model()
    model.summary()
