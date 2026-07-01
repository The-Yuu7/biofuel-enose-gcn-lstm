# Matrices de Operacionalización de la Investigación

Este documento presenta las matrices de operacionalización del proyecto. Se divide en dos secciones fundamentales para la tesis:
1. **Matriz de Operacionalización de Variables de Investigación (Científica):** Mapeo de variables físicas y químicas para el análisis del biocombustible.
2. **Matriz de Operacionalización de Calidad de Software (Ingeniería/ISO):** Mapeo de atributos de calidad del sistema, métricas, límites (Quality Gates) e instrumentos de verificación, referenciada en base a la matriz de control de versiones.

---

## 💻 1. ¿A qué se refiere el término "Gits" o "Trabajo con Gits"?

En ingeniería de software y en tu matriz de control de versiones, el término **"Gits"** (jerga para referirse a elementos de **Git**) se refiere a:
* **Commits de Git:** Cada vez que guardas una versión del código en el historial local con un mensaje explicativo (ej. `git commit -m "Implementación del modelo GCN-LSTM"`). Cada commit genera un código alfanumérico único (Hash de Commit, por ejemplo `d8f6a7b...`) que sirve como la **evidencia física infalsificable** de que hiciste ese desarrollo en esa fecha.
* **Ramas (Branches):** Subdivisiones del código para trabajar en paralelo (ej. una rama `feature/gcn-model` y otra `feature/fastapi-api`).
* **Pull Requests (PR) / Fusiones (Merges):** El proceso de integrar el código de una rama de desarrollo hacia la rama principal (`main` o `master`) después de pasar la suite de pruebas.

En tu Matriz de Registro de Control de Versiones, cuando te pide "Evidencia en Gits", se refiere a que coloques el **ID del Commit** o el enlace al repositorio de Git que demuestra que ese "Bolt" (módulo de software) fue integrado de forma trazable.

---

## 🔬 2. Matriz de Operacionalización de Variables de la Investigación

Esta matriz define cómo se miden y recolectan las variables físico-químicas y de clasificación de la tesis.

| Variable | Tipo de Variable | Definición Conceptual | Definición Operacional | Dimensión | Indicadores | Instrumento de Recolección |
|---|---|---|---|---|---|---|
| **Señales del Arreglo de Sensores MOS (E-Nose)** | **Independiente (X)** | Capacidad de absorción química de los gases volátiles liberados por el biocombustible al entrar en contacto con sensores semiconductores de óxido metálico. | Lecturas de voltaje digitalizadas por el ADC (16-bit) del ESP32 en un periodo de 30 segundos. | **Firma Química de Gases** | * Voltaje promedio del sensor MQ-2 (Combustibles/GLP)<br>* Voltaje promedio del MQ-4 (Metano)<br>* Voltaje promedio del MQ-135 (VOCs)<br>* Voltaje promedio del MQ-3 (Alcoholes)<br>* Voltaje promedio del MQ-7 (Monóxido de Carbono)<br>* Voltaje promedio del MQ-9 (Gases inflamables) | * Arreglo de sensores MQ.<br>* Microcontrolador ESP32.<br>* Script de captura [`data/leer_esp32.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/leer_esp32.py). |
| **Condiciones Ambientales de la Cámara** | **Independiente (X2)** | Temperatura y humedad relativa dentro del compartimiento de sensado que alteran la línea base del sensor. | Lecturas digitales de temperatura y humedad en el sensor DHT22. | **Deriva Ambiental** | * Temperatura ambiente (°C).<br>* Humedad relativa (%). | * Sensor digital DHT22.<br>* Script de captura [`data/leer_esp32.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/leer_esp32.py). |
| **Calidad del Biocombustible (Bio-oil)** | **Dependiente (Y)** | Clasificación de la calidad del bio-oil pirolítico determinada por su grado de correlación y similitud química con el patrón de gasolina 90. | Salida de clasificación multiclase procesada en tiempo real mediante la arquitectura de Deep Learning GCN-LSTM. | **Especificación de Calidad** | * **Grado A (Conforme):** Bio-oil óptimo similar a gasolina 90.<br>* **Grado B (Desviado):** Desviaciones operativas medias en el reactor.<br>* **Grado C (No Conforme):** Presencia excesiva de humedad o subproductos. | * Modelo TensorFlow Lite [`model/enose_modelo.tflite`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/model/enose_modelo.tflite).<br>* Servidor FastAPI [`fastapi_server/api.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/api.py). |

---

## 🛠️ 3. Matriz de Operacionalización de Calidad y Pruebas de Software (ISO 25000 / 29119)

Esta matriz operacionaliza cómo medimos que el producto de software de la tesis cumple con los estándares internacionales de ingeniería.

| Atributo de Calidad (ISO 25000) | Tipo de Prueba (ISO 29119) | Métrica / Indicador | Umbral de Aceptación (Quality Gate) | Valor Real Obtenido (Reporte QA) | Instrumento / Herramienta de Medición | Evidencia en Proyecto (Mapeo de Bolts) |
|---|---|---|---|---|---|---|
| **Adecuación Funcional** | Caja Negra / Funcional | Exactitud de Predicción (Accuracy) | $\ge 90.0\%$ de aciertos en datos reales. | **100.0%** | Script evaluador masivo de lotes | [Resultados JSON](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/resultados_pruebas.json) (Bolt-006) |
| **Eficiencia de Rendimiento** | Integración / Desempeño | Latencia media de inferencia de la red neuronal | $< 20.0$ milisegundos por ventana. | **0.33 ms** | Medición de tiempo de cómputo en Python | [Resultados JSON](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/resultados_pruebas.json) (Bolt-001) |
| **Eficiencia de Rendimiento** | Estres / Integración | Consumo de memoria RAM del proceso | $< 500.0$ Megabytes en ejecución continua. | **361.59 MB** | Librería `psutil` en script de integración | [Resultados JSON](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/data/resultados_pruebas.json) (Bolt-006) |
| **Mantenibilidad** | Caja Blanca / Coherencia | Cobertura de código de pruebas unitarias | $\ge 80.0\%$ de líneas evaluadas por test. | **92.0%** (de la API principal) | Cobertura de pytest (`pytest-cov`) | [Coverage XML](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/coverage.xml) (Bolt-006) |
| **Mantenibilidad** | Análisis Estático / Estructura | Duplicaciones y Bugs críticos de código | $0$ bugs críticos y duplicación $< 3.0\%$. | **0 Bugs** / **0% Duplicación** | SonarQube Scanner | [Sonar Properties](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/sonar-project.properties) (Bolt-006) |
| **Seguridad de la Información** | Caja Negra / Validación | Manejo de excepciones ante datos incorrectos o nulos | $100\%$ de peticiones erróneas retornan código HTTP 400 sin colapsar el hilo del servidor. | **100% de éxito** | Peticiones HTTP asíncronas con pytest | [test_api.py](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/test_api.py) (Bolt-002) |
| **Capacidad de Visualización** | Funcional / Integración | Conexión en streaming y parpadeo de pantalla | Frecuencia de muestreo estable a $1.0\text{ s}$ sin parpadeos visuales (anti-flicker). | **Aprobado** | Cliente físico LCD con anti-flicker e interfaz SCADA | [lcd_client.py](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/lcd_client.py) (Bolt-004) |
