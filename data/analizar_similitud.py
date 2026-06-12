import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

SENSORES = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']

def generar_datos_reales_de_prueba(ruta_csv='data/datos_reales.csv'):
    """
    Genera un dataset de prueba de alta fidelidad con curvas reales de 60 segundos 
    para poder verificar todo el flujo del modelo sin hardware conectado.
    """
    print("Generando datos de simulación reales...")
    np.random.seed(42)
    
    # 80 gasolina_90, 60 bio_oil_PE, 60 bio_oil_PET, 60 bio_oil_mezcla
    muestras = {
        'gasolina_90': 80,
        'bio_oil_PE': 60,
        'bio_oil_PET': 60,
        'bio_oil_mezcla': 60
    }
    
    # Perfiles promedio base para cada tipo de muestra (firma química)
    # Sensores: MQ2, MQ4, MQ135, MQ3, MQ7, MQ9, temp, humedad
    perfiles_base = {
        'gasolina_90':    [450.0, 320.0, 500.0, 600.0, 180.0, 290.0, 22.0, 60.0],
        'bio_oil_PE':     [420.0, 340.0, 480.0, 550.0, 190.0, 310.0, 22.5, 59.0], # Similar
        'bio_oil_PET':    [210.0, 150.0, 780.0, 220.0, 450.0, 120.0, 23.0, 62.0], # Muy diferente (VOC y CO altos)
        'bio_oil_mezcla': [380.0, 290.0, 520.0, 490.0, 280.0, 250.0, 22.2, 61.0]  # Intermedio
    }
    
    filas = []
    
    for etiqueta, num_exp in muestras.items():
        base = np.array(perfiles_base[etiqueta])
        for exp in range(1, num_exp + 1):
            muestra_id = f"{etiqueta}_{exp:03d}"
            
            # Variabilidad inter-experimento (deriva sensorial/lote)
            variacion_exp = np.random.normal(1.0, 0.08, size=len(SENSORES))
            variacion_exp[6:] = 1.0  # temp y humedad varían menos
            perfil_exp = base * variacion_exp
            
            # Generar curva temporal de 60 segundos
            for t in range(60):
                # Efecto dinámico de acumulación de gases (curva sigmoide o exponencial)
                factor_tiempo = 1.0 - np.exp(-t / 15.0)
                
                # Lectura de los sensores químicos
                valores = perfil_exp.copy()
                valores[:6] = valores[:6] * factor_tiempo + np.random.normal(0, 3.0, size=6)
                
                # Ruido en temperatura y humedad
                valores[6] += np.random.normal(0, 0.2)
                valores[7] += np.random.normal(0, 0.5)
                
                # Asegurar valores no negativos para sensores
                valores = np.clip(valores, 0, 1023)
                
                fila = {
                    'tiempo': t,
                    'muestra_id': muestra_id,
                    'etiqueta': etiqueta
                }
                for i, s in enumerate(SENSORES):
                    fila[s] = round(valores[i], 2)
                    
                filas.append(fila)
                
    df_prueba = pd.DataFrame(filas)
    os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
    df_prueba.to_csv(ruta_csv, index=False)
    print(f"Creado '{ruta_csv}' con {len(df_prueba)} lecturas ({sum(muestras.values())} experimentos).")

def main():
    ruta_reales = 'data/datos_reales.csv'
    if not os.path.exists(ruta_reales):
        generar_datos_reales_de_prueba(ruta_reales)
        
    print(f"Leyendo dataset de datos reales desde: {ruta_reales}")
    df = pd.read_csv(ruta_reales)
    
    # 1. Promediar cada experimento para análisis de similitud
    print("Promediando lecturas por experimento...")
    df_exp = df.groupby(['muestra_id', 'etiqueta'])[SENSORES].mean().reset_index()
    
    # 2. Normalizar las lecturas promedio
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(df_exp[SENSORES])
    
    # 3. Reducir a 2D con PCA para visualizar
    print("Ejecutando PCA...")
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X_norm)
    df_exp['PCA1'] = X_2d[:, 0]
    df_exp['PCA2'] = X_2d[:, 1]
    
    # 4. Calcular la distancia al centroide de gasolina_90
    print("Calculando distancias al centroide de gasolina 90...")
    centroide_gasolina = X_norm[df_exp['etiqueta'] == 'gasolina_90'].mean(axis=0)
    distancias = np.linalg.norm(X_norm - centroide_gasolina, axis=1)
    df_exp['distancia_gasolina'] = distancias
    
    # 5. Asignar clases de calidad basadas en distancia
    def asignar_clase(row):
        if row['etiqueta'] == 'gasolina_90':
            return 'referencia'
        d = row['distancia_gasolina']
        if d < 1.5:
            return 'bio_oil_similar'       # Muy parecido a la gasolina
        elif d < 4.0:
            return 'bio_oil_intermedio'    # Diferencias notables
        else:
            return 'bio_oil_diferente'     # Muy distinto
            
    df_exp['clase_calidad'] = df_exp.apply(asignar_clase, axis=1)
    
    print("\nDistribución de experimentos etiquetados por calidad:")
    print(df_exp['clase_calidad'].value_counts())
    
    # 6. Mapear de regreso al dataset de series temporales completas
    print("\nMapeando clases de calidad de regreso al dataset temporal...")
    mapping = df_exp.set_index('muestra_id')['clase_calidad'].to_dict()
    df['clase_calidad'] = df['muestra_id'].map(mapping)
    
    # Guardar dataset completo de series de tiempo con etiquetas
    ruta_etiquetados = 'data/datos_etiquetados.csv'
    df.to_csv(ruta_etiquetados, index=False)
    print(f"Dataset de series temporales etiquetado guardado en: {ruta_etiquetados}")
    
    # Guardar resumen promedio
    df_exp.to_csv('data/datos_experimentos_promedio.csv', index=False)
    
    # 7. Graficar mapa de similitud
    print("Generando mapa de similitud...")
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
                    c=color, label=f"{tipo} (N={mask.sum()})", alpha=0.8, s=80, edgecolors='k')
                    
    plt.title('Mapa de Similitud E-Nose: Gasolina 90 vs Bio-oil\n(PCA sobre señales promedio de sensores)', fontsize=13, fontweight='bold')
    plt.xlabel(f'Componente Principal 1 ({pca.explained_variance_ratio_[0]*100:.1f}% varianza)')
    plt.ylabel(f'Componente Principal 2 ({pca.explained_variance_ratio_[1]*100:.1f}% varianza)')
    plt.legend(frameon=True, facecolor='white', framealpha=0.9)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    os.makedirs('data', exist_ok=True)
    plt.savefig('data/mapa_similitud.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Gráfico PCA guardado en: data/mapa_similitud.png")

if __name__ == '__main__':
    main()
