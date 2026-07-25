import os
import sys
import csv
import time
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Rutas de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "registros_gasolina_50.csv")

app = FastAPI(title="Servidor de Calibración Real E-Nose (Laptop)")

# Estado Global de Captura
class EstadoCaptura:
    def __init__(self):
        self.modo_diagnostico: bool = False
        self.grabando_activo: bool = False
        self.grifo_actual: str = "Grifo_1"
        self.muestras_grifo_1: int = 0
        self.muestras_grifo_2: int = 0
        self.muestras_grifo_3: int = 0
        self.buffer_actual: List[Dict[str, float]] = []
        self.ultima_telemetria: Optional[Dict[str, float]] = None
        self.total_muestras: int = 0

estado = EstadoCaptura()

# Estructura Pydantic para validar datos entrantes del ESP32 / ADS1115
class SensorDataPayload(BaseModel):
    MQ2: float = Field(..., description="Valor ADC del MQ-2")
    MQ4: float = Field(..., description="Valor ADC del MQ-4")
    MQ135: float = Field(..., description="Valor ADC del MQ-135")
    MQ3: float = Field(..., description="Valor ADC del MQ-3")
    MQ7: float = Field(..., description="Valor ADC del MQ-7")
    MQ9: float = Field(..., description="Valor ADC del MQ-9")
    temp: float = Field(..., description="Temperatura DHT22 °C")
    humedad: float = Field(..., description="Humedad relativa DHT22 %")

CSV_G1 = os.path.join(BASE_DIR, "registros_grifo_1.csv")
CSV_G2 = os.path.join(BASE_DIR, "registros_grifo_2.csv")
CSV_G3 = os.path.join(BASE_DIR, "registros_grifo_3.csv")

def obtener_csv_por_grifo(grifo_codigo: str) -> str:
    if grifo_codigo == "Grifo_1":
        return CSV_G1
    elif grifo_codigo == "Grifo_2":
        return CSV_G2
    else:
        return CSV_G3

def inicializar_csv_si_falta(filepath: str):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        with open(filepath, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["muestra_id", "origen_grifo", "timestep", "MQ2", "MQ4", "MQ135", "MQ3", "MQ7", "MQ9", "temp", "humedad"])

def contar_muestras_existentes():
    for csv_path in [CSV_G1, CSV_G2, CSV_G3]:
        inicializar_csv_si_falta(csv_path)

    def contar_ids(filepath):
        if not os.path.exists(filepath):
            return 0
        muestras = set()
        with open(filepath, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                m_id = row.get("muestra_id")
                if m_id:
                    muestras.add(m_id)
        return len(muestras)

    estado.muestras_grifo_1 = contar_ids(CSV_G1)
    estado.muestras_grifo_2 = contar_ids(CSV_G2)
    estado.muestras_grifo_3 = contar_ids(CSV_G3)
    estado.total_muestras = estado.muestras_grifo_1 + estado.muestras_grifo_2 + estado.muestras_grifo_3

@app.post("/sensor_data")
async def recibir_telemetria(data: SensorDataPayload):
    payload_dict = data.model_dump()
    estado.ultima_telemetria = payload_dict

    if not estado.grabando_activo or estado.modo_diagnostico:
        return {"status": "ok", "mode": "standby", "message": "Telemetría recibida en Standby"}

    estado.buffer_actual.append(payload_dict)

    if len(estado.buffer_actual) >= 30:
        estado.total_muestras += 1
        nuevo_id = f"MUESTRA_{estado.total_muestras:03d}"

        target_csv = obtener_csv_por_grifo(estado.grifo_actual)
        inicializar_csv_si_falta(target_csv)
        
        try:
            with open(target_csv, mode='a', newline='') as f:
                writer = csv.writer(f)
                for t_idx, item in enumerate(estado.buffer_actual):
                    writer.writerow([
                        nuevo_id,
                        estado.grifo_actual,
                        t_idx + 1,
                        item['MQ2'],
                        item['MQ4'],
                        item['MQ135'],
                        item['MQ3'],
                        item['MQ7'],
                        item['MQ9'],
                        item['temp'],
                        item['humedad']
                    ])
        except PermissionError:
            print(f"\n❌ [ERROR DE PERMISO] No se pudo escribir en {target_csv}. ¡Por favor cierre el archivo en Excel o Block de Notas!")

        # Sincronizar también con el CSV consolidado registros_gasolina_50.csv
        try:
            inicializar_csv_si_falta(CSV_FILE)
            with open(CSV_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                for t_idx, item in enumerate(estado.buffer_actual):
                    writer.writerow([
                        nuevo_id,
                        estado.grifo_actual,
                        t_idx + 1,
                        item['MQ2'],
                        item['MQ4'],
                        item['MQ135'],
                        item['MQ3'],
                        item['MQ7'],
                        item['MQ9'],
                        item['temp'],
                        item['humedad']
                    ])
        except PermissionError:
            print(f"\n❌ [ERROR DE PERMISO] No se pudo escribir en {CSV_FILE}. ¡Cierre el archivo en Excel!")

        estado.buffer_actual = []
        estado.grabando_activo = False

    return {"status": "ok", "samples_accumulated": len(estado.buffer_actual)}

def realizar_chequeo_salud():
    print("\n======================================================================")
    print("        MONITOREO EN VIVO Y DIAGNÓSTICO DE SENSORES (PRE-FLIGHT)")
    print("======================================================================")
    print("  Mostrando lecturas en vivo recibidas por WiFi del ESP32...")
    print("  Presione Enter o espere 8 segundos para volver al menú principal.\n")

    estado.modo_diagnostico = True
    canales = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']

    for i in range(8):
        time.sleep(1)
        if not estado.ultima_telemetria:
            print("  ⏳ Esperando primera trama del ESP32...", end="\r")
            continue

        data = estado.ultima_telemetria
        print(f"\n--- [Lectura en Vivo #{i+1} | IP ESP32 Conectado] ---")
        fallas = 0
        for c in canales:
            val = data.get(c, 0)
            status_str = "🟢 [OK - SALUDABLE]"
            if c in ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9']:
                volt = val * (4.096 / 32768.0)
                if val <= 50:
                    status_str = "🔴 [ERROR - DESCONECTADO (0 ADC)]"
                    fallas += 1
                elif val >= 65530:
                    status_str = "🔴 [ERROR - CORTOCIRCUITO (MAX ADC)]"
                    fallas += 1
                lectura_str = f"{val:5.0f} ADC ({volt:.3f} V)"
            elif c == 'temp':
                if val < 5 or val > 60:
                    status_str = "🔴 [ERROR - TEMP FUERA DE RANGO]"
                    fallas += 1
                lectura_str = f"{val:5.1f} °C"
            elif c == 'humedad':
                if val < 10 or val > 98:
                    status_str = "🔴 [ERROR - HUMEDAD FUERA DE RANGO]"
                    fallas += 1
                lectura_str = f"{val:5.1f} %"

            print(f"  {c:<10} : {lectura_str:<22} | {status_str}")

    estado.modo_diagnostico = False
    print("======================================================================")
    if fallas == 0:
        print("  ✅ RESULTADO: Todos los sensores están funcionando al 100%. ¡Listo para calibrar!")
    else:
        print(f"  ⚠️ RESULTADO: Se observaron algunas anomalías. Verifique el estado de las conexiones.")
    print("======================================================================")

def ejecutar_toma_manual(grifo_codigo: str, meta: int):
    estado.grifo_actual = grifo_codigo
    contar_muestras_existentes()

    actuales = estado.muestras_grifo_1 if grifo_codigo == "Grifo_1" else (estado.muestras_grifo_2 if grifo_codigo == "Grifo_2" else estado.muestras_grifo_3)

    print(f"\n======================================================================")
    print(f"  INICIANDO CAPTURA AUTOMÁTICA: {grifo_codigo.upper()} (Meta: {meta} Muestras)")
    print(f"======================================================================")

    if actuales >= meta:
        print(f"  ✅ El origen {grifo_codigo} ya tiene completadas sus {meta} muestras.")
        return

    print(f"  🟢 Grabando de corrido las muestras restantes para {grifo_codigo} (30s por muestra)...")

    while actuales < meta:
        estado.buffer_actual = []
        estado.grabando_activo = True

        muestra_num_actual = estado.total_muestras + 1
        print(f"\n  ▶️ [GRABANDO] MUESTRA_{muestra_num_actual:03d} ({grifo_codigo}) - Esperando 30 segundos...")

        while estado.grabando_activo:
            time.sleep(1)
            seg_esperados = len(estado.buffer_actual)
            print(f"     ➡️ Transcurridos {seg_esperados}/30 segundos del lote...", end="\r")

        contar_muestras_existentes()
        actuales = estado.muestras_grifo_1 if grifo_codigo == "Grifo_1" else (estado.muestras_grifo_2 if grifo_codigo == "Grifo_2" else estado.muestras_grifo_3)
        print(f"\n  ✅ ¡MUESTRA_{estado.total_muestras:03d} ({grifo_codigo}) GUARDADA EN CSV! Progreso {grifo_codigo}: {actuales}/{meta}")

    print(f"\n🎉 ¡COMPLETADAS LAS {meta} MUESTRAS PARA {grifo_codigo.upper()}!")
    print("======================================================================")

if __name__ == "__main__":
    contar_muestras_existentes()
    print("======================================================================")
    print("     INICIANDO SERVIDOR DE CALIBRACIÓN REAL DE SENSORES (LAPTOP)")
    print("======================================================================")
    print(f"  Directorio: {BASE_DIR}")
    print(f"  Archivo de datos: {CSV_FILE}")
    print(f"  Muestras actuales registradas: {estado.total_muestras}/50")
    print(f"    - Grifo 1: {estado.muestras_grifo_1}/17")
    print(f"    - Grifo 2: {estado.muestras_grifo_2}/17")
    print(f"    - Grifo 3: {estado.muestras_grifo_3}/16")
    print("======================================================================")
    print("  Estado del Servidor: STANDBY SEGURO (No se graba nada sin su orden)")
    print("======================================================================")

    # Iniciar servidor Uvicorn en segundo plano
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="error")
    server = uvicorn.Server(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Iniciar servidor en hilo alterno
    import threading
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    time.sleep(1)

    while True:
        contar_muestras_existentes()
        print("\nMENÚ DE OPCIONES DE CALIBRACIÓN:")
        print("  [0] -> Ejecutar Diagnóstico y Monitoreo en Vivo (Pre-flight Check)")
        print(f"  [1] -> Iniciar Toma para GRIFO 1 (Actual: {estado.muestras_grifo_1}/17)")
        print(f"  [2] -> Iniciar Toma para GRIFO 2 (Actual: {estado.muestras_grifo_2}/17)")
        print(f"  [3] -> Iniciar Toma para GRIFO 3 (Actual: {estado.muestras_grifo_3}/16)")
        print("  [4] -> Ver Avance Global y Conteo")
        print("  [5] -> Salir y Finalizar Captura")

        opcion = input("\nIngrese opción [0-5]: ").strip()

        if opcion == "0":
            realizar_chequeo_salud()
        elif opcion == "1":
            ejecutar_toma_manual("Grifo_1", 17)
        elif opcion == "2":
            ejecutar_toma_manual("Grifo_2", 17)
        elif opcion == "3":
            ejecutar_toma_manual("Grifo_3", 16)
        elif opcion == "4":
            contar_muestras_existentes()
            print(f"\n📊 RESUMEN DE MUESTRAS CAPTURADAS:")
            print(f"   Grifo 1 : {estado.muestras_grifo_1}/17")
            print(f"   Grifo 2 : {estado.muestras_grifo_2}/17")
            print(f"   Grifo 3 : {estado.muestras_grifo_3}/16")
            print(f"   TOTAL   : {estado.total_muestras}/50")
        elif opcion == "5":
            print("\n👋 Cerrando servidor de calibración. ¡Hasta pronto!")
            break
        else:
            print("❌ Opción no válida. Intente nuevamente.")
