import subprocess
import time
import os
import sys
import webbrowser
import urllib.request
import urllib.error

# Obtener rutas absolutas
base_dir = os.path.dirname(os.path.abspath(__file__))

# Detectar el entorno virtual
venv_python = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
if not os.path.exists(venv_python):
    venv_python = sys.executable  # Fallback a Python global

fastapi_dir = os.path.join(base_dir, "fastapi_server")

print("======================================================================")
print("             LANZADOR UNIFICADO DEL SISTEMA E-NOSE")
print("======================================================================")
print(f"[INFO] 1. Iniciando Servidor Backend FastAPI...")

# 1. Iniciar FastAPI en segundo plano
api_process = subprocess.Popen(
    [venv_python, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=fastapi_dir
)

# 2. Esperar activamente a que la API responda en el puerto 8000
print("[INFO] Esperando a que el servidor FastAPI cargue los modelos y esté listo...")
print("       (Nota: Cargar TensorFlow y la red neuronal toma entre 15 y 25 segundos, por favor espere...)")
api_ready = False
max_retries = 45  # Esperar hasta 45 segundos máximo

for i in range(max_retries):
    try:
        # Intentar conectar al endpoint /health
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
            if response.status == 200:
                api_ready = True
                break
    except Exception:
        # Esperar 1 segundo antes de reintentar
        time.sleep(1)
        print(f"  [Espera] {i+1}s transcurridos... cargando modelos analíticos...")

if not api_ready:
    print("\n[ERROR] El servidor FastAPI tardó demasiado tiempo en responder.")
    print("[CONSEJO] Intente ejecutar el servidor manualmente para verificar si hay algún error de importación.")
    api_process.terminate()
    api_process.wait()
    sys.exit(1)

print("\n[INFO] Servidor levantado exitosamente.")

# 3. Abrir el navegador por defecto
url = "http://localhost:8000"
print(f"[INFO] 2. Abriendo navegador web en {url}...")
webbrowser.open(url)

# 4. Mantener el proceso activo para ver logs y esperar señal de apagado
print("\n======================================================================")
print("              SISTEMA LISTO Y ESPERANDO DATOS DE SENSORES")
print("======================================================================")
print("  El backend está corriendo y el búfer está vacío.")
print("  Usa 'python enviar_dataset.py' en otra terminal para transmitir datos.")
print("  Presiona Ctrl+C en esta terminal para apagar el servidor FastAPI.\n")

try:
    # Mantener el proceso vivo esperando Ctrl+C
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n[INFO] Detectado apagado del usuario. Deteniendo servidor backend...")
finally:
    # Terminar el proceso de FastAPI
    api_process.terminate()
    try:
        api_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        api_process.kill()
    print("[INFO] Servidor backend cerrado con éxito. ¡Lanzador finalizado!")
