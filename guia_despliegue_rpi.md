# Guía de Despliegue en Raspberry Pi e Inicio Automático (Boot)

Esta guía explica paso a paso cómo transferir tu proyecto a la Raspberry Pi, configurarlo para que sea accesible desde cualquier dispositivo conectado a tu red WiFi local, y programar un servicio del sistema para que el servidor y la pantalla LCD arranquen automáticamente al encender la placa.

---

## 🔌 Paso 1: ¿Cómo pasar los archivos a la Raspberry Pi?

Tienes dos opciones principales para copiar la carpeta del proyecto `Deep-Learning-for-Biofuel-Quality-Control` desde tu laptop/PC hacia la Raspberry Pi:

### Opción A: Usando una memoria USB (Pendrive)
1. Copia la carpeta del proyecto completa a tu memoria USB en Windows.
2. Expulsa la memoria USB y conéctala a uno de los puertos USB de la Raspberry Pi.
3. Si estás usando la interfaz gráfica de la Raspberry Pi, la memoria se montará automáticamente. Abre la terminal en la RPi y cópiala a tu carpeta de usuario:
   ```bash
   cp -r /media/pi/NOMBRE_USB/Deep-Learning-for-Biofuel-Quality-Control ~/
   ```
4. Si estás por consola pura, monta el dispositivo USB manualmente:
   ```bash
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sda1 /mnt/usb
   cp -r /mnt/usb/Deep-Learning-for-Biofuel-Quality-Control ~/
   sudo umount /mnt/usb
   ```

### Opción B: Por Red Local usando SCP o SFTP (Recomendada y más rápida)
Si tu PC y la Raspberry Pi están conectadas a la misma red WiFi, puedes transferir los archivos directamente sin desconectar nada:
1. Instala un cliente SFTP gráfico como **FileZilla** en tu PC.
2. Conéctate ingresando la IP de la Raspberry Pi, tu usuario (ej. `pi`), contraseña y puerto `22` (SSH).
3. Arrastra y suelta la carpeta del proyecto a la carpeta `/home/pi/`.
4. *Alternativamente, desde la terminal de Windows (PowerShell) puedes usar `scp`:*
   ```powershell
   scp -r d:\Deep-Learning-for-Biofuel-Quality-Control pi@<IP-DE-TU-RASPBERRY>:~/
   ```

---

## 📶 Paso 2: Configurar la Red Local y Obtener la IP

Para que cualquier dispositivo (móvil, tablet, laptop) en la misma red WiFi acceda al dashboard:

1. **Obtener la IP de la Raspberry Pi:**
   Abre una terminal en tu Raspberry Pi y ejecuta:
   ```bash
   hostname -I
   ```
   *Te devolverá una dirección IP (por ejemplo, `192.168.1.45`). Anota esta dirección.*

2. **Permitir accesos de red en FastAPI:**
   Por defecto, los servidores web escuchan en `127.0.0.1` (localhost), lo que significa que solo aceptan conexiones de la misma máquina.
   Para aceptar conexiones desde cualquier dispositivo del WiFi, el servidor debe escuchar en la dirección **`0.0.0.0`**. 
   
   Tu archivo [`api.py`](file:///d:/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/api.py) ya cuenta con esta configuración al final:
   ```python
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
   ```
   *Esto asegura que al iniciar la API, esta escuche las peticiones de toda tu red local en el puerto 8000.*

---

## 🛠️ Paso 3: Crear el Script Cargador Principal (Loader Script)

Crearemos un script de Bash (`.sh`) en la Raspberry Pi que actúe como el **Cargador Principal**. Este script se encargará de activar el entorno virtual, levantar el servidor FastAPI y ejecutar el cliente LCD en segundo plano en un solo paso.

Crea un archivo llamado `start_enose.sh` en el directorio de tu proyecto en la Raspberry Pi:
```bash
nano ~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/start_enose.sh
```

Pega el siguiente contenido:
```bash
#!/bin/bash
# Directorio raíz del proyecto
DIR="/home/pi/Deep-Learning-for-Biofuel-Quality-Control"

echo "=== INICIANDO SISTEMA DE MONITOREO E-NOSE ==="
cd $DIR/fastapi_server

# 1. Activar el entorno virtual de Python
source $DIR/.venv/bin/activate

# 2. Levantar la API de FastAPI en segundo plano en el puerto 8000
python -m uvicorn api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
API_PID=$!
echo "[LOADER] Servidor FastAPI iniciado (PID: $API_PID). Esperando 5s..."
sleep 5

# 3. Levantar el cliente físico del LCD 16x2 en segundo plano
python lcd_client.py > lcd.log 2>&1 &
LCD_PID=$!
echo "[LOADER] Cliente de pantalla LCD iniciado (PID: $LCD_PID)."

# Mantener el script vivo y capturar señales de apagado para cerrar procesos hijos
trap "echo 'Apagando servicios...'; kill $API_PID $LCD_PID; exit" SIGINT SIGTERM

while true; do
    sleep 1
done
```

Guarda el archivo (`Ctrl+O`, `Enter`, `Ctrl+X`) y dale permisos de ejecución:
```bash
chmod +x ~/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/start_enose.sh
```

---

## ⚡ Paso 4: Configurar el Inicio Automático al Encender la Raspberry Pi

La forma estándar y profesional de hacer que este script corra automáticamente al prender la Raspberry Pi (incluso sin que tengas que iniciar sesión o abrir el escritorio gráfico) es mediante un **servicio de systemd** de Linux.

1. **Crear el archivo del servicio:**
   Ejecuta el siguiente comando en la terminal de la RPi:
   ```bash
   sudo nano /etc/systemd/system/enose.service
   ```

2. **Pegar la siguiente configuración:**
   *(Asegúrate de ajustar los nombres de usuario si el tuyo no es `pi`)*
   ```ini
   [Unit]
   Description=Servidor de Inferencia y Monitoreo E-Nose Biofuel
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server
   ExecStart=/home/pi/Deep-Learning-for-Biofuel-Quality-Control/fastapi_server/start_enose.sh
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. **Guardar y habilitar el servicio:**
   Recarga el demonio de systemd para que reconozca el nuevo archivo:
   ```bash
   sudo systemctl daemon-reload
   ```

   Habilita el servicio para que **se inicie automáticamente al arrancar la Raspberry Pi**:
   ```bash
   sudo systemctl enable enose.service
   ```

   Inicia el servicio en este momento para verificar que todo funcione:
   ```bash
   sudo systemctl start enose.service
   ```

4. **Comandos útiles de mantenimiento para el servicio:**
   * **Ver el estado actual:** `sudo systemctl status enose.service`
   * **Detener el servicio:** `sudo systemctl stop enose.service`
   * **Reiniciar el servicio:** `sudo systemctl restart enose.service`
   * **Ver los logs en vivo del sistema:** `journalctl -u enose.service -f`

---

## 📱 Paso 5: ¿Cómo accedo desde otro dispositivo?

¡Listo! Una vez que la Raspberry Pi esté encendida, el servicio levantará la API automáticamente.

1. Conecta tu celular, tablet o laptop a la **misma red WiFi** que la Raspberry Pi.
2. Abre tu navegador web favorito (Chrome, Safari, Firefox).
3. En la barra de direcciones escribe la IP de la Raspberry Pi y el puerto `8000`:
   ```text
   http://192.168.1.45:8000/
   ```
   *(Reemplaza `192.168.1.45` por la IP real de tu placa).*
4. Verás aparecer inmediatamente la interfaz de control SCADA en vivo. Cualquier dato que envíe el ESP32 a la API se actualizará de forma instantánea en tu celular y en la pantalla física LCD conectada a la Raspberry Pi.
