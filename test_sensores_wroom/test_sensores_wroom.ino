/*
  ======================================================================
     CÓDIGO DE DIAGNÓSTICO SENSORES ESP32 WROOM (30 PINES - SIN WIFI)
  ======================================================================
  Placa Arduino IDE: ESP32 Dev Module
  ======================================================================
*/

#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <DHT.h>
#include <max6675.h>

#define I2C_SDA 21
#define I2C_SCL 22

#define DHTPIN  4
#define DHTTYPE DHT22

#define MAX_SO  19
#define MAX_CS  5
#define MAX_SCK 18

Adafruit_ADS1115 ads1; // 0x48 (ADDR -> GND)
Adafruit_ADS1115 ads2; // 0x49 (ADDR -> VDD)
DHT dht(DHTPIN, DHTTYPE);
MAX6675 thermocouple(MAX_SCK, MAX_CS, MAX_SO);

bool status_ads1 = false;
bool status_ads2 = false;

void setup() {
  Serial.begin(115200);
  delay(1500);
  
  Serial.println("\n======================================================================");
  Serial.println("  INICIANDO DIAGNÓSTICO HARDWARE ESP32 WROOM (30 PINES)");
  Serial.println("======================================================================");

  Wire.begin(I2C_SDA, I2C_SCL);
  Serial.println("[BUS I2C] Iniciado en GPIO 21 (SDA) y GPIO 22 (SCL).");

  if (ads1.begin(0x48, &Wire)) {
    ads1.setGain(GAIN_ONE);
    status_ads1 = true;
    Serial.println("[ADS1115 #1 - 0x48] ✅ OK (MQ2, MQ4, MQ135, MQ3)");
  } else {
    Serial.println("[ADS1115 #1 - 0x48] ❌ ERROR DE CONEXIÓN. Revisa LV1(21), LV2(22).");
  }

  if (ads2.begin(0x49, &Wire)) {
    ads2.setGain(GAIN_ONE);
    status_ads2 = true;
    Serial.println("[ADS1115 #2 - 0x49] ✅ OK (MQ7, MQ9)");
  } else {
    Serial.println("[ADS1115 #2 - 0x49] ❌ ERROR DE CONEXIÓN. Revisa ADDR a 5V.");
  }

  dht.begin();
  Serial.println("[DHT22] ✅ OK Iniciado en GPIO 4.");
  Serial.println("[MAX6675] ✅ OK Iniciado en SO=19, CS=5, SCK=18.");
  Serial.println("======================================================================\n");
}

void loop() {
  Serial.println("----------------------------------------------------------------------");
  
  int16_t mq2 = 0, mq4 = 0, mq135 = 0, mq3 = 0;
  if (status_ads1) {
    mq2   = ads1.readADC_SingleEnded(0);
    mq4   = ads1.readADC_SingleEnded(1);
    mq135 = ads1.readADC_SingleEnded(2);
    mq3   = ads1.readADC_SingleEnded(3);
  }

  int16_t mq7 = 0, mq9 = 0;
  if (status_ads2) {
    mq7 = ads2.readADC_SingleEnded(0);
    mq9 = ads2.readADC_SingleEnded(1);
  }

  float t_cam = dht.readTemperature();
  float h_cam = dht.readHumidity();
  float t_reactor = thermocouple.readCelsius();

  float v_mq2   = mq2 * 0.000125;
  float v_mq4   = mq4 * 0.000125;
  float v_mq135 = mq135 * 0.000125;
  float v_mq3   = mq3 * 0.000125;
  float v_mq7   = mq7 * 0.000125;
  float v_mq9   = mq9 * 0.000125;

  Serial.printf("📊 SENSORES MQ (ADC / VOLTIOS):\n");
  Serial.printf("   - MQ2   : %5d  (%.3f V)\n", mq2, v_mq2);
  Serial.printf("   - MQ4   : %5d  (%.3f V)\n", mq4, v_mq4);
  Serial.printf("   - MQ135 : %5d  (%.3f V)\n", mq135, v_mq135);
  Serial.printf("   - MQ3   : %5d  (%.3f V)\n", mq3, v_mq3);
  Serial.printf("   - MQ7   : %5d  (%.3f V)\n", mq7, v_mq7);
  Serial.printf("   - MQ9   : %5d  (%.3f V)\n", mq9, v_mq9);
  
  Serial.printf("🌡️ TEMPERATURAS Y HUMEDAD:\n");
  if (isnan(t_cam) || isnan(h_cam)) {
    Serial.printf("   - Cámara Ambient : ❌ ERROR LECTURA DHT22 (Revisa GPIO 4)\n");
  } else {
    Serial.printf("   - Cámara Ambient : %.1f °C | Humedad: %.1f %%\n", t_cam, h_cam);
  }

  if (isnan(t_reactor) || t_reactor <= 0) {
    Serial.printf("   - Reactor Interno: ❌ ERROR LECTURA MAX6675 (Revisa SO=19, CS=5, SCK=18)\n");
  } else {
    Serial.printf("   - Reactor Interno: 🔥 %.1f °C (Termopar Tipo K)\n", t_reactor);
  }

  delay(1500);
}
