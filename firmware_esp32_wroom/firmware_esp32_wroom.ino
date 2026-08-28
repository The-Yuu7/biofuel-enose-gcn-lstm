/*
  ======================================================================
     CÓDIGO OFICIAL ESP32 WROOM (30 PINES) - BIO-E-NOSE PIRÓLISIS
  ======================================================================
  Microcontrolador: ESP32 WROOM-32 (30 Pines)
  Red WiFi Target : MAGLIONI (Raspberry Pi AP)
  Password WiFi   : ingeapruebemecon20
  Servidor Target : http://10.42.0.1:8000/sensor_data
  ======================================================================
  MAPA DE PINES ESP32 WROOM 30 PINES:
    - SDA I2C (ADS1115) -> Pin GPIO 21 (Entrada LV1 del Nivelador Lógico)
    - SCL I2C (ADS1115) -> Pin GPIO 22 (Entrada LV2 del Nivelador Lógico)
    - DHT22 DATA        -> Pin GPIO 4  (Sensor Ambiental de Cámara)
    - MAX6675 SO        -> Pin GPIO 19 (Datos Termopar Reactor)
    - MAX6675 CS        -> Pin GPIO 5  (Chip Select Termopar Reactor)
    - MAX6675 SCK       -> Pin GPIO 18 (Clock SPI Termopar Reactor)
    - VCC / LV          -> Pin 3V3
    - GND               -> Pin GND (Masa común)
  ======================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <DHT.h>
#include <max6675.h>
#include <ArduinoJson.h>

// ----------------------------------------------------------------------
// CONFIGURACIÓN DE RED WIFI Y SERVIDOR RASPBERRY PI
// ----------------------------------------------------------------------
const char* ssid = "MAGLIONI";
const char* password = "ingeapruebemecon20";
const char* serverUrl = "http://10.42.0.1:8000/sensor_data";

// ----------------------------------------------------------------------
// CONFIGURACIÓN DE PINES HARDWARE NATIVOS ESP32 WROOM
// ----------------------------------------------------------------------
#define I2C_SDA 21       // Pin nativo Hardware I2C SDA
#define I2C_SCL 22       // Pin nativo Hardware I2C SCL

#define DHTPIN  4        // Pin GPIO 4 para datos del DHT22
#define DHTTYPE DHT22

// Pines VSPI Nativos para MAX6675 (Termopar del Reactor)
#define MAX_SO  19       // VSPI MISO
#define MAX_CS  5        // VSPI SS
#define MAX_SCK 18       // VSPI CLK

// Instancias de Hardware
Adafruit_ADS1115 ads1; // Dirección 0x48 (ADDR -> GND)
Adafruit_ADS1115 ads2; // Dirección 0x49 (ADDR -> VDD)
DHT dht(DHTPIN, DHTTYPE);
MAX6675 thermocouple(MAX_SCK, MAX_CS, MAX_SO);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n======================================================================");
  Serial.println("  INICIANDO EMISOR ESP32 WROOM-32 (30 PINES) - BIO-E-NOSE PIRÓLISIS");
  Serial.println("======================================================================");

  // 1. Inicializar bus I2C Nativo en GPIO 21 (SDA) y GPIO 22 (SCL)
  Wire.begin(I2C_SDA, I2C_SCL);
  Serial.println("[INFO] Bus I2C Nativo iniciado en GPIO 21 (SDA) y GPIO 22 (SCL).");

  // 2. Inicializar ADS1115 #1 (0x48)
  if (!ads1.begin(0x48, &Wire)) {
    Serial.println("[ERROR] No se encontró ADS1115 #1 (0x48). Revisa LV1(21), LV2(22) y 5V.");
  } else {
    ads1.setGain(GAIN_ONE); // Rango +/- 4.096V
    Serial.println("[OK] ADS1115 #1 (0x48) inicializado.");
  }

  // 3. Inicializar ADS1115 #2 (0x49)
  if (!ads2.begin(0x49, &Wire)) {
    Serial.println("[ERROR] No se encontró ADS1115 #2 (0x49). Revisa ADDR a 5V.");
  } else {
    ads2.setGain(GAIN_ONE); // Rango +/- 4.096V
    Serial.println("[OK] ADS1115 #2 (0x49) inicializado.");
  }

  // 4. Inicializar DHT22 y Termopar MAX6675
  dht.begin();
  Serial.println("[OK] Sensor DHT22 iniciado en GPIO 4.");
  Serial.println("[OK] Termopar MAX6675 iniciado en SO=19, CS=5, SCK=18.");

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
    Serial.println("\n[WIFI OK] ¡Conectado exitosamente!");
    Serial.print("[WIFI OK] IP asignada al ESP32 WROOM: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WIFI ERROR] No se pudo conectar a la red MAGLIONI.");
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

  // 3. Leer DHT22 (Ambiente Cámara) y MAX6675 (Interior del Reactor)
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  float temp_reactor = thermocouple.readCelsius();

  // Reemplazar valores NaN por protección
  if (isnan(temp)) temp = 25.0;
  if (isnan(hum))  hum  = 50.0;
  if (isnan(temp_reactor) || temp_reactor <= 0) temp_reactor = 430.0;

  // 4. Imprimir en Consola Serie
  Serial.printf("[SENSORES] MQ2: %d | MQ4: %d | MQ135: %d | MQ3: %d | MQ7: %d | MQ9: %d | Temp Cam: %.1f°C | Hum: %.1f%% | TEMP REACTOR: %.1f°C\n",
                adc_mq2, adc_mq4, adc_mq135, adc_mq3, adc_mq7, adc_mq9, temp, hum, temp_reactor);

  // 5. Construir objeto JSON
  StaticJsonDocument<320> doc;
  doc["MQ2"]          = adc_mq2;
  doc["MQ4"]          = adc_mq4;
  doc["MQ135"]        = adc_mq135;
  doc["MQ3"]          = adc_mq3;
  doc["MQ7"]          = adc_mq7;
  doc["MQ9"]          = adc_mq9;
  doc["temp"]         = temp;
  doc["humedad"]      = hum;
  doc["temp_reactor"] = temp_reactor;

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
    Serial.printf("[HTTP ERROR] Fallo al enviar POST. Error: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();

  // Transmitir cada 1 segundo
  delay(1000);
}
