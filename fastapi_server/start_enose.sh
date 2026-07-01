#!/bin/bash
# Directorio raíz del proyecto en la Raspberry Pi
DIR="/home/pollito/Deep-Learning-for-Biofuel-Quality-Control"

echo "=== INICIANDO SERVIDORES E-NOSE ==="
cd $DIR/fastapi_server

# 1. Activar el entorno virtual de Python
source $DIR/.venv/bin/activate

# 2. Levantar la API de FastAPI en segundo plano en el puerto 8000
python -m uvicorn api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
API_PID=$!
echo "[LOADER] Servidor FastAPI iniciado (PID: $API_PID)."
echo "[LOADER] Puedes monitorear los logs con: tail -f api.log"

# 3. Levantar el cliente físico del LCD 16x2 (DESHABILITADO TEMPORALMENTE)
# Descomentar las siguientes líneas una vez que el hardware del LCD esté conectado a los pines I2C.
# python lcd_client.py > lcd.log 2>&1 &
# LCD_PID=$!
# echo "[LOADER] Cliente de pantalla LCD iniciado (PID: $LCD_PID)."

# Mantener el script vivo y capturar señales de apagado
trap "echo 'Apagando servicios...'; kill $API_PID $LCD_PID; exit" SIGINT SIGTERM

while true; do
    sleep 1
done
