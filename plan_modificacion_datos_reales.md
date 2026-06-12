# Plan de Modificación: Modelo con Datos Reales de Gasolina como Referencia

**Proyecto:** Sistema de Nariz Electrónica — Deep Learning  
**Modificación clave:** Reemplazar datos simulados por datos reales usando gasolina de 90 octanos como patrón de referencia de calidad  
**Autor:** Junior Quispe Aquino — Universidad Continental, Huancayo

---

## Concepto central del enfoque

La gasolina comercial de 90 octanos tiene una composición química conocida y estable. Al exponer los sensores MOS a sus vapores, obtenemos una "firma química de referencia". El modelo aprende esa firma y luego evalúa qué tan parecido o diferente es el bio-oil producido por pirólisis de plásticos.

```
Gasolina 90 → sensores → firma de referencia ──┐
                                                ├─→ modelo aprende la diferencia
Bio-oil pirólisis → sensores → firma desconocida┘
```

La calidad del bio-oil se define como **qué tan similar es su firma a la de la gasolina 90**. No necesitas laboratorio de cromatografía para esto — la nariz electrónica hace esa comparación por ti.

---

## Cambio en las etiquetas del dataset

### Antes (datos simulados)
```
alta_calidad / media_calidad / baja_calidad
```

### Ahora (datos reales con gasolina como referencia)
```
gasolina_90          ← tu referencia, la "calidad perfecta"
bio_oil_similar      ← bio-oil cuyo perfil se parece a la gasolina 90
bio_oil_intermedio   ← bio-oil con diferencias notables
bio_oil_diferente    ← bio-oil muy distinto a la gasolina 90
```

El criterio de qué clase asignar a cada experimento de bio-oil lo defines **después de ver los datos** comparando visualmente los perfiles de señal con los de la gasolina. Se explica en detalle en la Fase 1.

---

## Fase 1 — Protocolo de recolección de datos reales

### Materiales necesarios

| Material | Dónde conseguir en Huancayo | Cantidad |
|---|---|---|
| Gasolina 90 octanos | Grifo / estación de servicio | 500 mL |
| Recipiente hermético de vidrio | Ferretería / laboratorio | 3 unidades |
| Bio-oil de pirólisis (PE, PET, mezcla) | Tu reactor de pirólisis | Lo que produzcas |
| Ventilador pequeño 5V (purga) | Ya está en tu cotización | 1 unidad |
| Manguera / tubo de silicona | Ferretería | 50 cm |

### Protocolo de experimento (paso a paso)

#### Paso 1 — Preparar la cámara de gases
Coloca la cámara hermética con la muestra líquida dentro. Deja reposar 5 minutos para que los vapores se acumulen en el espacio superior (headspace).

#### Paso 2 — Precalentar sensores
Enciende el ESP32 y espera **60 segundos** antes de empezar a capturar. Los sensores MOS necesitan ese tiempo para estabilizarse térmicamente.

#### Paso 3 — Capturar datos
Conecta la salida de gases de la cámara a la cámara de sensores. El script del ESP32 empieza a grabar automáticamente durante **60 segundos** (60 lecturas de 1s cada una).

#### Paso 4 — Purgar
Activa el ventilador 5V durante 30 segundos para limpiar los sensores antes de la siguiente muestra. Crítico para que los sensores vuelvan a su línea base.

#### Paso 5 — Repetir
Mínimo **50 repeticiones por tipo de muestra**. Si tienes tiempo, apunta a 100.

#### Paso 6 — Etiquetar
Anota en tu hoja de registro qué muestra es cada experimento. Después del análisis visual asignas la clase (ver Fase 3).

### Hoja de registro de experimentos

```
ID_exp | Tipo_muestra        | Fecha     | Temp_amb | Hum_amb | Notas
-------|---------------------|-----------|----------|---------|------
001    | gasolina_90         | 2024-05-01| 18°C     | 65%     | OK
002    | gasolina_90         | 2024-05-01| 18°C     | 65%     | OK
...
051    | bio_oil_PE          | 2024-05-03| 19°C     | 63%     | olor fuerte
052    | bio_oil_PE          | 2024-05-03| 19°C     | 63%     | OK
...
```

### Cuántos experimentos necesitas

| Tipo de muestra | Experimentos mínimos | Experimentos recomendados |
|---|---|---|
| Gasolina 90 (referencia) | 80 | 150 |
| Bio-oil PE | 50 | 100 |
| Bio-oil PET | 50 | 100 |
| Bio-oil mezcla plásticos | 50 | 100 |
| **Total** | **230** | **450** |

Cada experimento tiene 60 lecturas → con 450 experimentos tendrás ~27,000 filas en el CSV.

---

## Fase 2 — Modificación del generador de datos

El archivo `data/generar_datos.py` ya no se usa para entrenamiento real. Se reemplaza por `data/leer_esp32.py` que graba datos del ESP32 directamente.

### Nuevo archivo: `data/leer_esp32.py`

```python
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

    ser = serial.Serial(PUERTO, BAUDRATE, timeout=2)
    time.sleep(2)  # esperar que el ESP32 reinicie

    print(f"\nEXPERIMENTO {muestra_id}")
    print(f"Capturando {DURACION_SEG} lecturas...")

    filas = []
    for t in range(DURACION_SEG):
        linea = ser.readline().decode('utf-8').strip()
        try:
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

    # Guardar al CSV acumulando (append)
    with open(ruta_csv, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        if not archivo_existe:
            writer.writeheader()
        writer.writerows(filas)

    print(f"\nGuardado: {len(filas)} lecturas → {ruta_csv}")
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
    sesion_de_captura()
```

---

## Fase 3 — Análisis visual y etiquetado por similitud

Esta es la fase más importante del enfoque. Antes de entrenar, necesitas ver los datos y decidir qué bio-oils son similares a la gasolina.

### Nuevo archivo: `data/analizar_similitud.py`

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

SENSORES = ['MQ2','MQ4','MQ135','MQ3','MQ7','MQ9','temp','humedad']

df = pd.read_csv('data/datos_reales.csv')

# Promediar cada experimento (una fila por experimento)
df_exp = df.groupby(['muestra_id','etiqueta'])[SENSORES].mean().reset_index()

# Normalizar
scaler = StandardScaler()
X_norm = scaler.fit_transform(df_exp[SENSORES])

# Reducir a 2D con PCA para visualizar
pca = PCA(n_components=2)
X_2d = pca.fit_transform(X_norm)
df_exp['PCA1'] = X_2d[:, 0]
df_exp['PCA2'] = X_2d[:, 1]

# Graficar
colores = {
    'gasolina_90':    'gold',
    'bio_oil_PE':     'steelblue',
    'bio_oil_PET':    'tomato',
    'bio_oil_mezcla': 'mediumseagreen',
}
plt.figure(figsize=(10, 7))
for tipo, color in colores.items():
    mask = df_exp['etiqueta'] == tipo
    plt.scatter(df_exp[mask]['PCA1'], df_exp[mask]['PCA2'],
                c=color, label=tipo, alpha=0.7, s=60)

plt.title('Mapa de similitud: gasolina vs bio-oil\n(PCA sobre señales promedio de sensores)')
plt.xlabel(f'Componente 1 ({pca.explained_variance_ratio_[0]*100:.1f}% varianza)')
plt.ylabel(f'Componente 2 ({pca.explained_variance_ratio_[1]*100:.1f}% varianza)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('data/mapa_similitud.png', dpi=120)
plt.show()
print("Gráfico guardado en data/mapa_similitud.png")
```

### Cómo interpretar el gráfico PCA

El gráfico muestra cada experimento como un punto. La **gasolina 90** forma un cluster (grupo) dorado. Los bio-oils que caen **cerca de ese cluster** son similares a la gasolina — esos son tus candidatos a "buena calidad".

```
Ejemplo de lo que verás:

      ●●● gasolina_90 (cluster dorado)
    ○○○ bio_oil_PE cercano  ← similar = buena calidad
                    △△△ bio_oil_PET lejos ← diferente
```

### Reetiquetado basado en distancia

```python
# Calcular distancia de cada bio-oil al centroide de gasolina_90
centroide_gasolina = X_norm[df_exp['etiqueta'] == 'gasolina_90'].mean(axis=0)
distancias = np.linalg.norm(X_norm - centroide_gasolina, axis=1)
df_exp['distancia_gasolina'] = distancias

# Asignar clase de calidad según distancia
def asignar_clase(row):
    if row['etiqueta'] == 'gasolina_90':
        return 'referencia'
    d = row['distancia_gasolina']
    if   d < 1.5:  return 'bio_oil_similar'       # muy parecido a gasolina
    elif d < 3.0:  return 'bio_oil_intermedio'     # diferencias notables
    else:          return 'bio_oil_diferente'       # muy distinto

df_exp['clase_calidad'] = df_exp.apply(asignar_clase, axis=1)
print(df_exp['clase_calidad'].value_counts())

# Guardar dataset con nuevas clases
df_exp.to_csv('data/datos_etiquetados.csv', index=False)
```

Los umbrales de distancia (1.5, 3.0) los ajustas tú según lo que veas en el gráfico PCA. No hay valor fijo — depende de qué tan dispersos estén tus datos reales.

---

## Fase 4 — Modificaciones al modelo GCN-LSTM

### Cambios en `preprocessing/preprocesar.py`

Solo cambiar la fuente de datos:

```python
# ANTES (datos simulados):
df = pd.read_csv('data/datos_sensores.csv')

# AHORA (datos reales etiquetados):
df = pd.read_csv('data/datos_etiquetados.csv')

# Y cambiar la columna de etiqueta:
# ANTES: df['etiqueta_num'] = le.fit_transform(df['etiqueta'])
# AHORA:
df['etiqueta_num'] = le.fit_transform(df['clase_calidad'])
```

### Cambios en `model/gcn_lstm.py`

Ninguno en la arquitectura. Solo ajustar `n_clases` si cambias el número de clases:

```python
# Si usas 4 clases (referencia + similar + intermedio + diferente):
modelo = construir_modelo(n_clases=4)

# Si simplificas a 3 (referencia + buena_calidad + mala_calidad):
modelo = construir_modelo(n_clases=3)
```

### Cambios en `train.py`

```python
# Línea que cambia:
# ANTES:
exec(open('data/generar_datos.py').read())

# AHORA (no generar datos, ya los tienes reales):
# Simplemente verificar que el archivo existe
if not os.path.exists('data/datos_etiquetados.csv'):
    raise FileNotFoundError("Primero ejecuta data/analizar_similitud.py para etiquetar los datos")
```

---

## Fase 5 — Nuevo script de inferencia con descripción de diferencias

Cuando el modelo clasifica una muestra de bio-oil, además de la clase, queremos saber **en qué se diferencia de la gasolina**.

### Nuevo archivo: `inferencia_con_diagnostico.py`

```python
import numpy as np
import pickle
import tflite_runtime.interpreter as tflite

SENSORES = ['MQ2','MQ4','MQ135','MQ3','MOS','MQ9','temp','humedad']

DIAGNOSTICOS = {
    'MQ7':    ('CO elevado',      'Combustión incompleta — temperatura de pirólisis muy baja'),
    'MQ135':  ('VOCs elevados',   'Presencia de benceno/tolueno — pirólisis incompleta'),
    'MQ4':    ('CH4 elevado',     'Exceso de metano — temperatura óptima no alcanzada'),
    'MQ2':    ('GLP elevado',     'Fracción liviana alta — condensación insuficiente'),
    'MQ3':    ('Alcoholes altos', 'Posible contaminación por PET o plástico mixto'),
    'temp':   ('Temp. inestable', 'Revisar control de temperatura del reactor'),
    'humedad':('Humedad alta',    'Humedad ambiental afectando lectura — revisar condiciones'),
}

def diagnosticar(muestra_norm, perfil_gasolina_norm):
    """Compara una muestra contra el perfil promedio de gasolina e identifica diferencias."""
    diferencias = muestra_norm - perfil_gasolina_norm
    alertas = []
    for i, sensor in enumerate(SENSORES):
        if abs(diferencias[i]) > 1.0:   # más de 1 desviación estándar de diferencia
            direccion = 'alto' if diferencias[i] > 0 else 'bajo'
            if sensor in DIAGNOSTICOS:
                titulo, causa = DIAGNOSTICOS[sensor]
                alertas.append(f"  ⚠ {sensor} {direccion}: {titulo} → {causa}")
    return alertas if alertas else ["  ✓ Perfil similar a gasolina 90 — sin alertas"]
```

---

## Resumen de archivos modificados y nuevos

| Archivo | Estado | Cambio |
|---|---|---|
| `data/generar_datos.py` | Solo para práctica | Ya no se usa en producción |
| `data/leer_esp32.py` | **NUEVO** | Captura datos reales del ESP32 |
| `data/analizar_similitud.py` | **NUEVO** | PCA + etiquetado por distancia a gasolina |
| `data/datos_reales.csv` | **NUEVO** | Dataset real capturado |
| `data/datos_etiquetados.csv` | **NUEVO** | Dataset con clases de calidad asignadas |
| `preprocessing/preprocesar.py` | Modificado | Cambia fuente de datos y columna de etiqueta |
| `model/gcn_lstm.py` | Sin cambios | Arquitectura válida para datos reales |
| `train.py` | Modificado mínimo | Apunta a datos etiquetados reales |
| `inferencia_con_diagnostico.py` | **NUEVO** | Explica en qué difiere del patrón gasolina |

---

## Cronograma actualizado

| Semana | Actividad |
|---|---|
| 1 | Comprar gasolina 90, montar cámara hermética, probar protocolo de purga |
| 2–3 | Capturar 150 experimentos de gasolina 90 (línea base) |
| 4–5 | Producir bio-oil con PE, PET y mezcla — capturar 100 exp. por tipo |
| 6 | Correr `analizar_similitud.py`, ver PCA, ajustar umbrales y etiquetar |
| 7 | Reentrenar modelo con datos reales, evaluar métricas |
| 8 | Validar con muestras nuevas, ajustar diagnósticos, cerrar sistema |

---

## Notas importantes

1. **La gasolina es inflamable.** Trabajar en ambiente ventilado, lejos de fuentes de calor. Usar recipientes de vidrio, nunca plástico.

2. **Capturar gasolina primero.** Asegúrate de tener al menos 80 experimentos de gasolina antes de empezar con el bio-oil. Es tu referencia y necesitas que sea sólida.

3. **Mismas condiciones ambientales.** Intentar capturar todos los experimentos con temperatura y humedad similares, o al menos registrarlas siempre. El DHT22 compensará las diferencias en el modelo.

4. **Los umbrales de distancia son tuyos.** No existe un valor universal para decidir qué es "similar" a la gasolina. El gráfico PCA te lo dirá visualmente — confía en lo que veas.

5. **Registrar lote de plástico.** El tipo de plástico (PE vs PET vs mezcla) y el lote afectan el bio-oil. Anótalo siempre en la hoja de registro para poder analizar patrones después.
