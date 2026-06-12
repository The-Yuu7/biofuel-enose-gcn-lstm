# Nariz Electrónica Inteligente (E-Nose) para el Análisis y Control de Calidad de Bio-oil

Este repositorio contiene la implementación del sistema de **Nariz Electrónica (E-Nose) basado en Aprendizaje Profundo Espacio-Temporal (GCN-LSTM)** para la clasificación de calidad y diagnóstico físico-químico en tiempo real de bio-oil (aceite pirolítico) obtenido de la pirólisis de residuos plásticos.

Desarrollado por **Junior Quispe Aquino** (Universidad Continental, Huancayo), este proyecto transiciona de datos simulados a **datos reales utilizando gasolina de 90 octanos como patrón de referencia de calidad estándar**.

---

## 📌 Concepto Central: Gasolina 90 como Referencia

La gasolina de 90 octanos cuenta con una composición química conocida y altamente estable. Al exponer nuestro arreglo de sensores MOS a sus vapores, se captura una **"firma química de referencia"** (huella digital olfativa). 

La calidad del bio-oil se determina a partir de su similitud multidimensional con esta referencia:
1. **Gasolina 90**: Muestra de calibración y referencia de "calidad perfecta".
2. **Bio-oil Similar**: Perfil sensorial muy parecido a la gasolina 90 (alta calidad).
3. **Bio-oil Intermedio**: Perfil sensorial con desviaciones notables de rango medio (calidad media).
4. **Bio-oil Diferente**: Perfil sensorial muy distante a la gasolina 90 (baja calidad).

---

## 🏗️ Arquitectura del Modelo: GCN-LSTM

El modelo híbrido de aprendizaje profundo combina la extracción de características espaciales del arreglo de sensores mediante una **Red Convolucional en Grafos (GCN)** y la modelación de dependencias temporales mediante **Memoria a Corto y Largo Plazo (LSTM)**.

```
                  ┌──────────────────────────────┐
                  │ Ventana Temporal (30s x 8)   │ (Lecturas de sensores)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │  Graph Convolutional (GCN)  │ -> Modela relaciones químicas entre sensores
                  └──────────────┬───────────────┘    y compensa temperatura y humedad.
                                 ▼
                  ┌──────────────────────────────┐
                  │    LSTM Capa 1 (64 units)    │ -> Captura la dinámica temporal de la 
                  └──────────────┬───────────────┘    acumulación de gases.
                                 ▼
                  ┌──────────────────────────────┐
                  │    LSTM Capa 2 (32 units)    │ -> Reducción y regularización (Dropout 0.3)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ Capa Densa (Softmax Output)  │ -> Clasificación de Calidad: 3 o 4 Clases
                  └──────────────────────────────┘
```

### El Grafo de Sensores (Compensación de Deriva Ambiental)
El grafo de adyacencia se define en [gcn_lstm.py](file:///d:/PROYECTO%20DE%20INVESTIGACION/model/gcn_lstm.py) basándose en las correlaciones físico-químicas del hardware:
* Los sensores químicos de gas (**MQ2, MQ4, MQ135, MQ3, MQ7, MQ9**) se interconectan según su sensibilidad cruzada.
* **Compensación Ambiental Activa:** Los sensores físicos de **temperatura** y **humedad** actúan como nodos directores interconectados con los sensores químicos más propensos a la deriva (MQ2, MQ4, MQ135, MQ7). Esto permite a la GCN aprender coeficientes de corrección cruzada en cada paso temporal.

---

## 📚 Fundamentación Científica en 5 Estados del Arte (SOTA)

El diseño del modelo de Deep Learning y el pipeline físico-químico están basados en 5 investigaciones del estado del arte:

### 1. Modelado Espacio-Temporal en Narices Electrónicas
* **Referencia:** *Yuan et al. (2025). International Journal of Computational Intelligence Systems (DOI: 10.1007/s44196-025-00913-5)*.
* **Aporte:** Implementaron un marco híbrido GCN-LSTM con un arreglo de 16 sensores MOS para reconocer las 3 etapas de pirólisis del esquisto bituminoso. Reportaron una exactitud de clasificación promedio del **93.87%**.
* **Integración:** Adoptamos la arquitectura GCN-LSTM. La GCN procesa las adyacencias del arreglo sensorial y la LSTM mapea la evolución temporal de la curva de respuesta de gases, superando las limitaciones de los clasificadores estáticos tradicionales.

### 2. Compensación y Calibración Térmica Activa
* **Referencia:** *Wu et al. (2020). Sensors (DOI: 10.3390/s20071817)*.
* **Aporte:** Demostraron que la exactitud de una nariz electrónica MOS al clasificar líquidos inflamables (incluyendo gasolina) cae catastróficamente del **100% al 39%** si no se compensa la temperatura ambiente.
* **Integración:** Integramos variables exógenas térmicas y de humedad directa en el grafo convolucional. La GCN propaga esta información ambiental hacia los nodos de los sensores químicos en cada capa de convolución, aislando las derivas por clima en Huancayo.

### 3. Selección y Extracción de Atributos Críticos (Soft-Sensing)
* **Referencia:** *Wang et al. (2025). Results in Engineering (DOI: 10.1016/j.rineng.2025.105967)*.
* **Aporte:** Propusieron un modelo CNN-LSTM integrado con selección de variables mediante Información Mutua (MI) para la predicción de parámetros del gas de pirólisis en reactores acoplados pequeños, incrementando el coeficiente de determinación ($R^2$ hasta 0.96) y reduciendo el sobreajuste.
* **Integración:** Usamos PCA en [analizar_similitud.py](file:///d:/PROYECTO%20DE%20INVESTIGACION/data/analizar_similitud.py) para filtrar la redundancia de los 8 canales. Adicionalmente, el módulo de inferencia aísla desviaciones químicas (Z-score) sensor por sensor para evaluar qué canales aportan la mayor varianza respecto al patrón.

### 4. Segmentación del Perfil y Diagnóstico Temprano
* **Referencia:** *Chen et al. (2026). Scientific Reports (DOI: 10.1038/s41598-025-30436-0)*.
* **Aporte:** Utilizaron PCA-SVM para detectar etapas de combustión de carbón e identificaron compuestos como acetaldehído y benceno como indicadores clave correlacionados con la temperatura del material.
* **Integración:** Estructuramos una función de distancia basada en el clúster PCA de la gasolina 90. Esto proporciona una fundamentación matemática para clasificar bio-oils y diagnosticar cuáles sensores desvían el perfil general.

### 5. Química de la Pirólisis de Plásticos mixtos (PP/PS/HDPE)
* **Referencia:** *Muhbat et al. (2026). Periodica Polytechnica Chemical Engineering (DOI: 10.3311/PPch.42704)*.
* **Aporte:** Investigaron la co-pirólisis de mezclas PP/PS/HDPE (1:1:1), analizando el impacto de la temperatura (350–470 °C) en el rendimiento líquido (hasta 95%) y la distribución de fracciones combustibles tipo gasolina o queroseno.
* **Integración:** Usamos estos datos operativos para diseñar nuestro módulo de alertas físicas en [inferencia_con_diagnostico.py](file:///d:/PROYECTO%20DE%20INVESTIGACION/inferencia_con_diagnostico.py). Las temperaturas bajas o materias primas impuras generan desviaciones específicas en MQ3 (alcoholes/oxigenados) y MQ7 (monóxido de carbono), permitiendo asociar la señal eléctrica a fallas del reactor.

---

## 📁 Estructura del Código

* 📂 **`data/`**
  * [`leer_esp32.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/data/leer_esp32.py): Captura de experimentos de 60 segundos desde el puerto serie del hardware.
  * [`analizar_similitud.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/data/analizar_similitud.py): PCA, etiquetado por distancias euclidianas a la gasolina 90 y generación de mapas de clusters.
  * `datos_reales.csv`: Dataset crudo recopilado por el ESP32.
  * `datos_etiquetados.csv`: Dataset de series temporales completas etiquetado con las clases de calidad.
* 📂 **`preprocessing/`**
  * [`preprocesar.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/preprocessing/preprocesar.py): Pipeline de limpieza, normalización Z-score y segmentación por ventanas robustas.
* 📂 **`model/`**
  * [`gcn_lstm.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/model/gcn_lstm.py): Definición de la red GCN-LSTM en Keras 3.
  * `mejor_modelo.keras`: Pesos del modelo entrenado.
  * `enose_modelo.tflite`: Modelo optimizado sin control flow para microcontroladores y Raspberry Pi.
  * `scaler.pkl`: StandardScaler entrenado.
  * `label_encoder.pkl`: LabelEncoder de las clases de calidad.
  * `perfil_referencia.pkl`: Perfil normalizado promedio de la gasolina 90.
* [`train.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/train.py): Script principal para el preprocesamiento, entrenamiento de 60 épocas y exportación del modelo.
* [`inferencia_con_diagnostico.py`](file:///d:/PROYECTO%20DE%20INVESTIGACION/inferencia_con_diagnostico.py): Inferencia en tiempo real con diagnóstico físico-químico comparado contra la gasolina 90.

---

## 🚀 Guía de Uso Rápido

### Paso 1: Recolección de Datos
Conecta el ESP32 a la PC y ejecuta:
```bash
python data/leer_esp32.py
```
Selecciona el tipo de muestra a ingresar en la cámara de sensores (Graba archivos con 60 lecturas de 1s cada una).

### Paso 2: Análisis de Similitud y Etiquetado
Ejecuta el análisis visual de clusters y genera el mapa de similitud:
```bash
python data/analizar_similitud.py
```
*Si no dispones del hardware conectado, este script autogenerará un dataset real de simulación basado en curvas físicas para validar el flujo.*

### Paso 3: Entrenamiento del Modelo GCN-LSTM
Entrena el modelo y expórtalo a TensorFlow Lite ejecutando:
```bash
python train.py
```
Las curvas de pérdida y precisión se guardarán en `model/curvas_entrenamiento.png`.

### Paso 4: Inferencia en Tiempo Real y Diagnóstico
Para iniciar el monitoreo de calidad del bio-oil en tiempo real (modo simulación o puerto serial):
```bash
python inferencia_con_diagnostico.py --sim
```
Al finalizar cada ventana de 30 segundos, el sistema mostrará la calidad predicha, el porcentaje de confianza y las **alertas de desviaciones físico-químicas** de los sensores MOS frente a la gasolina de referencia.
