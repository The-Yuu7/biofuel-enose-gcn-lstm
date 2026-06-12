import serial
import csv
import time
import os
from datetime import datetime

# Configura el puerto serie del ESP32
# Windows: 'COM3', 'COM4', etc. (ver en Administrador de dispositivos)
# Linux/RPi: '/dev/ttyUSB0'
PUERTO       = 'COM3'
BAUDRATE     = 115200
DURACION_SEG = 60          # segundos por experimento
SENSORES     = ['MQ2','MQ4','MQ135','MQ3','MQ7','MQ9','temp','humedad']

def grabar_experimento(etiqueta, id_exp, ruta_csv='data/datos_reales.csv'):
    """
    Graba un experimento completo de 60 segundos.
    etiqueta: 'gasolina_90', 'bio_oil_PE', 'bio_oil_PET', 'bio_oil_mezcla'
    id_exp:   número único del experimento (ej: 1, 2, 3...)
    """
    muestra_id = f'{etiqueta}_{id_exp:03d}'
    archivo_existe = os.path.exists(ruta_csv)

    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=2)
        time.sleep(2)  # esperar que el ESP32 reinicie
    except Exception as e:
        print(f"\nError al conectar al puerto serial {PUERTO}: {e}")
        return []

    print(f"\nEXPERIMENTO {muestra_id}")
    print(f"Capturando {DURACION_SEG} lecturas...")

    filas = []
    for t in range(DURACION_SEG):
        try:
            linea = ser.readline().decode('utf-8', errors='ignore').strip()
            if not linea:
                continue
            valores = list(map(float, linea.split(',')))
            if len(valores) == 8:
                fila = {
                    'tiempo':     t,
                    'muestra_id': muestra_id,
                    'etiqueta':   etiqueta,   # se puede cambiar después
                }
                for i, sensor in enumerate(SENSORES):
                    fila[sensor] = round(valores[i], 2)
                filas.append(fila)
                print(f"  t={t:2d}s | MQ7(CO)={valores[4]:.0f} | temp={valores[6]:.1f}°C", end='\r')
        except Exception as e:
            print(f"  Error en t={t}: {e}")

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
    tipos = {
        '1': 'gasolina_90',
        '2': 'bio_oil_PE',
        '3': 'bio_oil_PET',
        '4': 'bio_oil_mezcla',
    }
    contadores = {t: 0 for t in tipos.values()}

    print("=" * 50)
    print("SISTEMA DE CAPTURA — NARIZ ELECTRÓNICA")
    print("=" * 50)

    while True:
        print("\n¿Qué muestra vas a medir?")
        for k, v in tipos.items():
            print(f"  {k}. {v}  (ya capturadas: {contadores[v]})")
        print("  0. Salir")
        opcion = input("\nOpción: ").strip()

        if opcion == '0':
            break
        if opcion not in tipos:
            print("Opción inválida.")
            continue

        etiqueta = tipos[opcion]
        contadores[etiqueta] += 1
        id_exp = contadores[etiqueta]

        input(f"\nColoca la muestra de '{etiqueta}' y presiona ENTER para iniciar...")
        grabar_experimento(etiqueta, id_exp)

        print("\nPurgando sensores (30 segundos)...")
        time.sleep(30)
        print("Listo para siguiente muestra.")

    print("\nSesión terminada.")
    print("Dataset guardado en data/datos_reales.csv")


if __name__ == '__main__':
    # Asegurar que el directorio data exista
    os.makedirs('data', exist_ok=True)
    sesion_de_captura()
