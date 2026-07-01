# Plan de Pruebas y Reporte de Ejecución (Normativa ISO/IEC 29119)

Este documento contiene la planificación, especificación técnica de casos de prueba (caja negra, caja blanca, unitarias e integración) y el reporte de ejecución unificado para el sistema de control de calidad de biocombustibles mediante Nariz Electrónica (E-Nose).

---

## 📋 1. Especificación del Entorno de Pruebas

Para garantizar la reproducibilidad de las pruebas, se especifica el siguiente entorno tecnológico de ejecución:

* **Sistema Operativo:** Windows 10/11
* **Intérprete de Python:** Python 3.13 (Entorno virtual `.venv` aislado)
* **Librerías Críticas de Prueba:**
  * `pytest` (v9.1.1): Framework de automatización.
  * `pytest-cov` (v7.1.0): Generador de reportes de cobertura de código.
  * `httpx`: Cliente de peticiones asíncronas para pruebas de API.
* **Componentes de Producción Evaluados:**
  * Servidor de inferencia: FastAPI (`fastapi_server/api.py`)
  * Modelo de Deep Learning: TensorFlow Lite (`fastapi_server/model/enose_modelo.tflite`)
  * Normalizador estadístico: StandardScaler (`fastapi_server/model/scaler.pkl`)

---

## 🧪 2. Matriz de Casos de Prueba Detallada

### 2.1 Pruebas Unitarias y de Caja Negra (Funcionales)
Estas pruebas validan el comportamiento externo de la API ante peticiones y payloads específicos de entrada sin considerar la lógica interna de la red neuronal.

| ID de Prueba | Nombre | Descripción | Entrada Enviada (Payload) | Resultado Esperado |
|---|---|---|---|---|
| **PR-UN-01** | `test_health_endpoint` | Valida que la API responda correctamente y confirme que el modelo TFLite y normalizadores se cargaron bien. | GET `/health` | Status `200 OK`<br>`status: "healthy"`<br>`model_loaded: true` |
| **PR-UN-02** | `test_root_endpoint` | Verifica que el endpoint raíz sirva correctamente la interfaz HTML del SCADA. | GET `/` | Status `200 OK`<br>Contenido tipo `text/html`<br>Debe contener el tag `E-Nose` |
| **PR-UN-03** | `test_predict_alta_optimal` | Comprueba que un perfil sensorial idéntico al patrón de gasolina 90 se clasifique como Grado A. | Ventana de 30s con valores Z-score aproximados a `0` (similares a gasolina 90). | Status `200 OK`<br>`prediction: "ALTA"`<br>`confidence > 90%`<br>`alert: "Excelente calidad"` |
| **PR-UN-04** | `test_predict_deviated` | Evalúa si las desviaciones en sensores (anomalías) disparan alertas y diagnósticos específicos. | Ventana de 30s con desviación Z-score superior a 1.0 en MQ4 y MQ7. | Status `200 OK`<br>`prediction: "MEDIA"` o `"BAJA"`<br>Diagnósticos con alertas para MQ4 y MQ7. |
| **PR-UN-05** | `test_predict_invalid_size` | Comprueba el manejo de límites ante dimensiones incorrectas en la ventana de datos. | Lista con 10 lecturas (se requieren exactamente 30 lecturas/segundos). | Status `400 Bad Request`<br>Mensaje descriptivo indicando que requiere 30 timesteps. |
| **PR-UN-06** | `test_sensor_data_streaming` | Valida el ingreso continuo de lecturas en tiempo real y el manejo de búfer en memoria. | Envío de 1 registro JSON al endpoint `/sensor_data`. | Status `200 OK`<br>`buffer_size: 1` |

---

### 2.2 Pruebas de Caja Blanca (Estructurales y Excepciones)
Validan los caminos lógicos de ejecución dentro del código del backend (`api.py`), incluyendo el manejo de fallos y la lógica de flujo.

* **Flujo de Carga de Recursos (Lifespan):** Se prueba la inicialización asíncrona de FastAPI. Si falta algún archivo crítico (`enose_modelo.tflite` o `scaler.pkl`), la API corta la ejecución mediante una excepción `FileNotFoundError`, previniendo que el servidor funcione en estado corrupto.
* **Control del Búfer Circular (Memoria Constante):** En `/sensor_data`, se prueba la lógica de inserción:
  * Si el búfer es `< 30`, se añade el dato y se actualiza el estado.
  * Si es `= 30`, se dispara la normalización, inferencia y diagnóstico, actualizando el estado del dashboard.
  * Si es `> 30`, se elimina el dato más antiguo (`buffer.pop(0)`) y se inserta el nuevo, garantizando que el consumo de memoria del proceso sea constante ($O(1)$) y no crezca indefinidamente.
* **Manejo de Errores de Normalización:** Se valida que si el normalizador recibe valores no numéricos o matrices inconsistentes, el bloque `try/except` intercepte la falla y la API responda con un error `500 Internal Server Error` estructurado, sin congelar el hilo de ejecución del servidor.

---

### 2.3 Pruebas de Integración y Rendimiento (Batch Testing)
Validan la capacidad del modelo entrenado de integrarse con el software de inferencia y evaluar la exactitud físico-química sobre el dataset de validación real (450 lotes experimentales, equivalentes a 27,000 registros).

* **ID de Prueba:** `PR-INT-01`
* **Métricas Evaluadas:**
  1. **Exactitud Global (Accuracy):** Porcentaje de concordancia entre la etiqueta del modelo y la validación química del laboratorio.
  2. **Latencia del Modelo:** Tiempo de ejecución del intérprete TensorFlow Lite por predicción.
  3. **Consumo de RAM:** Medición de memoria del proceso mediante la librería `psutil`.

---

## 📈 3. Reporte de Resultados de la Última Ejecución

Los resultados obtenidos tras correr el ejecutor unificado de pruebas son los siguientes:

### A. Resultados de la Suite de Pruebas Unitarias (Pytest)
* **Pruebas Programadas:** 6
* **Pruebas Aprobadas:** 6 (100% de éxito)
* **Pruebas Falladas:** 0
* **Tiempo de Ejecución:** 8.93 segundos
* **Estado de la Suite:** **APROBADO**
* **Detalle de Ejecución:**
  * `test_health_endpoint` ─── **PASSED** [✓]
  * `test_root_endpoint` ─── **PASSED** [✓]
  * `test_predict_alta_optimal` ─── **PASSED** [✓]
  * `test_predict_deviated` ─── **PASSED** [✓]
  * `test_predict_invalid_size` ─── **PASSED** [✓]
  * `test_sensor_data_streaming` ─── **PASSED** [✓]
* **Reporte de Cobertura de Código:** Generado exitosamente en `fastapi_server/coverage.xml`.

### B. Resultados de la Suite de Integración y Rendimiento (Lotes)
* **Lotes Reales Evaluados:** 450 lotes (100% del dataset real)
* **Exactitud de Calificación (Accuracy):** **100%** (0 falsos positivos, 0 falsos negativos)
* **Latencia de Inferencia Promedio:** **0.33 milisegundos** por ventana
* **Consumo de RAM Promedio:** **361.59 MB**
* **Tiempo de Ejecución:** 10.47 segundos
* **Estado de la Suite:** **APROBADO**
* **Archivo de Resultados:** Generado en `data/resultados_pruebas.json`.

---

## 🚀 4. Instrucciones para Correr las Pruebas

Para ejecutar la suite de pruebas completa en un solo comando, abre una terminal en la raíz de tu proyecto y ejecuta:

```powershell
python run_all_tests.py
```

*El script detectará de forma automática el entorno virtual `.venv`, redireccionará la ejecución del Python global al intérprete correcto y te mostrará el dashboard unificado de resultados en consola.*
