import os
import sys
import time
import requests

# Try to import the Raspberry Pi RPLCD library
try:
    # pyrefly: ignore [missing-import]
    from RPLCD.i2c import CharLCD
    LCD_AVAILABLE = True
except ImportError:
    LCD_AVAILABLE = False
    print("[WARN] La librería RPLCD no está instalada. Se simulará la salida en pantalla.")

# Configuration
API_URL = "http://localhost:8000/latest_result"
LCD_I2C_ADDRESS = 0x27  # Common address for 16x2 I2C LCD screens
LCD_COLS = 16
LCD_ROWS = 2

def main():
    print("=" * 60)
    print("      RASPBERRY PI - CLIENTE DE VISUALIZACIÓN LCD 16x2")
    print("=" * 60)
    print(f"Buscando actualizaciones en la API: {API_URL} cada 2 segundos...")
    
    # Initialize physical LCD if library is installed
    lcd = None
    if LCD_AVAILABLE:
        try:
            # Initialize LCD via I2C using the PCF8574 chip
            lcd = CharLCD(i2c_expander='PCF8574', address=LCD_I2C_ADDRESS, port=1, cols=LCD_COLS, rows=LCD_ROWS)
            lcd.clear()
            lcd.write_string("E-Nose Control\nIniciando...")
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar la pantalla LCD física: {e}")
            lcd = None

    last_prediction = ""
    last_confidence = 0.0

    try:
        while True:
            try:
                # Query the latest result from the FastAPI server
                response = requests.get(API_URL, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    prediction = data.get("prediction", "Esperando...")
                    confidence = data.get("confidence", 0.0)
                    buffer_size = data.get("buffer_size", 0)

                    # Check if there is new data or if buffer is still filling
                    if buffer_size < 30:
                        line1 = "Llenando Bufer  "
                        line2 = f"Progreso: {buffer_size:02d}/30s"
                    else:
                        # Translate prediction to formal academic quality specification
                        if prediction == "ALTA":
                            line1 = "Gasol. Grado A  "  # Conforme - Alta Especificidad
                        elif prediction == "MEDIA":
                            line1 = "Gasol. Grado B  "  # Desviado - Calidad Intermedia
                        else:
                            line1 = "Gasol. Grado C  "  # No conforme - Fuera de especificaciones
                        
                        line2 = f"Confianza: {confidence}%"

                    # Only update the LCD if values changed to prevent screen flicker
                    if prediction != last_prediction or confidence != last_confidence:
                        print(f"[LCD Update] {line1.strip()} | {line2}")
                        
                        if lcd:
                            lcd.clear()
                            # Write line 1 and line 2 (using newline \n to split rows)
                            lcd.write_string(f"{line1[:16]}\n{line2[:16]}")
                        
                        last_prediction = prediction
                        last_confidence = confidence

                else:
                    msg = "Error Servidor  \nHTTP: " + str(response.status_code)
                    if lcd:
                        lcd.clear()
                        lcd.write_string(msg)
                    print(f"[LCD Error] HTTP Code {response.status_code}")

            except requests.exceptions.RequestException:
                msg = "Sin Conexion API\nReintentando..."
                if lcd:
                    lcd.clear()
                    lcd.write_string(msg)
                print("[LCD Error] No se pudo conectar a la API. Reintentando...")

            time.sleep(2.0)

    except KeyboardInterrupt:
        print("\nCliente LCD detenido.")
        if lcd:
            lcd.clear()
            lcd.write_string("Sistema Apagado")

if __name__ == "__main__":
    main()
