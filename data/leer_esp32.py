import serial
import csv
import time
import os
from datetime import datetime

# Configura el puerto serie del ESP32
# Windows: 'COM3', 'COM4', etc.
# Linux/RPi: '/dev/ttyUSB0'
PUERTO       = 'COM3'
BAUDRATE     = 115200
DURACION_SEG = 120         # 120 segundos por experimento para la bitácora
SENSORES     = ['MQ2','MQ4','MQ135','MQ3','MQ7','MQ9','temp','humedad']

def obtener_ultimo_lote(ruta_csv='data/datos_reales.csv'):
    """Retorna el último número de lote registrado para autoincrementar."""
    if not os.path.exists(ruta_csv):
        return 0
    try:
        with open(ruta_csv, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers or 'muestra_id' not in headers:
                return 0
            idx = headers.index('muestra_id')
            last_id = None
            for row in reader:
                if len(row) > idx:
                    last_id = row[idx]
            if last_id and last_id.startswith('lote_'):
                return int(last_id.split('_')[1])
    except Exception:
        pass
    return 0

def grabar_experimento(etiqueta, tipo_plastico, temp_max, id_exp, ruta_csv='data/datos_reales.csv'):
    """
    Graba un experimento completo de 120 segundos.
    etiqueta: 'ALTA', 'MEDIA', 'BAJA' (Etiqueta real / Ground Truth)
    tipo_plastico: 'PE', 'PP', 'PS', 'MIX'
    temp_max: Temperatura máxima registrada en el reactor (°C)
    id_exp: número único del lote (ej: 1, 2, 3...)
    """
    muestra_id = f'lote_{id_exp:03d}'
    archivo_existe = os.path.exists(ruta_csv)

    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=2)
        time.sleep(2)  # esperar que el ESP32 reinicie
    except Exception as e:
        print(f"\nError al conectar al puerto serial {PUERTO}: {e}")
        return []

    print(f"\nINICIANDO ADQUISICIÓN LOTE {muestra_id}")
    print(f"Plástico: {tipo_plastico} | Temp. Reactor: {temp_max}°C | Calidad Real: {etiqueta}")
    print(f"Capturando {DURACION_SEG} lecturas (Frecuencia: 1 Hz, Resolución: 16 bits)...")

    filas = []
    for t in range(DURACION_SEG):
        try:
            linea = ser.readline().decode('utf-8', errors='ignore').strip()
            if not linea:
                continue
            # Se esperan 8 valores separados por coma del ESP32
            # El ADC externo ADS1115 reporta valores en el rango 16-bit (0-65535)
            valores = list(map(float, linea.split(',')))
            if len(valores) == 8:
                fila = {
                    'tiempo':         t,
                    'muestra_id':     muestra_id,
                    'tipo_plastico':  tipo_plastico,
                    'temp_max':       temp_max,
                    'frec_muestreo':  1.0,   # 1 Hz
                    'res_adc':        16,    # 16 bits (ADS1115)
                    'etiqueta':       etiqueta
                }
                for i, sensor in enumerate(SENSORES):
                    fila[sensor] = round(valores[i], 2)
                filas.append(fila)
                print(f"  t={t:3d}s | MQ7(CO)={valores[4]:.0f} | temp={valores[6]:.1f}°C", end='\r')
        except Exception as e:
            print(f"\n  Error en t={t}: {e}")

    ser.close()

    if filas:
        # Guardar al CSV acumulando (append)
        with open(ruta_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            if not archivo_existe:
                writer.writeheader()
            writer.writerows(filas)
        print(f"\nGuardado: {len(filas)} lecturas → {ruta_csv}")
    else:
        print("\nNo se capturaron lecturas válidas. No se guardó nada.")

    return filas


def sesion_de_captura():
    """Menú interactivo para capturar múltiples experimentos."""
    os.makedirs('data', exist_ok=True)
    
    tipos_plastico = {
        '1': 'PE',
        '2': 'PP',
        '3': 'PS',
        '4': 'MIX',
    }
    
    clases_calidad = {
        '1': 'ALTA',
        '2': 'MEDIA',
        '3': 'BAJA',
    }

    ultimo_lote = obtener_ultimo_lote()
    print("=" * 50)
    print("SISTEMA DE CAPTURA DE LOTES — NARIZ ELECTRÓNICA")
    print(f"Último lote registrado: lote_{ultimo_lote:03d}")
    print("=" * 50)

    while True:
        print("\n¿Desea registrar un nuevo lote experimental?")
        print("  1. Registrar Lote")
        print("  0. Salir")
        opcion = input("\nOpción: ").strip()

        if opcion == '0':
            break
        if opcion != '1':
            print("Opción inválida.")
            continue

        ultimo_lote += 1

        # 1. Tipo de Plástico
        tipo_p = None
        while not tipo_p:
            print("\nSeleccione el tipo de plástico ingresado:")
            for k, v in tipos_plastico.items():
                print(f"  {k}. {v}")
            op_p = input("Opción: ").strip()
            tipo_p = tipos_plastico.get(op_p)

        # 2. Temperatura Máxima del Reactor
        temp_max = None
        while not temp_max:
            try:
                temp_max = float(input("\nIngrese la temperatura máxima del reactor (°C): ").strip())
            except ValueError:
                print("Temperatura inválida. Ingrese un valor numérico.")

        # 3. Etiqueta Real (Ground Truth)
        etiqueta = None
        while not etiqueta:
            print("\nSeleccione el análisis de calidad real (Ground Truth):")
            for k, v in clases_calidad.items():
                print(f"  {k}. {v}")
            op_c = input("Opción: ").strip()
            etiqueta = clases_calidad.get(op_c)

        input(f"\nColoque la muestra de {tipo_p} ({temp_max}°C) y presione ENTER para iniciar la captura...")
        grabar_experimento(etiqueta, tipo_p, temp_max, ultimo_lote)

        print("\nPurgando sensores (30 segundos)...")
        time.sleep(30)
        print("Listo para el siguiente lote.")

    print("\nSesión terminada. Datos guardados en data/datos_reales.csv")


if __name__ == '__main__':
    sesion_de_captura()
