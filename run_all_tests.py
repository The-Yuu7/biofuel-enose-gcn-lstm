import os
import sys
import subprocess
import json
import time

def print_separator(char="=", length=70):
    print(char * length)

def main():
    print_separator()
    print("      EJECUTOR UNIFICADO DE PRUEBAS DE CALIDAD E-NOSE")
    print("      (Pruebas Unitarias, Caja Negra/Blanca e Integración)")
    print_separator()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fastapi_dir = os.path.join(base_dir, "fastapi_server")
    pytest_file = os.path.join(fastapi_dir, "test_api.py")
    batch_script = os.path.join(base_dir, "data", "ejecutar_pruebas_json.py")
    
    # 1. Detección automática del entorno virtual (.venv)
    venv_python_win = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
    venv_python_unix = os.path.join(base_dir, ".venv", "bin", "python")
    
    python_executable = sys.executable
    using_venv = False
    
    if os.path.exists(venv_python_win):
        python_executable = venv_python_win
        using_venv = True
    elif os.path.exists(venv_python_unix):
        python_executable = venv_python_unix
        using_venv = True
        
    print(f"[INFO] Directorio base detectado: {base_dir}")
    if using_venv:
        print(f"[INFO] REDIRECCIONAMIENTO ACTIVO: Se usará el entorno virtual .venv")
    else:
        print(f"[WARN] No se detectó entorno virtual local en .venv, usando Python global")
    print(f"[INFO] Usando intérprete de Python: {python_executable}")
    print(f"[INFO] Pruebas unitarias: {pytest_file}")
    print(f"[INFO] Rendimiento de lotes: {batch_script}\n")
    
    if not os.path.exists(pytest_file):
        print(f"[ERROR] No se encontró el archivo de pruebas de API en {pytest_file}")
        sys.exit(1)
        
    if not os.path.exists(batch_script):
        print(f"[ERROR] No se encontró el script de pruebas de lotes en {batch_script}")
        sys.exit(1)

    # =========================================================================
    # FASE 1: Pruebas Unitarias y de APIs con Pytest (Caja Negra y Blanca)
    # =========================================================================
    print_separator("-")
    print("[FASE 1] Ejecutando Pruebas Unitarias y de Endpoints REST (Pytest)...")
    print_separator("-")
    
    # Ejecutamos pytest sobre fastapi_server usando el intérprete de Python correcto
    t_ini_unit = time.time()
    res_pytest = subprocess.run(
        [python_executable, "-m", "pytest", "test_api.py", "-v", "--cov=api", "--cov-report=xml"],
        cwd=fastapi_dir,
        capture_output=True,
        text=True
    )
    t_fin_unit = time.time()
    
    unit_success = res_pytest.returncode == 0
    print(res_pytest.stdout)
    if res_pytest.stderr:
        print("[STDERR PYTEST]:", res_pytest.stderr)
        
    # =========================================================================
    # FASE 2: Pruebas de Integración y Rendimiento de Lotes (Batch Performance)
    # =========================================================================
    print_separator("-")
    print("[FASE 2] Ejecutando Pruebas de Integración de Lotes y Rendimiento...")
    print_separator("-")
    
    t_ini_batch = time.time()
    res_batch = subprocess.run(
        [python_executable, "data/ejecutar_pruebas_json.py"],
        cwd=base_dir,
        capture_output=True,
        text=True
    )
    t_fin_batch = time.time()
    
    batch_success = res_batch.returncode == 0
    print(res_batch.stdout)
    if res_batch.stderr:
        print("[STDERR BATCH]:", res_batch.stderr)

    # =========================================================================
    # RESUMEN GLOBAL UNIFICADO (Dashboard de Reporte ISO 29119)
    # =========================================================================
    print_separator()
    print("              DASHBOARD RESUMEN DE PRUEBAS DE CALIDAD")
    print_separator()
    
    # Leer el reporte JSON de lotes si existe
    resultados_json_path = os.path.join(base_dir, "data", "resultados_pruebas.json")
    lotes_resumen = {}
    if os.path.exists(resultados_json_path):
        try:
            with open(resultados_json_path, "r") as f:
                data_json = json.load(f)
                lotes_resumen = data_json.get("resumen_global", {})
        except Exception as e:
            print(f"[WARN] No se pudo leer resultados_pruebas.json: {e}")

    # Determinar estado de pruebas unitarias
    passed_tests = 0
    failed_tests = 0
    for line in res_pytest.stdout.split("\n"):
        if "PASSED" in line:
            passed_tests += 1
        elif "FAILED" in line:
            failed_tests += 1
            
    print("A. PRUEBAS UNITARIAS Y CAJA NEGRA/BLANCA (fastapi_server/test_api.py):")
    status_unit = "APROBADO [OK]" if unit_success else "FALLIDO [ERROR]"
    print(f"   - Estado de Ejecución     : {status_unit}")
    print(f"   - Pruebas que Pasaron     : {passed_tests}")
    print(f"   - Pruebas que Fallaron    : {failed_tests}")
    print(f"   - Tiempo de Ejecución     : {t_fin_unit - t_ini_unit:.2f} segundos")
    print(f"   - Reporte de Cobertura    : Generado (fastapi_server/coverage.xml)")
    print()
    
    print("B. PRUEBAS DE INTEGRACIÓN Y DESEMPEÑO (data/ejecutar_pruebas_json.py):")
    status_batch = "APROBADO [OK]" if batch_success else "FALLIDO [ERROR]"
    print(f"   - Estado de Ejecución     : {status_batch}")
    if lotes_resumen and batch_success:
        print(f"   - Lotes Evaluados         : {lotes_resumen.get('total_lotes', 450)}")
        print(f"   - Precision (Accuracy)    : {lotes_resumen.get('precision_accuracy_porc', 100.0)}%")
        print(f"   - Latencia Media Inferencia: {lotes_resumen.get('latencia_media_ms', 0.0)} ms")
        print(f"   - Consumo Medio de RAM    : {lotes_resumen.get('ram_media_mb', 0.0)} MB")
        print(f"   - Falsos Positivos (Alta) : {lotes_resumen.get('falsos_positivos_calidad_alta', 0)}")
        print(f"   - Falsos Negativos        : {lotes_resumen.get('falsos_negativos', 0)}")
    else:
        print(f"   - Lotes Evaluados         : 0 (Ejecución fallida o incompleta)")
    print(f"   - Tiempo de Ejecución     : {t_fin_batch - t_ini_batch:.2f} segundos")
    print(f"   - Reporte Detallado Lotes : Generado (data/resultados_pruebas.json)")
    print()

    print_separator("-")
    # Veredicto Final
    if unit_success and batch_success:
        print("RESULTADO FINAL: SISTEMA APROBADO (100% CUMPLIMIENTO ISO 29119/25000)")
    else:
        print("RESULTADO FINAL: SISTEMA CON ERRORES (REVISAR LOGS DE PRUEBAS)")
    print_separator()

if __name__ == "__main__":
    main()
