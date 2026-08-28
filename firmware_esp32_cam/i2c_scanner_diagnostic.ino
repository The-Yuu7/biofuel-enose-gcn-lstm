/*
  ======================================================================
     ESCANER I2C Y DIAGNÓSTICO DE PINES ESP32-CAM
  ======================================================================
*/

#include <Wire.h>
#include <DHT.h>
#include <max6675.h>

#define I2C_SDA 14
#define I2C_SCL 15

#define DHTPIN  13
#define DHTTYPE DHT22

#define MAX_SO  12
#define MAX_CS  2
#define MAX_SCK 4

DHT dht(DHTPIN, DHTTYPE);
MAX6675 thermocouple(MAX_SCK, MAX_CS, MAX_SO);

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n======================================================================");
  Serial.println("         ESCANER DE BUS I2C Y DIAGNÓSTICO ESP32-CAM");
  Serial.println("======================================================================");

  // Inicializar bus I2C en GPIO 14 (SDA) y GPIO 15 (SCL) a 100kHz
  Wire.begin(I2C_SDA, I2C_SCL, 100000);
  Serial.println("[I2C BUS] Bus I2C configurado en SDA=14 y SCL=15.");

  dht.begin();
}

void loop() {
  Serial.println("\n🔍 ESCANEANDO DISPOSITIVOS I2C EN BUS (SDA: 14, SCL: 15)...");
  byte count = 0;

  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf("   ✅ Dispositivo I2C encontrado en dirección: 0x%02X ", address);
      if (address == 0x48) Serial.print("(ADS1115 #1 - MQ2, MQ4, MQ135, MQ3)");
      if (address == 0x49) Serial.print("(ADS1115 #2 - MQ7, MQ9)");
      Serial.println();
      count++;
    }
  }

  if (count == 0) {
    Serial.println("   ❌ NO SE ENCONTRÓ NINGÚN DISPOSITIVO I2C.");
    Serial.println("   --> Verifica: 1) Pin LV del nivelador a 3V3 del ESP32. 2) Pin HV del nivelador a 5V.");
    Serial.println("   --> Verifica: 3) Cables LV1 a GPIO14 y LV2 a GPIO15. 4) GND común.");
  } else {
    Serial.printf("   🎉 ¡Se encontraron %d dispositivo(s) I2C!\n", count);
  }

  // Probar DHT22 en GPIO 13
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  Serial.println("\n🌡️ ESTADO DHT22 (GPIO 13):");
  if (isnan(t) || isnan(h)) {
    Serial.println("   ❌ DHT22 Error de lectura. Asegúrate de alimentar DHT22 con 3.3V/5V y masa común.");
  } else {
    Serial.printf("   ✅ DHT22 OK -> Temp: %.1f °C | Humedad: %.1f %%\n", t, h);
  }

  // Probar MAX6675 en GPIO 12, 2, 4
  float tr = thermocouple.readCelsius();
  Serial.println("\n🔥 ESTADO MAX6675 (REACTOR):");
  Serial.printf("   ✅ MAX6675 OK -> Temp Reactor: %.1f °C\n", tr);

  delay(3000);
}
