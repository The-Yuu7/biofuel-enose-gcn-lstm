# Documentación de Investigación, Estándares ISO y Plan de Pruebas

Este documento detalla la estructura del proyecto, la fundamentación teórica (Estado del Arte), el cumplimiento de las normativas internacionales de calidad de software (**ISO 9001, 25000, 29119 y 27000**), el diseño del sistema y el plan completo de pruebas (Caja Negra, Caja Blanca, Unitarias y de Integración).

---

## 📁 1. Mapeo de Carpetas del Proyecto

A continuación se detalla en qué carpetas y archivos específicos del proyecto se encuentra cada sección requerida por la investigación:

| Requisito de la Investigación | Carpeta / Archivo en el Proyecto | Descripción |
|---|---|---|
| **Estado del Arte** | 📂 [`Estados del Arte/`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/Estados%20del%20Arte)<br>📄 [`README.md#L54-L83`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/README.md#L54-L83) | Contiene los 5 artículos científicos (`.docx`) y su síntesis/integración directa con el modelo de Deep Learning en el README. |
| **Planificación (Plan de Pruebas)** | 📄 [`doc_investigacion_y_pruebas.md`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/doc_investigacion_y_pruebas.md) (este archivo)<br>📂 [`fastapi_server/test_api.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/test_api.py) | Detalle metodológico de las pruebas de caja negra, caja blanca, unitarias y su automatización en código. |
| **Diseño (Mockups / Dashboard)** | 📄 [`fastapi_server/index.html`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/index.html) | Interfaz web interactiva en tiempo real (SCADA/Lab style) que muestra gráficos, tablas de diagnóstico e indicadores. |
| **Desarrollo basado en ISO** | 📄 [`doc_investigacion_y_pruebas.md#4-desarrollo-basado-en-normas-iso`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/doc_investigacion_y_pruebas.md#4-desarrollo-basado-en-normas-iso) (este archivo)<br>📄 [`fastapi_server/sonar-project.properties`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/sonar-project.properties) | Fundamentos de aplicación de ISO 9001 (calidad de gestión), ISO 25000 (calidad de producto), ISO 29119 (pruebas) e ISO 27000 (seguridad). |
| **Mantenimiento (Pruebas Automatizadas)**| 📂 [`fastapi_server/test_api.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/test_api.py)<br>📂 [`data/ejecutar_pruebas_json.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/ejecutar_pruebas_json.py)<br>📄 [`fastapi_server/coverage.xml`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/coverage.xml) | Suites de pruebas automatizadas locales (`pytest`), pruebas de lotes experimentales y reportes de cobertura de código. |
| **Ejecutable para el LCD 16x2** | 📄 [`fastapi_server/lcd_client.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/lcd_client.py) | Cliente ejecutable en Python para Raspberry Pi que se conecta con la API y muestra el estado de calidad (Grados A, B, C) en la pantalla física. |

---

## 📚 2. Estado del Arte del Producto a Implementar

La base científica y tecnológica de esta nariz electrónica se apoya en 5 investigaciones de punta:

1. **Modelado Espacio-Temporal (GCN-LSTM):** *Yuan et al. (2025)*. Implementación de una red convolucional sobre grafos combinada con LSTM para la clasificación de etapas de pirólisis con un 93.87% de exactitud.
2. **Compensación Térmica y Deriva:** *Wu et al. (2020)*. Evidencia que la exactitud de clasificación de combustibles inflamables (como la gasolina) con sensores MOS cae de 100% a 39% si no se compensa la temperatura. En este proyecto se compensa la deriva usando la temperatura/humedad ambiental como nodos directores en el grafo convolucional.
3. **Soft-Sensing y Selección de Atributos:** *Wang et al. (2025)*. Selección de variables para predicción de gases de pirólisis en reactores. Se integra en el análisis de similitud multidimensional y diagnósticos por desviación Z-score.
4. **Segmentación y Diagnóstico de Etapas:** *Chen et al. (2026)*. Uso de PCA y distancias euclidianas a clústeres para detectar anomalías operativas.
5. **Química de la Pirólisis de Plásticos:** *Muhbat et al. (2026)*. Análisis de distribución de productos líquidos (tipo gasolina) en pirólisis de mezclas PP/PS/HDPE a 350-470 °C. Este estudio fundamenta los diagnósticos físico-químicos del biocombustible.

---

## 🎨 3. Diseño y Mockups (Interfaz de Usuario)

El diseño del frontend se encuentra implementado en [index.html](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/index.html). No es un mockup estático de Figma, sino una interfaz real interactiva.

A continuación se muestra el Mockup visual del Dashboard generado por IA que sirvió como base para la interfaz implementada:

![Mockup de la Interfaz Web E-Nose](C:/Users/Asus/.gemini/antigravity/brain/252923e1-46d7-4c01-892a-6aea79152de4/biofuel_dashboard_mockup_1782521644837.png)

### Características del Diseño:
* **Estilo Visual:** Dark mode de nivel SCADA industrial/laboratorio, alejado de diseños genéricos de plantillas web.
* **Componentes visuales:**
  * **Indicador de Calidad en Vivo:** Muestra la predicción actual en formato académico formal (**Grado A - Conforme**, **Grado B - Desviación Media**, **Grado C - No Conforme**) junto con el porcentaje de confianza del modelo.
  * **Panel de Parámetros del Reactor:** Sliders interactivos deshabilitados para evitar manipulación humana, que muestran las lecturas en tiempo real capturadas por los sensores (MQ2, MQ4, MQ135, MQ3, MQ7, MQ9, Temp, Humedad).
  * **Tabla de Análisis de Laboratorio y Diagnóstico:** Identifica qué sensor presenta desviaciones significativas comparado con el patrón de referencia de gasolina de 90 octanos (análisis Z-score) y proporciona recomendaciones automáticas para ajustar el reactor en tiempo real.

---

## 📐 4. Desarrollo Basado en Normas ISO

### A. ISO 9001 (Sistema de Gestión de la Calidad)
* **Control de Procesos:** Estructuración de código modular (datos, preprocesamiento, modelo, servidor, cliente hardware).
* **Trazabilidad:** Registro e historial de experimentos en archivos `.csv` y bitácoras de ejecución.
* **Reproducibilidad:** Fijación de semillas aleatorias (`seed=42`) para garantizar que el entrenamiento del modelo sea reproducible.

### B. ISO/IEC 25000 (SQuaRE - Calidad de Producto de Software)
* **Eficiencia de Rendimiento:** El modelo original en Keras se optimiza convirtiéndolo al formato TensorFlow Lite (`enose_modelo.tflite`), reduciendo la latencia de inferencia a **< 10 ms** y el consumo de RAM a **< 60 MB**, ideal para computadores embebidos como Raspberry Pi.
* **Adecuación Funcional:** Monitoreo y diagnóstico automatizado de lotes experimentales que reportan métricas clave (Accuracy, Falsos Positivos, Latencia) guardados directamente en [resultados_pruebas.json](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/resultados_pruebas.json).

### C. ISO/IEC 29119 (Pruebas de Software)
* **Enfoque en Pruebas:** Implementación de pruebas automatizadas continuas con `pytest` y generación de archivos de cobertura `coverage.xml`.
* **Criterios de Aceptación:** Validación sistemática de estructuras de datos y cobertura de código.

### D. ISO/IEC 27000 (Seguridad de la Información)
* **Validación de Entradas:** Uso de esquemas Pydantic en FastAPI para evitar ataques de inyección de tipos y asegurar que el modelo solo intente procesar matrices con dimensiones válidas `(30, 8)`.
* **Aislamiento:** El backend de inferencia y control está desacoplado del frontend, interactuando únicamente a través de endpoints REST seguros con configuración CORS explícita.

---

## 🧪 5. Planificación y Plan de Pruebas (ISO 29119)

### 5.1 Pruebas de Caja Negra (Black-Box Testing)
Estas pruebas evalúan el comportamiento externo del sistema a nivel funcional (entradas y salidas) sin analizar el código interno o la lógica matemática del modelo.

| ID | Caso de Prueba | Entrada (Input Payload) | Resultado Esperado (Expected Output) | Validación en el Proyecto |
|---|---|---|---|---|
| **CN-01** | Entrada Válida (Lote de Alta Calidad) | Ventana temporal de 30 segundos con lecturas estables muy cercanas al perfil de gasolina 90. | Status 200, predicción: `ALTA` con confianza > 90% y diagnóstico "Excelente calidad". | Probado en `test_api.py:test_predict_alta_optimal` |
| **CN-02** | Entrada Válida (Lote Desviado) | Ventana temporal de 30 segundos donde MQ4 y MQ7 presentan valores superiores al perfil de gasolina 90. | Status 200, predicción: `MEDIA` o `BAJA`, con diagnósticos explícitos para los sensores MQ4 y MQ7. | Probado en `test_api.py:test_predict_deviated` |
| **CN-03** | Ventana Temporal Incompleta | JSON con una lista de solo 10 pasos temporales (se requieren 30). | Status 400 Bad Request, mensaje de error indicando que la ventana debe contener exactamente 30 timesteps. | Probado en `test_api.py:test_predict_invalid_size` |
| **CN-04** | Formato de Sensor Inválido | Envío de valores de sensores que no son numéricos (ej. cadena de texto `"ERROR"` en el MQ2). | Status 422 Unprocessable Entity (FastAPI Pydantic validation error). | Validado de forma nativa por FastAPI / Pydantic schemas |
| **CN-05** | Estado de Salud de la API | Consulta GET al endpoint `/health` | Status 200, JSON con el estado de carga del modelo, scaler y label encoder en `true`. | Probado en `test_api.py:test_health_endpoint` |

---

### 5.2 Pruebas de Caja Blanca (White-Box Testing)
Evalúan la estructura del código interno de la API, el flujo de ejecución lógica y el manejo de excepciones.

* **Análisis de Cobertura de Caminos:**
  * **Flujo de Carga de Archivos (Lifespan):** Se evalúan los caminos donde faltan archivos requeridos (`enose_modelo.tflite`, `scaler.pkl`, `label_encoder.pkl`), verificando que la API lance la excepción correspondiente `FileNotFoundError` y escriba un log crítico.
  * **Normalización de Datos:** Se introduce un bloque `try/except` en `process_prediction` para capturar fallos matemáticos al invocar `scaler.transform(raw_window)`. Si la matriz de entrada contiene infinitos o valores no convertibles, la API interrumpe la ejecución de forma segura y retorna un error 500.
  * **Evaluación del Intérprete TFLite:** Se verifica la asignación de memoria a los tensores de entrada y salida mediante `assets.interpreter.allocate_tensors()` y la ejecución del intérprete `interpreter.invoke()`.
  * **Lógica del Búfer Circular en Memoria:** Se valida la condición lógica en `/sensor_data`: si el tamaño de `app.state.sensor_buffer` es menor a 30, se almacena la muestra y retorna el progreso. Si es igual a 30, ejecuta la predicción y el diagnóstico, y si supera 30, remueve la muestra más antigua (`buffer.pop(0)`) antes de insertar, asegurando que la memoria se mantenga constante.

---

### 5.3 Pruebas Unitarias (Unit Testing)
Se ejecutan a nivel de funciones y rutas REST individuales para comprobar que cada unidad de software funciona de forma independiente.

* **Ubicación de las pruebas unitarias:** Archivo [`fastapi_server/test_api.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/test_api.py).
* **Framework:** `pytest` con el cliente de pruebas `TestClient` de FastAPI.
* **Componentes cubiertos:**
  * Ruta GET `/health`
  * Ruta GET `/` (Frontend Dashboard)
  * Ruta POST `/predict` (Inferencia completa con diagnóstico Z-score y recomendaciones)
  * Ruta POST `/sensor_data` (Ingreso en streaming y lógica de búfer circular)
  * Ruta GET `/latest_result` (Consulta del último estado disponible)

---

### 5.4 Pruebas de Integración y Rendimiento (Batch Performance Testing)
Estas pruebas evalúan cómo se comporta el modelo de aprendizaje profundo integrado con el pipeline físico-químico sobre un lote masivo de datos reales de calibración.

* **Script de ejecución:** [`data/ejecutar_pruebas_json.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/ejecutar_pruebas_json.py).
* **Funcionamiento:** Carga el dataset completo de 450 experimentos reales y ejecuta una ventana deslizante con solapamiento del 80% sobre cada lote. Registra métricas críticas en [resultados_pruebas.json](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/resultados_pruebas.json).
* **Métricas evaluadas:**
  * **Exactitud Global (Accuracy):** Concordancia entre la predicción del modelo y la etiqueta de calidad asignada por laboratorio.
  * **Latencia de Inferencia:** Tiempo en milisegundos que toma el modelo en procesar cada predicción.
  * **Consumo de Memoria:** Memoria RAM en MB consumida durante el proceso de análisis (monitoreada con `psutil`).
  * **Distribución de Errores:** Cantidad de falsos positivos y falsos negativos de calidad.

---

## 🚀 6. Guía de Ejecución de Pruebas: ¿Cómo las corro?

Para ejecutar las pruebas en tu computador o servidor local, sigue estos pasos desde la terminal de comandos (PowerShell):

### 1. Activar el Entorno Virtual de Python
Asegúrate de estar en el directorio raíz del proyecto y activa el entorno:
```powershell
# En Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Correr las Pruebas Unitarias y Generar Reporte de Cobertura
Navega a la carpeta del servidor de FastAPI y ejecuta `pytest` junto con la generación del reporte XML para SonarQube:
```powershell
cd fastapi_server
# Ejecutar pytest y calcular la cobertura sobre el script api.py
pytest --cov=api --cov-report=xml -v
```
*Esto ejecutará las pruebas de caja negra y unitarias de `test_api.py`, validando el correcto funcionamiento de las rutas REST y el búfer circular. Generará el archivo `coverage.xml` en la misma carpeta.*

### 3. Ejecutar las Pruebas de Integración y Rendimiento de Lotes
Vuelve a la raíz del proyecto y ejecuta el script de análisis de lotes experimentales reales:
```powershell
cd ..
python data/ejecutar_pruebas_json.py
```
*Este script evaluará los 450 lotes de datos reales. Al finalizar, mostrará el resumen de precisión, latencia y consumo de RAM por pantalla y los guardará en `data/resultados_pruebas.json`.*

### 4. Ejecutar el Análisis de Calidad de Código en SonarQube
Si deseas analizar el código y la cobertura de pruebas con SonarQube, inicia el contenedor y ejecuta el escáner:
```powershell
# 1. Asegurarse de que SonarQube está activo en Docker
docker start sonarqube

# 2. Situarse en la carpeta fastapi_server (donde está sonar-project.properties)
cd fastapi_server

# 3. Ejecutar el escáner de SonarQube mediante Docker
docker run --rm -e SONAR_HOST_URL="http://host.docker.internal:9000" -e SONAR_TOKEN="sqp_f692361fccdff77061534403e9a84ef84f9ef6e7" -v "${PWD}:/usr/src" sonarsource/sonar-scanner-cli
```
*Una vez completado, podrás ver el reporte de vulnerabilidades, duplicaciones de código y porcentaje de cobertura en tu navegador abriendo: `http://localhost:9000`.*

---

## 📟 7. Ejecutable para el LCD: ¿Dónde está y cómo lo corro?

El archivo ejecutable para la pantalla LCD física es **[`fastapi_server/lcd_client.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/lcd_client.py)**.

### Características del Ejecutable:
* Utiliza la librería **`RPLCD`** para comunicarse a través del bus I2C con la pantalla física LCD 16x2 de la Raspberry Pi (dirección I2C por defecto `0x27`).
* Consulta el endpoint `/latest_result` del servidor FastAPI local cada 2 segundos.
* **Salida Dinámica:**
  * Si el búfer de 30 segundos no está lleno, muestra: `Llenando Bufer` y el progreso de llenado en segundos (ej. `Progreso: 12/30s`).
  * Si el búfer está completo, muestra el diagnóstico formal de calidad académica en la primera línea: **`Gasol. Grado A`** (Conforme), **`Gasol. Grado B`** (Desviado) o **`Gasol. Grado C`** (No Conforme); y el porcentaje de confianza en la segunda línea: `Confianza: 94.5%`.
  * Si el servidor se apaga o se pierde la conexión de red, muestra automáticamente: `Sin Conexion API \n Reintentando...`.

### ¿Cómo correrlo en la Raspberry Pi?

1. **Instalar dependencias necesarias en la Raspberry Pi:**
   ```bash
   pip install requests RPLCD
   ```

2. **Habilitar el puerto I2C de la Raspberry Pi:**
   Si no lo has hecho, abre la configuración de la RPi:
   ```bash
   sudo raspi-config
   ```
   Navega a *Interface Options* -> *I2C* y actívalo. Reinicia la Raspberry Pi.

3. **Ejecutar el script cliente:**
   Asegúrate de que la API de FastAPI esté activa en la misma red (en el puerto 8000) y corre el script:
   ```bash
   python lcd_client.py
   ```
   *Nota: Si ejecutas el script en una PC de desarrollo convencional donde no hay pines físicos ni bus I2C, el ejecutable detectará la ausencia de la librería `RPLCD`, entrará en modo de emulación automática y mostrará las lecturas y actualizaciones del LCD por consola sin generar errores.*
