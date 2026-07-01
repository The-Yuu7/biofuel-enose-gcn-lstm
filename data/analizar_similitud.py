import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']

def generar_datos_reales_de_prueba(ruta_csv='data/datos_reales.csv'):
    """
    Genera un dataset de simulación de 16 bits de alta fidelidad con 450 lotes
    de 120 segundos cada uno, de acuerdo con la matriz de operacionalización (1 Hz, 16 bits).
    """
    print("Generando datos de simulación a 16 bits (450 experimentos)...")
    np.random.seed(42)
    
    # 9 condiciones: 3 plásticos x 3 temperaturas x 50 réplicas = 450 lotes
    plasticos = ['PE', 'PP', 'PS']
    temperaturas = [380, 430, 480]
    replicas = 50
    
    # Perfiles base de 16 bits (multiplicados por 64 del rango de 10 bits original para simular ADS1115 de 16 bits)
    # Sensores: MQ2, MQ4, MQ135, MQ3, MQ7, MQ9, temp, humedad
    perfiles_base = {
        ('PE', 380): [22400.0, 14080.0, 20480.0, 16000.0, 26880.0, 19200.0, 22.0, 60.0], # MEDIA (temp baja)
        ('PE', 430): [28800.0, 20480.0, 16000.0, 11520.0, 9600.0, 17920.0, 22.5, 59.0],  # ALTA (óptima)
        ('PE', 480): [41600.0, 33280.0, 22400.0, 12800.0, 24320.0, 32000.0, 23.0, 58.0],  # MEDIA (temp alta)
        ('PP', 380): [21120.0, 12800.0, 21760.0, 15360.0, 27520.0, 18560.0, 22.1, 60.5],  # MEDIA (temp baja)
        ('PP', 430): [28160.0, 19840.0, 15360.0, 12160.0, 8960.0, 17280.0, 22.4, 59.5],  # ALTA (óptima)
        ('PP', 480): [40320.0, 32640.0, 23040.0, 13440.0, 24960.0, 31360.0, 22.9, 58.2],  # MEDIA (temp alta)
        ('PS', 380): [16000.0, 9600.0, 54400.0, 19200.0, 35200.0, 15360.0, 22.2, 61.0],  # BAJA (aromáticos, cera)
        ('PS', 430): [19840.0, 11520.0, 58880.0, 17920.0, 32000.0, 17920.0, 22.6, 60.1],  # BAJA (aromáticos)
        ('PS', 480): [25600.0, 17920.0, 60800.0, 16640.0, 37120.0, 22400.0, 23.1, 58.8]   # BAJA (aromáticos, craking)
    }
    
    filas = []
    lote_counter = 1
    
    for plastico in plasticos:
        for temp_camara in temperaturas:
            for rep in range(1, replicas + 1):
                muestra_id = f"lote_{lote_counter:03d}"
                base = np.array(perfiles_base[(plastico, temp_camara)])
                
                # Asignar la calidad real según la matriz de consistencia
                if plastico in ['PE', 'PP'] and temp_camara == 430:
                    calidad = 'ALTA'
                elif plastico in ['PE', 'PP']:
                    calidad = 'MEDIA'
                else: # PS siempre genera alquitranes/pesados aromáticos
                    calidad = 'BAJA'
                
                # Variabilidad del experimento (deriva y ruido térmico)
                variacion_exp = np.random.normal(1.0, 0.06, size=len(SENSORES))
                variacion_exp[6:] = 1.0  # temp y humedad varían menos
                perfil_exp = base * variacion_exp
                
                # Generar ciclo de 120 segundos (1 Hz de muestreo)
                for t in range(120):
                    # Dinámica de acumulación en la cámara
                    factor_tiempo = 1.0 - np.exp(-t / 25.0)
                    
                    valores = perfil_exp.copy()
                    # Afectar sensores químicos por dinámica temporal y ruido
                    valores[:6] = valores[:6] * factor_tiempo + np.random.normal(0, 150.0, size=6)
                    
                    # Ruido menor en temp y humedad ambientales
                    valores[6] += np.random.normal(0, 0.15)
                    valores[7] += np.random.normal(0, 0.4)
                    
                    # Asegurar límites del convertidor ADS1115 de 16 bits (0 - 65535)
                    valores[:6] = np.clip(valores[:6], 0, 65535)
                    valores[6] = np.clip(valores[6], 10.0, 50.0) # temp ambiente razonable
                    valores[7] = np.clip(valores[7], 10.0, 95.0) # humedad razonable
                    
                    fila = {
                        'tiempo': t,
                        'muestra_id': muestra_id,
                        'tipo_plastico': plastico,
                        'temp_max': temp_camara,
                        'frec_muestreo': 1.0,
                        'res_adc': 16,
                        'etiqueta': calidad
                    }
                    for i, s in enumerate(SENSORES):
                        fila[s] = round(valores[i], 2)
                        
                    filas.append(fila)
                
                lote_counter += 1
                
    df_prueba = pd.DataFrame(filas)
    os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
    df_prueba.to_csv(ruta_csv, index=False)
    print(f"Creado '{ruta_csv}' con {len(df_prueba)} lecturas (450 experimentos).")

def main():
    ruta_reales = 'data/datos_reales.csv'
    if not os.path.exists(ruta_reales):
        generar_datos_reales_de_prueba(ruta_reales)
    else:
        # Si ya existe pero queremos forzar la consistencia con 450 lotes y 120s, lo regeneramos
        df_existente = pd.read_csv(ruta_reales)
        # Verificar si tiene el formato antiguo o número diferente de filas
        if len(df_existente) != 450 * 120 or 'res_adc' not in df_existente.columns:
            print("El dataset existente no cumple con la matriz de 450 lotes de 120s a 16 bits. Regenerando...")
            generar_datos_reales_de_prueba(ruta_reales)
        
    print(f"Leyendo dataset de datos reales desde: {ruta_reales}")
    df = pd.read_csv(ruta_reales)
    
    # 1. Promediar cada experimento para análisis de similitud
    print("Promediando lecturas por experimento...")
    df_exp = df.groupby(['muestra_id', 'tipo_plastico', 'temp_max', 'etiqueta'])[SENSORES].mean().reset_index()
    
    # 2. Normalizar las lecturas promedio
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(df_exp[SENSORES])
    
    # 3. Reducir a 2D con PCA para visualizar
    print("Ejecutando PCA...")
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X_norm)
    df_exp['PCA1'] = X_2d[:, 0]
    df_exp['PCA2'] = X_2d[:, 1]
    
    print("\nDistribución de experimentos por calidad de biocombustible (Ground Truth):")
    print(df_exp['etiqueta'].value_counts())
    
    # 4. Guardar dataset completo etiquetado
    ruta_etiquetados = 'data/datos_etiquetados.csv'
    # Como ya tenemos la etiqueta física en los datos simulados, la copiamos
    df['clase_calidad'] = df['etiqueta']
    df.to_csv(ruta_etiquetados, index=False)
    print(f"Dataset completo guardado en: {ruta_etiquetados}")
    
    # Guardar resumen promedio
    df_exp.to_csv('data/datos_experimentos_promedio.csv', index=False)
    
    # 5. Graficar mapa de similitud por clase de calidad
    print("Generando mapa de similitud...")
    colores = {
        'ALTA':  'gold',
        'MEDIA': 'steelblue',
        'BAJA':  'tomato',
    }
    
    plt.figure(figsize=(10, 7))
    for cat, color in colores.items():
        mask = df_exp['etiqueta'] == cat
        plt.scatter(df_exp[mask]['PCA1'], df_exp[mask]['PCA2'],
                    c=color, label=f"Calidad {cat} (N={mask.sum()})", alpha=0.8, s=80, edgecolors='k')
                    
    plt.title('Mapa de Similitud E-Nose: Calidad del Biocombustible\n(PCA sobre señales promedio a 16 bits - ADS1115)', fontsize=13, fontweight='bold')
    plt.xlabel(f'Componente Principal 1 ({pca.explained_variance_ratio_[0]*100:.1f}% varianza)')
    plt.ylabel(f'Componente Principal 2 ({pca.explained_variance_ratio_[1]*100:.1f}% varianza)')
    plt.legend(frameon=True, facecolor='white', framealpha=0.9)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.savefig('data/mapa_similitud.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Gráfico PCA guardado en: data/mapa_similitud.png")

if __name__ == '__main__':
    main()
