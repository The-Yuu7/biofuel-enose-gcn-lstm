/*
  ======================================================================
     CÓDIGO OFICIAL ESP32-CAM PARA SISTEMA BIO-E-NOSE (PIRÓLISIS)
  ======================================================================
  Microcontrolador: ESP32-CAM (AI-Thinker)
  Red WiFi Target : MAGLIONI (Raspberry Pi AP)
  Password WiFi   : ingeapruebemecon20
  Servidor Target : http://10.42.0.1:8000/sensor_data
  ======================================================================
  CONEXIÓN DE PINES:
    - 5V        -> Pin 5V (Fuente Alimentación 5V)
    - GND       -> Pin GND (Masa común)
    - SDA (I2C) -> Pin GPIO 14 (Salida LV1 del Convertidor de Nivel)
    - SCL (I2C) -> Pin GPIO 15 (Salida LV2 del Convertidor de Nivel)
    - DHT22 DATA-> Pin GPIO 13 (con resistencia pull-up 10k a 3.3V)
  ======================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ----------------------------------------------------------------------
// CONFIGURACIÓN DE RED WIFI Y SERVIDOR RASPBERRY PI
// ----------------------------------------------------------------------
const char* ssid = "MAGLIONI";
const char* password = "ingeapruebemecon20";
const char* serverUrl = "http://10.42.0.1:8000/sensor_data";

// ----------------------------------------------------------------------
// CONFIGURACIÓN DE PINES Y HARDWARE
// ----------------------------------------------------------------------
#define I2C_SDA 14       // Pin GPIO 14 para SDA I2C en ESP32-CAM
#define I2C_SCL 15       // Pin GPIO 15 para SCL I2C en ESP32-CAM
#define DHTPIN  13       // Pin GPIO 13 para datos del DHT22
#define DHTTYPE DHT22

// Instancias de Hardware
Adafruit_ADS1115 ads1; // Dirección 0x48 (ADDR -> GND)
Adafruit_ADS1115 ads2; // Dirección 0x49 (ADDR -> VDD)
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n======================================================================");
  Serial.println("     INICIANDO EMISOR ESP32-CAM - BIO-E-NOSE PIRÓLISIS");
  Serial.println("======================================================================");

  // 1. Inicializar bus I2C en pines dedicados GPIO 14 (SDA) y GPIO 15 (SCL)
  Wire.begin(I2C_SDA, I2C_SCL);
  Serial.println("[INFO] Bus I2C iniciado en GPIO 14 (SDA) y GPIO 15 (SCL).");

  // 2. Inicializar ADS1115 #1 (0x48)
  if (!ads1.begin(0x48, &Wire)) {
    Serial.println("[ERROR CRÍTICO] No se encontró el ADS1115 #1 en dirección 0x48.");
  } else {
    ads1.setGain(GAIN_ONE); // Rango +/- 4.096V
    Serial.println("[OK] ADS1115 #1 (0x48) inicializado.");
  }

  // 3. Inicializar ADS1115 #2 (0x49)
  if (!ads2.begin(0x49, &Wire)) {
    Serial.println("[ERROR CRÍTICO] No se encontró el ADS1115 #2 en dirección 0x49.");
  } else {
    ads2.setGain(GAIN_ONE); // Rango +/- 4.096V
    Serial.println("[OK] ADS1115 #2 (0x49) inicializado.");
  }

  // 4. Inicializar DHT22
  dht.begin();
  Serial.println("[OK] Sensor DHT22 iniciado en GPIO 13.");

  // 5. Conexión WiFi a la Raspberry Pi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("[WIFI] Conectando a la red '");
  Serial.print(ssid);
  Serial.print("'");

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI OK] Conectado exitosamente!");
    Serial.print("[WIFI OK] Dirección IP asignada al ESP32-CAM: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WIFI ERROR] No se pudo conectar a la red WiFi. Verifique la Raspberry Pi.");
  }
}

void loop() {
  // Reintentar conexión WiFi si se desconecta
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI RECONNECT] Reconectando a la red MAGLIONI...");
    WiFi.begin(ssid, password);
    delay(2000);
    return;
  }

  // 1. Leer Canales ADC del ADS1115 #1 (0x48)
  int16_t adc_mq2   = ads1.readADC_SingleEnded(0); // A0 -> MQ2
  int16_t adc_mq4   = ads1.readADC_SingleEnded(1); // A1 -> MQ4
  int16_t adc_mq135 = ads1.readADC_SingleEnded(2); // A2 -> MQ135
  int16_t adc_mq3   = ads1.readADC_SingleEnded(3); // A3 -> MQ3

  // 2. Leer Canales ADC del ADS1115 #2 (0x49)
  int16_t adc_mq7   = ads2.readADC_SingleEnded(0); // A0 -> MQ7
  int16_t adc_mq9   = ads2.readADC_SingleEnded(1); // A1 -> MQ9

  // 3. Leer Temperatura y Humedad del DHT22
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  // Reemplazar valores NaN por valores ambientales por defecto si hay fallo puntual
  if (isnan(temp)) temp = 25.0;
  if (isnan(hum))  hum  = 50.0;

  // 4. Imprimir lecturas en consola Serie para depuración
  Serial.printf("[SENSORES] MQ2: %d | MQ4: %d | MQ135: %d | MQ3: %d | MQ7: %d | MQ9: %d | Temp: %.1f°C | Hum: %.1f%%\n",
                adc_mq2, adc_mq4, adc_mq135, adc_mq3, adc_mq7, adc_mq9, temp, hum);

  // 5. Construir objeto JSON de Telemetría
  StaticJsonDocument<256> doc;
  doc["MQ2"]     = adc_mq2;
  doc["MQ4"]     = adc_mq4;
  doc["MQ135"]   = adc_mq135;
  doc["MQ3"]     = adc_mq3;
  doc["MQ7"]     = adc_mq7;
  doc["MQ9"]     = adc_mq9;
  doc["temp"]    = temp;
  doc["humedad"] = hum;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  // 6. Enviar datos vía HTTP POST a la Raspberry Pi
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.printf("[HTTP POST OK] Respuesta del Servidor Raspberry Pi (%d)\n", httpResponseCode);
  } else {
    Serial.printf("[HTTP ERROR] Fallo al enviar POST. Código de error: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();

  // Transmitir cada 1 segundo (1000 ms)
  delay(1000);
}
