# 🧪 Guía Oficial de Calibración Real de Sensores (50 Muestras Multi-Grifo)

Esta guía detalla el procedimiento paso a paso para calibrar la nariz electrónica **Bio-E-Nose** utilizando **50 muestras de gasolina comercial real** comprada en 3 estaciones de servicio (grifos) distintas.

---

## 📁 Archivos del Módulo (`calibracion_real/`)

* **`capturar_muestra_real.py`**: Servidor en vivo para la Laptop que recibe las lecturas de los sensores MQ + DHT22 desde el ESP32 (ADS1115).
* **`registros_gasolina_50.csv`**: Almacenamiento en blanco donde se guardarán las 50 matrices de 30 segundos.
* **`generar_perfil_real.py`**: Procesador que lee el CSV, calcula el **Perfil de Referencia de la Gasolina Real** (`perfil_referencia.pkl`), ajusta el escalador (`scaler.pkl`) y empaqueta el modelo TFLite.
* **`modelo_exportado/`**: Carpeta de salida con los 4 archivos listos para copiar a la Raspberry Pi.

---

## 🚀 PASO 1: Preparación del Hardware y Conexión en Laptop

1. Enciende el microcontrolador **ESP32 NodeMCU** con los sensores MQ conectados al ADC de 16-bit **ADS1115**.
2. Conecta tu Laptop al mismo punto de acceso WiFi del ESP32 (o hotspot).
3. Abre una consola de comandos (CMD o PowerShell) en tu Laptop en la carpeta del proyecto y ejecuta:

```powershell
python calibracion_real/capturar_muestra_real.py
```

---

## 🩺 PASO 2: Diagnóstico Previo de Salud de Sensores (Pre-Flight Check)

Antes de iniciar la captura de muestras:
1. En el menú de la consola presiona la opción **`0`** (`Diagnóstico de Salud`).
2. Revisa la tabla en vivo:
   * **🟢 [OK - SALUDABLE]:** Todos los sensores MQ2, MQ4, MQ135, MQ3, MQ7, MQ9 están dentro del rango ADC correcto y el DHT22 lee temperatura/humedad.
   * **🔴 [ERROR]:** Si algún sensor marca `0 ADC` (desconectado) o `65535` (cortocircuito), soluciona la conexión física del cable antes de continuar.

---

## ⛽ PASO 3: Toma de Muestras Multi-Grifo (50 Muestras)

Muestra la distribución de recolección:

### 1. Gasolinera / Grifo 1 (17 Muestras)
* En el menú de la consola presiona **`1`** (`Seleccionar GRIFO 1`).
* Coloca la gasolina del Grifo 1 en la cámara de sensado.
* Deja que el ESP32 transmita durante 30 segundos. Al completar los 30 segundos, verás: `✅ [ÉXITO] Guardada MUESTRA_001 (Grifo_1) en CSV!`.
* Repite el proceso hasta alcanzar las 17 muestras.

### 2. Gasolinera / Grifo 2 (17 Muestras)
* Presiona la opción **`2`** (`Seleccionar GRIFO 2`).
* Cambia la muestra por la gasolina del Grifo 2.
* Registra las 17 muestras hasta llegar al acumulado global de 34 muestras.

### 3. Gasolinera / Grifo 3 (16 Muestras)
* Presiona la opción **`3`** (`Seleccionar GRIFO 3`).
* Cambia la muestra por la gasolina del Grifo 3.
* Registra las 16 muestras hasta completar las **50 Muestras Totales**.
* Presiona la opción **`5`** para salir del capturador.

---

## 🧠 PASO 4: Generar la Firma Química Patrón y el Modelo

Una vez completadas las 50 muestras, ejecuta en la terminal de tu Laptop:

```powershell
python calibracion_real/generar_perfil_real.py
```

El script procesará los datos de los 3 grifos y creará la carpeta `calibracion_real/modelo_exportado/` con los archivos:
* `perfil_referencia.pkl` (Firma química promedio de la gasolina real).
* `scaler.pkl` (Escalador estándar de tus sensores).
* `label_encoder.pkl`
* `enose_modelo.tflite`

---

## 📟 PASO 5: Copiar los Archivos a la Raspberry Pi (Evaluación en Vivo)

Abre una terminal en tu Laptop y copia la nueva calibración hacia la Raspberry Pi conectada a la red **`MAGLIONI`**:

```powershell
scp calibracion_real/modelo_exportado/* pollito@10.42.0.1:~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/model/
```
*(Contraseña: `ingeapruebemecon20`)*.

Al reiniciar la Raspberry Pi (`sudo reboot`), el Dashboard Web SCADA evaluará las muestras de pirólisis **utilizando la calibración real obtenida con tus sensores físicas y la gasolina de los 3 grifos**.
