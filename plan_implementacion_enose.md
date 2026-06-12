# Plan de Implementación: Sistema de Nariz Electrónica Basado en Deep Learning
## Para el Control de Calidad del Biocombustible Producido por Pirólisis de Residuos Plásticos

**Autor:** Junior Quispe Aquino  
**Institución:** Universidad Continental — Huancayo, Perú  
**Arquitectura del modelo:** GCN-LSTM  
**Hardware central:** ESP32 NodeMCU + Raspberry Pi 4 (4GB)

---

## Resumen del sistema

El sistema captura las señales de un array de 8 sensores MOS expuestos a los gases del biocombustible producido por pirólisis. Un modelo de deep learning (GCN-LSTM) analiza esas señales para clasificar la calidad del bio-oil en tiempo real. El GCN extrae relaciones espaciales entre sensores; el LSTM extrae patrones temporales de la respuesta.

```
Pirólisis → Gases → Sensores MOS → ESP32 (ADC) → Raspberry Pi 4 → Clasificación
```

---

## Hardware del proyecto

| Componente | Función en el sistema |
|---|---|
| ESP32 NodeMCU | Adquisición: lee ADC y envía datos por serial/UART |
| MCP3008 (ADC externo) | Mejora la precisión del ADC (10-bit, sin ruido de WiFi) |
| MQ-2 | Detecta GLP, butano, propano, humo |
| MQ-4 | Detecta metano (CH4) — marcador de temperatura de pirólisis |
| MQ-135 | Detecta VOCs, benceno, CO2, NH3 — calidad del bio-oil |
| MQ-3 / MQ-8 | Detecta alcoholes e hidrógeno (H2) |
| MQ-7 | Detecta CO — marcador crítico de combustión incompleta |
| MQ-9 | Detecta CO en rangos bajos y GLP |
| DHT22 | Temperatura y humedad — compensación ambiental |
| Raspberry Pi 4 (4GB) | Inferencia del modelo TFLite en tiempo real |
| MicroSD 64 GB | Dataset + modelo entrenado |
| Termopar tipo K + MAX6675 | Temperatura del reactor de pirólisis (hasta 600°C) |
| Pantalla OLED 0.96" | Feedback visual del resultado de clasificación |

---

## Estructura del proyecto (código)

```
PROYECTO DE INVESTIGACION/
├── data/
│   ├── generar_datos.py          ← Fase 1: simula lecturas de sensores
│   └── datos_sensores.csv        ← Dataset (real o simulado)
├── preprocessing/
│   └── preprocesar.py            ← Fase 2: normalización y ventanas
├── model/
│   ├── gcn_lstm.py               ← Fase 3: arquitectura GCN-LSTM
│   ├── mejor_modelo.keras        ← Pesos del modelo entrenado
│   ├── enose_modelo.tflite       ← Modelo exportado para RPi (~74 KB)
│   ├── scaler.pkl                ← Normalizador (necesario en RPi)
│   └── label_encoder.pkl         ← Mapeo número → etiqueta
├── train.py                      ← Fase 4: entrenamiento y evaluación
└── inferencia_rpi.py             ← Fase 5: inferencia en tiempo real
```

---

## Fase 1 — Recolección de datos

### Objetivo
Generar un dataset con lecturas reales de los sensores etiquetadas según la calidad del biocombustible analizada por laboratorio.

### Formato del CSV

```
timestamp, MQ2,  MQ4,  MQ135, MQ3, MQ7,  MQ9,  temp,  humedad, etiqueta
0,         345,  210,  189,   95,  120,   100,  28.5,  62.1,    alta_calidad
1,         348,  212,  191,   97,  122,   103,  28.6,  62.0,    alta_calidad
...
```

### Clases de etiquetado

| Etiqueta | Descripción | Indicadores clave |
|---|---|---|
| `alta_calidad` | Bio-oil apto para uso directo | CO bajo, VOCs controlados |
| `media_calidad` | Requiere refinamiento | CO medio, temperatura inestable |
| `baja_calidad` | No apto / rechazado | CO alto, contaminantes elevados |

### Mínimo recomendado
- 300 experimentos por clase (900 total)
- 30 lecturas por experimento (1 lectura/segundo durante 30s)
- Total: ~27,000 filas en el CSV

### Código del ESP32 (esquema)

```cpp
// En Arduino IDE o MicroPython
// Leer cada sensor cada 1 segundo y enviar por Serial
void loop() {
  int mq2   = analogRead(A0);   // via MCP3008
  int mq4   = analogRead(A1);
  int mq135 = analogRead(A2);
  int mq3   = analogRead(A3);
  int mq7   = analogRead(A4);
  int mq9   = analogRead(A5);
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  Serial.printf("%d,%d,%d,%d,%d,%d,%.1f,%.1f\n",
                mq2,mq4,mq135,mq3,mq7,mq9,temp,hum);
  delay(1000);
}
```

### Consideración importante: deriva de calentamiento
Los sensores MOS tardan ~30-60 segundos en estabilizarse al encenderse. Siempre esperar ese tiempo antes de iniciar la captura de datos de entrenamiento.

---

## Fase 2 — Preprocesamiento

### Pasos aplicados

1. **Cargar CSV con Pandas**
2. **Normalización con `StandardScaler`** — escala cada sensor a media 0, desviación 1. Esto evita que sensores con valores altos (ej. MQ-7: 700) dominen sobre los de valores bajos (ej. DHT22 humedad: 50).
3. **Ventanas de tiempo** — cada experimento de 30 lecturas se convierte en un bloque `(30, 8)` que el LSTM puede procesar como secuencia.
4. **Split de datos** — 70% entrenamiento / 15% validación / 15% test.

### Ejecución

```bash
python preprocessing/preprocesar.py
```

### Salidas generadas

| Archivo | Descripción |
|---|---|
| `model/scaler.pkl` | Normalizador — guardar para usarlo en la RPi |
| `model/label_encoder.pkl` | Mapeo 0→alta, 1→baja, 2→media |

---

## Fase 3 — Arquitectura del modelo GCN-LSTM

### ¿Por qué GCN-LSTM y no solo LSTM?

Un LSTM simple trata todos los sensores igual. El GCN permite que el modelo aprenda que algunos sensores están **relacionados entre sí** (por ejemplo, MQ-7 y MQ-9 ambos detectan CO) y que la **temperatura del DHT22 afecta la respuesta de todos los sensores MOS**. Esa información estructural mejora la precisión de clasificación.

### Grafo de sensores

Los nodos son los 8 sensores. Las aristas conectan pares que tienen relación química en el contexto de pirólisis:

```
MQ2 ── MQ4 ── MQ9
 │      │
MQ7 ───┘      MQ135 ── MQ3
 │
temp ── MQ2, MQ4, MQ135, MQ7
hum  ── MQ2, MQ135
```

### Flujo de datos en el modelo

```
Entrada (batch, 30, 8)
    │
    ▼
[GCN Layer]  → combina señales de sensores vecinos en el grafo → (batch, 30, 32)
    │
[LayerNorm]  → estabiliza el entrenamiento
    │
[LSTM 64]    → aprende patrones temporales, secuencia por secuencia → (batch, 30, 64)
    │
[Dropout 0.3]
    │
[LSTM 32]    → condensa la secuencia en un vector de estado → (batch, 32)
    │
[Dropout 0.3]
    │
[Dense 32, ReLU]
    │
[Dense 3, Softmax] → probabilidad de cada clase → (batch, 3)
```

### Parámetros totales del modelo
~37,635 parámetros entrenables — modelo muy ligero, ideal para RPi 4.

### Ejecución

```bash
python model/gcn_lstm.py   # muestra el summary del modelo
```

---

## Fase 4 — Entrenamiento y evaluación

### Configuración de entrenamiento

| Parámetro | Valor | Razón |
|---|---|---|
| Optimizador | Adam (lr=0.001) | Converge rápido en redes recurrentes |
| Loss | `sparse_categorical_crossentropy` | Clasificación multiclase con enteros |
| Batch size | 32 | Balance entre velocidad y estabilidad |
| Epochs máx. | 60 | EarlyStopping detiene antes si es necesario |
| EarlyStopping | patience=10 | Evita sobreentrenamiento |
| ReduceLROnPlateau | factor=0.5, patience=5 | Reduce lr si val_loss se estanca |

### Métricas de evaluación

- **Accuracy:** porcentaje de predicciones correctas sobre el total
- **Precision por clase:** de todas las que predijo como "alta calidad", ¿cuántas realmente lo eran?
- **Recall por clase:** de todas las muestras reales de "alta calidad", ¿cuántas encontró?
- **F1-score:** media armónica entre precision y recall
- **Matriz de confusión:** muestra exactamente qué clases se confunden entre sí

### Resultados con datos simulados (referencia)

```
Accuracy en test: 100% (datos simulados bien separados)
Convergencia: epoch 11 de 60

              precision  recall  f1-score  support
alta_calidad    1.00     1.00     1.00      60
baja_calidad    1.00     1.00     1.00      60
media_calidad   1.00     1.00     1.00      60
```

Con datos reales de sensores se espera 85–95% según la calidad del etiquetado.

### Ejecución

```bash
python train.py
```

Genera automáticamente:
- `model/mejor_modelo.keras` — mejores pesos según val_accuracy
- `model/curvas_entrenamiento.png` — gráficas de accuracy y loss
- `model/enose_modelo.tflite` — modelo exportado para RPi

---

## Fase 5 — Despliegue en Raspberry Pi 4

### Archivos a copiar a la RPi

```bash
scp model/enose_modelo.tflite  pi@<ip-rpi>:~/enose/
scp model/scaler.pkl           pi@<ip-rpi>:~/enose/
scp model/label_encoder.pkl    pi@<ip-rpi>:~/enose/
scp inferencia_rpi.py          pi@<ip-rpi>:~/enose/
```

### Instalación en la RPi

```bash
pip install tflite-runtime numpy scikit-learn pyserial pickle5
```

### Script de inferencia en tiempo real

```python
# inferencia_rpi.py
import numpy as np
import pickle
import serial
import tflite_runtime.interpreter as tflite

SENSORES     = ['MQ2','MQ4','MQ135','MQ3','MQ7','MQ9','temp','humedad']
PASOS_TIEMPO = 30
CLASES       = {0: 'ALTA CALIDAD', 1: 'BAJA CALIDAD', 2: 'MEDIA CALIDAD'}

# Cargar modelo y preprocesadores
interpreter = tflite.Interpreter(model_path='enose_modelo.tflite')
interpreter.allocate_tensors()
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

with open('scaler.pkl','rb') as f:       scaler = pickle.load(f)
with open('label_encoder.pkl','rb') as f: le    = pickle.load(f)

# Leer del ESP32 por serial
ser    = serial.Serial('/dev/ttyUSB0', 115200)
buffer = []

print("Sistema listo. Esperando datos del ESP32...")

while True:
    linea = ser.readline().decode().strip()
    valores = list(map(float, linea.split(',')))
    buffer.append(valores)

    if len(buffer) == PASOS_TIEMPO:
        ventana = np.array(buffer)                         # (30, 8)
        ventana = scaler.transform(ventana)                # normalizar
        entrada = ventana[np.newaxis, :, :].astype(np.float32)  # (1, 30, 8)

        interpreter.set_tensor(input_details[0]['index'], entrada)
        interpreter.invoke()
        probs = interpreter.get_tensor(output_details[0]['index'])[0]

        clase     = np.argmax(probs)
        confianza = probs[clase] * 100
        print(f"Resultado: {CLASES[clase]}  (confianza: {confianza:.1f}%)")

        buffer = []   # resetear buffer para siguiente muestra
```

### Flujo completo en la RPi

```
ESP32 envía datos por Serial cada 1s
    │
    ▼  (30 lecturas = 30 segundos)
Raspberry Pi acumula ventana (30, 8)
    │
    ▼
Normaliza con scaler.pkl
    │
    ▼
Inferencia TFLite (~5ms por predicción)
    │
    ▼
Muestra resultado en pantalla OLED
```

---

## Dependencias del proyecto

### PC / entorno de entrenamiento

```bash
pip install tensorflow spektral pandas numpy scikit-learn matplotlib
```

| Librería | Versión probada | Uso |
|---|---|---|
| tensorflow | 2.21.0 | Construcción y entrenamiento del modelo |
| spektral | 1.3.1 | Soporte para capas de grafos en Keras |
| pandas | — | Lectura y manipulación del CSV |
| numpy | — | Operaciones matriciales |
| scikit-learn | — | Normalización, métricas, split |
| matplotlib | — | Gráficas de entrenamiento |

### Raspberry Pi 4

```bash
pip install tflite-runtime numpy scikit-learn pyserial
```

---

## Resumen de archivos y su rol

| Archivo | Cuándo ejecutarlo | Qué produce |
|---|---|---|
| `data/generar_datos.py` | Una vez, para practicar | `datos_sensores.csv` simulado |
| `preprocessing/preprocesar.py` | Antes de entrenar | Datos listos + scaler.pkl |
| `model/gcn_lstm.py` | Importado por train.py | Arquitectura del modelo |
| `train.py` | Para entrenar | modelo.keras + .tflite + gráficas |
| `inferencia_rpi.py` | En la RPi, en producción | Clasificación en tiempo real |

---

## Cronograma sugerido

| Semana | Actividad |
|---|---|
| 1–2 | Montar hardware, probar sensores individualmente, escribir script ESP32 |
| 3–4 | Recolectar datos reales etiquetados (mínimo 900 experimentos) |
| 5 | Preprocesamiento y validación del dataset |
| 6 | Entrenamiento, ajuste de hiperparámetros, evaluación |
| 7 | Exportar modelo, desplegar en RPi, prueba de integración |
| 8 | Pruebas con muestras reales, ajuste final, documentación |

---

## Notas importantes

1. **Etiquetado:** la calidad de los datos determina la calidad del modelo. Cada experimento debe tener su etiqueta validada por análisis de laboratorio (cromatografía o análisis de combustión), no solo por criterio visual.

2. **Deriva del sensor:** los sensores MOS cambian su respuesta con el tiempo de uso y la temperatura ambiente. El DHT22 es crítico para compensar esto. Reentrenar el modelo cada cierto tiempo con datos frescos si la precisión baja.

3. **Reproducibilidad:** las semillas `np.random.seed(42)` y `tf.random.set_seed(42)` garantizan que el entrenamiento sea reproducible entre ejecuciones.

4. **Escalar el dataset:** con más de 2,000 muestras por clase conviene agregar una segunda capa GCN y aumentar las unidades LSTM a 128 para aprovechar mejor los datos.

5. **TFLite en RPi:** el archivo `.tflite` incluye operaciones `SELECT_TF_OPS` (para las capas LSTM). Instalar `tflite-runtime` con soporte completo o usar la versión completa de TensorFlow en la RPi si hay problemas.
