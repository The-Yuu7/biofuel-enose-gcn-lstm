# 🧪 Guía Oficial de Calibración Real y Arquitectura Ciber-Física IoT
## Sistema E-Nose con Deep Learning (GCN-LSTM) para el Monitoreo y Diagnóstico del Reactor de Pirólisis

Esta guía documenta la arquitectura ciber-física (IoT + Edge AI) y el procedimiento oficial de calibración del sistema **Bio-E-Nose** para **Ingeniería de Sistemas e Informática**.

---

## 🛰️ 1. Arquitectura de Red y Topología de Comunicaciones IoT

```
┌────────────────────────────────┐         WiFi SoftAP        ┌──────────────────────────────────┐
│   ESP32-CAM / NodeMCU ESP32    │ ─────────────────────────> │   Raspberry Pi (Servidor AP)     │
│   (Capturador de Sensores)     │   SSID: E-Nose-Pi-Net      │   IP Estática: 10.42.0.1         │
│   - ADC ADS1115 (16-bit)       │   IP ESP32: 10.42.0.x      │   - Backend FastAPI (Port 8000)  │
│   - 6x MQ Sensors (MQ2-9)      │   HTTP POST /sensor_data   │   - Modelo LiteRT (enose.tflite) │
│   - Sensor Ambiental DHT22     │                            │   - Dashboard SCADA Web          │
└────────────────────────────────┘                            └────────────────┬─────────────────┘
                                                                               │
                                                                 Acceso Web    │ (http://10.42.0.1:8000)
                                                                 Navegador     ▼
                                                              ┌──────────────────────────────────┐
                                                              │  Laptop / Smartphone del Usuario │
                                                              │  (Visualización en Tiempo Real)  │
                                                              └──────────────────────────────────┘
```

### 📶 Configuración del Punto de Acceso WiFi Autónomo (Raspberry Pi AP):
1. La **Raspberry Pi** actúa como Punto de Acceso WiFi (`SSID: E-Nose-Pi-Net`, `IP: 10.42.0.1`).
2. El **ESP32-CAM** se conecta automáticamente al WiFi de la Pi y transmite cada segundo un objeto JSON con las lecturas analógicas y digitales al endpoint `http://10.42.0.1:8000/sensor_data`.
3. El usuario conecta su laptop o celular a `E-Nose-Pi-Net` y navega a `http://10.42.0.1:8000` para ver el control SCADA y diagnósticos del reactor de pirólisis en vivo.

---

## 🎯 2. Enfoque de Calidad del Reactor de Pirólisis de Plásticos

En lugar de requerir procesos complejos de destilación química (ajenos a la carrera de sistemas), el sistema evalúa la **firma espectral de los vapores del crudo de pirólisis (Bio-Oil)** directamente en la salida del reactor, comparándolos contra el **Patrón Ideal Comercial de 50 Muestras de Referencia**:

| Clase de Calidad | Evaluación de Vapores del Reactor | Diagnóstico y Acción de Control Automática |
| :--- | :--- | :--- |
| **🟢 CLASE A (ÓPTIMA)** | Vapores de pirólisis ricos en hidrocarburos livianos deseados. Alta convergencia con el patrón comercial ($Z \le 1.5\sigma$). | **Pirólisis Eficiente:** Reactor estabilizado a $400-450^\circ\text{C}$. Alimentación limpia de plástico PE/PP. Continuar parámetros actuales. |
| **🟡 CLASE B (ADVERTENCIA)** | Tasa de calentamiento lenta o deriva térmica en la cámara de pirólisis ($1.5\sigma < Z \le 3.0\sigma$). | **Desviación Térmica:** Incrementar la potencia del calentador en $+10\%$ para estabilizar la temperatura de craqueo térmico. |
| **🔴 CLASE C (DEFICIENTE)** | Monóxido de carbono $CO$ elevado en `MQ7` (incompleta), `MQ3` alto (PET/PVC contaminante) o vapores pobres ($Z > 3.0\sigma$). | **Reacción Fallida / Incompleta:** Detener alimentación de plásticos oxigenados. Purga de reactor recomendada. |

---

## 📁 3. Componentes del Módulo (`calibracion_real/`)

* **`registros_gasolina_50.csv`**: Matriz de calibración patrón ($50 \text{ muestras} \times 30\text{s} = 1,500 \text{ filas de datos}$).
* **`generar_perfil_real.py`**: Compilador del modelo TFLite (`enose_modelo.tflite`), escalador físico (`scaler.pkl`) y perfil patrón (`perfil_referencia.pkl`).
* **`modelo_exportado/`**: Directorio consolidado de artefactos empaquetados para la Raspberry Pi.

---

## 🚀 4. Comando de Despliegue en la Raspberry Pi

Para actualizar los modelos calibrados en la Raspberry Pi desde tu Laptop:

```powershell
scp -r d:\Deep-Learning-for-Biofuel-Quality-Control\calibracion_real\modelo_exportado\* pi@10.42.0.1:~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/model/
```

Para iniciar el servidor SCADA en la Raspberry Pi:
```bash
ssh pi@10.42.0.1
cd ~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server
python api.py
```
