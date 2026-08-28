/*
  ======================================================================
     CÓDIGO DE DIAGNÓSTICO PRUEBA INDIVIDUAL DE SENSORES (SIN REBOOT)
  ======================================================================
  Microcontrolador: ESP32-CAM / ESP32 Dev Module
  ======================================================================
  PINES SEGUROS:
    - SDA I2C     -> Pin GPIO 14 (LV1)
    - SCL I2C     -> Pin GPIO 15 (LV2)
    - DHT22 DATA   -> Pin GPIO 13
    - MAX6675 SO  -> Pin GPIO 16 (Pin seguro)
    - MAX6675 CS  -> Pin GPIO 2
    - MAX6675 SCK -> Pin GPIO 4
  ======================================================================
*/

#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <DHT.h>
#include <max6675.h>

#define I2C_SDA 14
#define I2C_SCL 15
#define DHTPIN  13
#define DHTTYPE DHT22

#define MAX_SO  16
#define MAX_CS  2
#define MAX_SCK 4

Adafruit_ADS1115 ads1; // Dirección 0x48 (ADDR -> GND)
Adafruit_ADS1115 ads2; // Dirección 0x49 (ADDR -> VDD)
DHT dht(DHTPIN, DHTTYPE);
MAX6675 thermocouple(MAX_SCK, MAX_CS, MAX_SO);

bool status_ads1 = false;
bool status_ads2 = false;

void setup() {
  Serial.begin(115200);
  delay(1500);
  
  Serial.println("\n======================================================================");
  Serial.println("  INICIANDO DIAGNÓSTICO HARDWARE BIO-E-NOSE (TEST DE SENSORES)");
  Serial.println("======================================================================");

  // 1. Inicializar I2C en GPIO 14 y 15
  Wire.begin(I2C_SDA, I2C_SCL, 100000);
  Serial.println("[BUS I2C] Iniciado en GPIO 14 (SDA) y GPIO 15 (SCL).");

  // 2. Probar ADS1115 #1 (0x48)
  if (ads1.begin(0x48, &Wire)) {
    ads1.setGain(GAIN_ONE);
    status_ads1 = true;
    Serial.println("[ADS1115 #1 - 0x48] ✅ OK (MQ2, MQ4, MQ135, MQ3)");
  } else {
    Serial.println("[ADS1115 #1 - 0x48] ❌ ERROR DE CONEXIÓN. Revisa GND, VCC, SDA(14), SCL(15).");
  }

  // 3. Probar ADS1115 #2 (0x49)
  if (ads2.begin(0x49, &Wire)) {
    ads2.setGain(GAIN_ONE);
    status_ads2 = true;
    Serial.println("[ADS1115 #2 - 0x49] ✅ OK (MQ7, MQ9)");
  } else {
    Serial.println("[ADS1115 #2 - 0x49] ❌ ERROR DE CONEXIÓN. Revisa ADDR conectado a VDD.");
  }

  // 4. Probar DHT22 y MAX6675
  dht.begin();
  Serial.println("[DHT22] ✅ OK Iniciado en GPIO 13.");
  Serial.println("[MAX6675] ✅ OK Iniciado en SO=16, CS=2, SCK=4.");
  Serial.println("======================================================================\n");
}

void loop() {
  Serial.println("----------------------------------------------------------------------");
  
  // 1. Leer Sensores de Gas ADS1115 #1
  int16_t mq2 = 0, mq4 = 0, mq135 = 0, mq3 = 0;
  if (status_ads1) {
    mq2   = ads1.readADC_SingleEnded(0);
    mq4   = ads1.readADC_SingleEnded(1);
    mq135 = ads1.readADC_SingleEnded(2);
    mq3   = ads1.readADC_SingleEnded(3);
  }

  // 2. Leer Sensores de Gas ADS1115 #2
  int16_t mq7 = 0, mq9 = 0;
  if (status_ads2) {
    mq7 = ads2.readADC_SingleEnded(0);
    mq9 = ads2.readADC_SingleEnded(1);
  }

  // 3. Leer DHT22 y MAX6675
  float t_cam = dht.readTemperature();
  float h_cam = dht.readHumidity();
  float t_reactor = thermocouple.readCelsius();

  // Convertir lecturas ADC a Volteos (Ganancia GAIN_ONE = 0.125mV por LSB)
  float v_mq2   = mq2 * 0.000125;
  float v_mq4   = mq4 * 0.000125;
  float v_mq135 = mq135 * 0.000125;
  float v_mq3   = mq3 * 0.000125;
  float v_mq7   = mq7 * 0.000125;
  float v_mq9   = mq9 * 0.000125;

  // Imprimir Resultados Formateados
  Serial.printf("📊 SENSORES MQ (ADC / VOLTIOS):\n");
  Serial.printf("   - MQ2   : %5d  (%.3f V)\n", mq2, v_mq2);
  Serial.printf("   - MQ4   : %5d  (%.3f V)\n", mq4, v_mq4);
  Serial.printf("   - MQ135 : %5d  (%.3f V)\n", mq135, v_mq135);
  Serial.printf("   - MQ3   : %5d  (%.3f V)\n", mq3, v_mq3);
  Serial.printf("   - MQ7   : %5d  (%.3f V)\n", mq7, v_mq7);
  Serial.printf("   - MQ9   : %5d  (%.3f V)\n", mq9, v_mq9);
  
  Serial.printf("🌡️ TEMPERATURAS Y HUMEDAD:\n");
  if (isnan(t_cam) || isnan(h_cam)) {
    Serial.printf("   - Cámara Ambient : ❌ ERROR LECTURA DHT22 (Revisa GPIO 13)\n");
  } else {
    Serial.printf("   - Cámara Ambient : %.1f °C | Humedad: %.1f %%\n", t_cam, h_cam);
  }

  if (isnan(t_reactor) || t_reactor <= 0) {
    Serial.printf("   - Reactor Interno: ❌ ERROR LECTURA MAX6675 (Revisa SO=16, CS=2, SCK=4)\n");
  } else {
    Serial.printf("   - Reactor Interno: 🔥 %.1f °C (Termopar Tipo K)\n", t_reactor);
  }

  delay(1500); // Repetir cada 1.5 segundos
}
