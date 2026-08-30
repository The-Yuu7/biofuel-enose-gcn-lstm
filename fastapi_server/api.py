import logging
import os
import pickle
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Setup logging configuration (SonarQube standard)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("E-Nose-API")

# Define global constants
SENSORES: List[str] = ['MQ2', 'MQ4', 'MQ135', 'MQ3', 'MQ7', 'MQ9', 'temp', 'humedad']
TIMESTEPS: int = 30

DIAGNOSTICOS: Dict[str, Dict[str, tuple]] = {
    'MQ7': {
        'ALTO': (
            'CO elevado (Combustión Incompleta)',
            'Causa: Temperatura de pirólisis del reactor demasiado baja. Acción correctiva: Incrementar la potencia del calentador en +15% para estabilizar el reactor.'
        ),
        'BAJO': (
            'CO bajo (Pobreza de gas)',
            'Causa: Falta de generación de gas por detención de reacción. Acción correctiva: Verificar que el alimentador de plásticos no esté obstruido.'
        )
    },
    'MQ135': {
        'ALTO': (
            'VOCs / Aromáticos elevados',
            'Causa: Craqueo térmico incompleto por flujo rápido. Acción correctiva: Reducir velocidad de inyección de gases para aumentar tiempo de residencia.'
        ),
        'BAJO': (
            'VOCs bajos (Bajo rendimiento)',
            'Causa: Reacción de pirólisis lenta. Acción correctiva: Aumentar la tasa de calentamiento térmico primario.'
        )
    },
    'MQ4': {
        'ALTO': (
            'Metano (CH4) elevado',
            'Causa: El reactor está por debajo del rango de craqueo óptimo para gasolina. Acción correctiva: Incrementar calefacción hasta estabilizar a 430°C.'
        ),
        'BAJO': (
            'Metano (CH4) bajo',
            'Causa: Temperatura excesiva o falta de craqueo primario. Acción correctiva: Monitorear termocupla central y ajustar límites térmicos.'
        )
    },
    'MQ2': {
        'ALTO': (
            'Gases livianos altos (GLP/Propano)',
            'Causa: Licuefacción ineficiente en el condensador. Acción correctiva: Aumentar el flujo de agua de refrigeración en el condensador secundario.'
        ),
        'BAJO': (
            'Gases livianos bajos',
            'Causa: Generación de vapores deficiente en el reactor. Acción correctiva: Aumentar la potencia del reactor principal.'
        )
    },
    'MQ3': {
        'ALTO': (
            'Contaminación por Oxigenados (Alcoholes)',
            'Causa: Contaminación de materia prima con plásticos oxigenados (PET/PVC). Acción correctiva: Detener alimentación y verificar clasificación previa de plásticos.'
        ),
        'BAJO': (
            'Trazas de oxigenados normales',
            'Causa: Comportamiento normal. Acción correctiva: No se requieren acciones correctivas.'
        )
    },
    'MQ9': {
        'ALTO': (
            'Combustibles medios elevados',
            'Causa: Desequilibrio de condensación o sobrecalentamiento local. Acción correctiva: Estabilizar la temperatura de la camisa del reactor.'
        ),
        'BAJO': (
            'Combustibles medios bajos',
            'Causa: Tasa de destilación muy lenta. Acción correctiva: Incrementar la rampa de temperatura del destilador.'
        )
    },
    'temp': {
        'ALTO': (
            'Temperatura de cámara elevada',
            'Causa: Calor radiante excesivo del reactor o falla del cooler. Acción correctiva: Activar extractor de la cámara y revisar aislamiento térmico.'
        ),
        'BAJO': (
            'Temperatura de cámara baja',
            'Causa: Temperatura ambiental fría o baja actividad de reacción. Acción correctiva: Estabilizar la temperatura de la cámara precalentándola.'
        )
    },
    'humedad': {
        'ALTO': (
            'Humedad de cámara elevada',
            'Causa: Fuga de vapor o trampa de agua saturada. Acción correctiva: Vaciar y purgar la trampa de agua/condensado antes del sensado.'
        ),
        'BAJO': (
            'Humedad de cámara baja',
            'Causa: Ambiente de sensado excesivamente seco. Acción correctiva: No se requieren acciones correctivas.'
        )
    }
}

# Dynamic import of TFLite
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import ai_edge_litert.interpreter as tflite
    except ImportError:
        try:
            import tensorflow.lite as tflite
        except ImportError as err:
            logger.critical("Neither tflite_runtime, ai_edge_litert, nor tensorflow.lite is installed.")
            raise ImportError("Required TensorFlow Lite libraries are missing.") from err


class ModelAssets:
    """Container for lazily loaded model assets at application startup."""
    
    def __init__(self) -> None:
        self.interpreter: Optional[Any] = None
        self.input_details: Optional[List[Dict[str, Any]]] = None
        self.output_details: Optional[List[Dict[str, Any]]] = None
        self.scaler: Optional[Any] = None
        self.label_encoder: Optional[Any] = None
        self.perfil_referencia: Optional[np.ndarray] = None


# Instantiate global asset container
assets = ModelAssets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles the startup and shutdown lifecycles of FastAPI assets."""
    logger.info("Initializing application startup sequence.")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize state variables for rolling window live monitoring and MANUAL pyrolysis dataset logging
    app.state.sensor_buffer = []
    app.state.recorded_samples_count = 0
    app.state.is_recording = False  # Modo manual: por defecto solo monitorea sin guardar
    app.state.csv_path = os.path.join(base_dir, "data_capturada_pirolisis.csv")
    app.state.latest_result = {
        "prediction": "Esperando datos...",
        "confidence": 0.0,
        "probabilities": {},
        "diagnostics": [],
        "buffer_size": 0,
        "ambient_status": "AIRE AMBIENTE (SENSORES LIMPIOS)",
        "is_ambient": True,
        "is_recording": False,
        "recorded_samples": 0,
        "latest_values": {k: 0.0 for k in SENSORES}
    }
    
    model_path = os.path.join(base_dir, "model", "enose_modelo.tflite")
    scaler_path = os.path.join(base_dir, "model", "scaler.pkl")
    encoder_path = os.path.join(base_dir, "model", "label_encoder.pkl")
    ref_path = os.path.join(base_dir, "model", "perfil_referencia.pkl")

    # Validate existence of required files
    for path in [model_path, scaler_path, encoder_path]:
        if not os.path.exists(path):
            error_msg = f"Required asset missing during startup check: {path}"
            logger.critical(error_msg)
            raise FileNotFoundError(error_msg)

    try:
        # Load scaler
        with open(scaler_path, 'rb') as file_in:
            assets.scaler = pickle.load(file_in)
        logger.info("Scaler loaded successfully from: %s", scaler_path)

        # Load label encoder
        with open(encoder_path, 'rb') as file_in:
            assets.label_encoder = pickle.load(file_in)
        logger.info("Label encoder loaded successfully from: %s", encoder_path)

        # Load reference profile (if available)
        if os.path.exists(ref_path):
            with open(ref_path, 'rb') as file_in:
                assets.perfil_referencia = pickle.load(file_in)
            logger.info("Reference profile loaded successfully from: %s", ref_path)
        else:
            logger.warning("Optional reference profile not found at: %s", ref_path)

        # Initialize TFLite Interpreter
        assets.interpreter = tflite.Interpreter(model_path=model_path)
        assets.interpreter.allocate_tensors()
        assets.input_details = assets.interpreter.get_input_details()
        assets.output_details = assets.interpreter.get_output_details()
        logger.info("TensorFlow Lite interpreter initialized successfully.")

    except (pickle.UnpicklingError, ValueError) as err:
        logger.critical("Data corruption or error loading pickle assets: %s", err)
        raise RuntimeError("Asset loading failed due to binary serialization errors.") from err
    except Exception as err:
        logger.critical("Unexpected error during startup initialization: %s", err)
        raise err

    yield
    
    # Cleanup lifecycle
    logger.info("Application shutting down. Releasing assets.")
    assets.interpreter = None
    assets.scaler = None
    assets.label_encoder = None
    assets.perfil_referencia = None


# Initialize FastAPI app with lifespan manager
app = FastAPI(
    title="E-Nose Biofuel Quality Control API",
    description="Optimized API for running real-time quality inference and pyrolysis diagnostics.",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.staticfiles import StaticFiles

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local static assets for offline SCADA UI rendering (without internet CDN)
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Pydantic schemas for request validation
class TimestepData(BaseModel):
    MQ2: float = Field(..., description="Sensor MQ2 reading")
    MQ4: float = Field(..., description="Sensor MQ4 reading")
    MQ135: float = Field(..., description="Sensor MQ135 reading")
    MQ3: float = Field(..., description="Sensor MQ3 reading")
    MQ7: float = Field(..., description="Sensor MQ7 reading")
    MQ9: float = Field(..., description="Sensor MQ9 reading")
    temp: float = Field(..., description="Chamber ambient temperature in °C")
    humedad: float = Field(..., description="Relative humidity percentage")
    temp_reactor: Optional[float] = Field(default=430.0, description="Internal pyrolysis reactor temperature in °C")


class PredictionRequest(BaseModel):
    window: List[TimestepData] = Field(
        ...,
        description="Time-series window consisting of exactly 30 sensor reading steps."
    )


class RawPredictionRequest(BaseModel):
    data: List[List[float]] = Field(
        ...,
        description="A 30x8 matrix of sensor values in order: MQ2, MQ4, MQ135, MQ3, MQ7, MQ9, temp, humedad."
    )


@app.get("/", response_class=HTMLResponse)
def read_root() -> HTMLResponse:
    """Serves the interactive quality control and pyrolysis diagnostics dashboard."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>E-Nose Control Center API is running.</h1>")


@app.get("/favicon.ico")
def get_favicon():
    """Silences browser favicon 404 requests."""
    from fastapi.responses import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, Any]:
    """Checks the operational status of the API and loaded models.
    
    Returns:
        Dict[str, Any]: Object containing health parameters and loaded classes.
    """
    is_ready = all([
        assets.interpreter is not None,
        assets.scaler is not None,
        assets.label_encoder is not None
    ])
    
    target_classes = list(assets.label_encoder.classes_) if assets.label_encoder else []
    
    return {
        "status": "healthy" if is_ready else "unhealthy",
        "model_loaded": assets.interpreter is not None,
        "scaler_loaded": assets.scaler is not None,
        "label_encoder_loaded": assets.label_encoder is not None,
        "reference_profile_loaded": assets.perfil_referencia is not None,
        "target_classes": target_classes
    }


def run_diagnostic(ventana_normalizada: np.ndarray) -> List[Dict[str, Any]]:
    """Compares actual normalized readings against the target ALTA reference profile.
    
    Args:
        ventana_normalizada (np.ndarray): Normalized sensor sequence matrix of shape (30, 8).
        
    Returns:
        List[Dict[str, Any]]: List of diagnostic warnings with deviations and recommended adjustments.
    """
    diagnostics: List[Dict[str, Any]] = []
    if assets.perfil_referencia is None:
        logger.debug("Diagnostics skipped. Reference profile not loaded.")
        return diagnostics
        
    perfil_actual = np.mean(ventana_normalizada, axis=0)
    ref_vec = np.mean(assets.perfil_referencia, axis=0) if assets.perfil_referencia.ndim == 2 else assets.perfil_referencia
    diferencias = perfil_actual - ref_vec
    
    for i, sensor in enumerate(SENSORES):
        diff = diferencias[i]
        # Any deviation > 1.0 standard deviations is considered a significant anomaly
        if abs(diff) > 1.0:
            status_dev = "ALTO" if diff > 0 else "BAJO"
            if sensor in DIAGNOSTICOS:
                rules = DIAGNOSTICOS[sensor]
                if status_dev in rules:
                    alert_title, recommendation = rules[status_dev]
                else:
                    alert_title, recommendation = f"Desviación {status_dev} en {sensor}", f"El sensor {sensor} está anormalmente {status_dev.lower()}."
                diagnostics.append({
                    "sensor": sensor,
                    "status": status_dev,
                    "deviation": round(float(diff), 2),
                    "alert": alert_title,
                    "recommendation": recommendation
                })
            else:
                diagnostics.append({
                    "sensor": sensor,
                    "status": status_dev,
                    "deviation": round(float(diff), 2),
                    "alert": f"Desviación en {sensor}",
                    "recommendation": f"El sensor {sensor} se encuentra anormalmente {status_dev.lower()}."
                })
    return diagnostics


def process_prediction(raw_window: np.ndarray) -> Dict[str, Any]:
    """Applies scaler, runs inference using TFLite, and computes diagnostics.
    
    Args:
        raw_window (np.ndarray): NumPy matrix containing 30 timesteps of 8 sensor features.
        
    Returns:
        Dict[str, Any]: Prediction class, confidence, probabilities, and diagnostics alerts.
    """
    if not assets.scaler or not assets.interpreter or not assets.label_encoder:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model assets are not fully loaded or initialized."
        )

    # 1. Normalize data
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            raw_window_2d = raw_window.reshape(-1, len(SENSORES))
            ventana_normalizada = assets.scaler.transform(raw_window_2d).reshape(TIMESTEPS, len(SENSORES))
    except Exception as err:
        logger.error("Data scaling failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data normalization error: {err}"
        ) from err
        
    # 2. Reshape and format for TFLite interpreter input tensor
    entrada = ventana_normalizada[np.newaxis, :, :].astype(np.float32)
    
    # 3. Invoke interpreter model prediction
    try:
        assets.interpreter.set_tensor(assets.input_details[0]['index'], entrada)
        assets.interpreter.invoke()
        probabilidades = assets.interpreter.get_tensor(assets.output_details[0]['index'])[0]
    except Exception as err:
        logger.error("Inference execution failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {err}"
        ) from err
        
    # 4. Map output prediction indexes to human-readable classes
    clase_idx = np.argmax(probabilidades)
    clase_predictiva = assets.label_encoder.classes_[clase_idx]
    confianza = round(float(probabilidades[clase_idx]) * 100, 2)
    
    probabilities_dict = {
        assets.label_encoder.classes_[i]: round(float(probabilidades[i]), 4)
        for i in range(len(assets.label_encoder.classes_))
    }
    
    # 5. Execute diagnostics warnings comparison
    diagnostics = run_diagnostic(ventana_normalizada)
    
    # Inject validation success indicator if quality is ALTA and no errors were found
    if not diagnostics and clase_predictiva == "ALTA":
        diagnostics.append({
            "sensor": "General",
            "status": "OK",
            "deviation": 0.0,
            "alert": "Excelente calidad",
            "recommendation": "El perfil sensorial es óptimo para la producción de biocombustible de alta calidad. Continuar con los parámetros de operación actuales."
        })
        
    return {
        "prediction": clase_predictiva,
        "confidence": confianza,
        "probabilities": probabilities_dict,
        "diagnostics": diagnostics
    }


@app.post("/predict", status_code=status.HTTP_200_OK)
def predict_quality(request: PredictionRequest) -> Dict[str, Any]:
    """Performs inference and diagnostics on Pydantic structured model inputs.
    
    Args:
        request (PredictionRequest): Validated model input schema containing the 30x8 window.
        
    Returns:
        Dict[str, Any]: Prediction outcomes and diagnostic parameters.
    """
    if len(request.window) != TIMESTEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The input window must contain exactly {TIMESTEPS} timesteps. Received {len(request.window)}."
        )
        
    try:
        raw_window = np.array([
            [t.MQ2, t.MQ4, t.MQ135, t.MQ3, t.MQ7, t.MQ9, t.temp, t.humedad]
            for t in request.window
        ])
    except ValueError as err:
        logger.error("Incorrect types or values inside time-series array: %s", err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pydantic validation passed but numerical conversions failed."
        ) from err
        
    return process_prediction(raw_window)


@app.post("/predict_raw", status_code=status.HTTP_200_OK)
def predict_quality_raw(request: RawPredictionRequest) -> Dict[str, Any]:
    """Performs inference and diagnostics directly on 2D float arrays.
    
    Args:
        request (RawPredictionRequest): Matrix schema containing the 30x8 raw data.
        
    Returns:
        Dict[str, Any]: Prediction outcomes and diagnostic parameters.
    """
    raw_window = np.array(request.data)
    if raw_window.shape != (TIMESTEPS, len(SENSORES)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input matrix must have shape ({TIMESTEPS}, {len(SENSORES)}). Got {raw_window.shape}."
        )
    return process_prediction(raw_window)


@app.post("/sensor_data", status_code=status.HTTP_200_OK)
def receive_sensor_data(request: TimestepData) -> Dict[str, Any]:
    """Receives a single timestep of sensor readings and appends it to the rolling buffer.
    Runs prediction and diagnostics automatically once the buffer is full (30 timesteps).
    Saves sensor data to CSV ONLY IF manual recording is active.
    """
    buffer = app.state.sensor_buffer
    buffer.append(request)
    
    if len(buffer) > TIMESTEPS:
        buffer.pop(0)
        
    # Detect ambient air baseline level (if main hydrocarbon sensors are < 10000 ADC)
    is_ambient = (request.MQ2 < 10000 and request.MQ4 < 10000 and request.MQ135 < 10000)
    ambient_status = "AIRE AMBIENTE (SENSORES LIMPIOS)" if is_ambient else "REACCIÓN ACTIVA / MONITORIZANDO VAPORES"
        
    if len(buffer) == TIMESTEPS:
        try:
            raw_window = np.array([
                [t.MQ2, t.MQ4, t.MQ135, t.MQ3, t.MQ7, t.MQ9, t.temp, t.humedad]
                for t in buffer
            ])
            prediction_res = process_prediction(raw_window)
            
            # Record to CSV ONLY when user activates manual recording mode
            if getattr(app.state, 'is_recording', False):
                try:
                    import csv
                    file_exists = os.path.exists(app.state.csv_path)
                    with open(app.state.csv_path, 'a', newline='') as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(SENSORES)
                        for row in raw_window:
                            writer.writerow(row)
                    app.state.recorded_samples_count += 1
                    logger.info("¡Muestra N° %d registrada en CSV (Modo Manual Active)!", app.state.recorded_samples_count)
                except Exception as csv_err:
                    logger.error("Error guardando muestra en CSV: %s", csv_err)
            
            app.state.latest_result = {
                "prediction": prediction_res["prediction"],
                "confidence": prediction_res["confidence"],
                "probabilities": prediction_res["probabilities"],
                "diagnostics": prediction_res["diagnostics"],
                "buffer_size": len(buffer),
                "ambient_status": ambient_status,
                "is_ambient": is_ambient,
                "is_recording": getattr(app.state, 'is_recording', False),
                "recorded_samples": app.state.recorded_samples_count,
                "latest_values": request.model_dump()
            }
            logger.info("Auto-analysis complete. Quality: %s | Ambient: %s | Recording Active: %s (%d samples)", 
                        prediction_res["prediction"], ambient_status, getattr(app.state, 'is_recording', False), app.state.recorded_samples_count)
        except Exception as err:
            logger.error("Error during auto-analysis: %s", err)
    else:
        # Just update latest values for visualization
        app.state.latest_result["buffer_size"] = len(buffer)
        app.state.latest_result["ambient_status"] = ambient_status
        app.state.latest_result["is_ambient"] = is_ambient
        app.state.latest_result["is_recording"] = getattr(app.state, 'is_recording', False)
        app.state.latest_result["recorded_samples"] = app.state.recorded_samples_count
        app.state.latest_result["latest_values"] = request.model_dump()
        
    return {
        "status": "success",
        "buffer_size": len(buffer),
        "ambient_status": ambient_status,
        "is_recording": getattr(app.state, 'is_recording', False),
        "recorded_samples": app.state.recorded_samples_count
    }


@app.get("/latest_result", status_code=status.HTTP_200_OK)
def get_latest_result() -> Dict[str, Any]:
    """Returns the latest prediction result, current sensor values, ambient status, and CSV recording progress."""
    return app.state.latest_result


@app.get("/recording_status", status_code=status.HTTP_200_OK)
def get_recording_status() -> Dict[str, Any]:
    """Returns current CSV manual recording progress and status."""
    return {
        "is_recording": getattr(app.state, 'is_recording', False),
        "recorded_samples": app.state.recorded_samples_count,
        "csv_path": app.state.csv_path
    }


@app.post("/recording/start", status_code=status.HTTP_200_OK)
def start_recording() -> Dict[str, Any]:
    """Starts manual CSV data logging."""
    app.state.is_recording = True
    logger.info("Grabación manual de CSV INICIADA por el usuario.")
    return {
        "status": "success",
        "is_recording": True,
        "recorded_samples": app.state.recorded_samples_count
    }


@app.post("/recording/stop", status_code=status.HTTP_200_OK)
def stop_recording() -> Dict[str, Any]:
    """Stops manual CSV data logging."""
    app.state.is_recording = False
    logger.info("Grabación manual de CSV DETENIDA por el usuario.")
    return {
        "status": "success",
        "is_recording": False,
        "recorded_samples": app.state.recorded_samples_count
    }


@app.post("/recording/clear", status_code=status.HTTP_200_OK)
def clear_recording() -> Dict[str, Any]:
    """Clears the recorded CSV dataset file and resets the counter."""
    if os.path.exists(app.state.csv_path):
        os.remove(app.state.csv_path)
    app.state.recorded_samples_count = 0
    app.state.is_recording = False
    logger.info("Archivo CSV borrado/limpiado por el usuario.")
    return {
        "status": "success",
        "is_recording": False,
        "recorded_samples": 0
    }


@app.get("/recording/download")
def download_recording():
    """Downloads the recorded CSV dataset file."""
    from fastapi.responses import FileResponse
    if os.path.exists(app.state.csv_path):
        return FileResponse(
            app.state.csv_path, 
            media_type="text/csv", 
            filename="registros_nariz_electronica_pirolisis.csv"
        )
    raise HTTPException(status_code=404, detail="No se ha grabado ningún archivo CSV aún.")


@app.get("/reference_profile", status_code=status.HTTP_200_OK)
def get_reference_profile() -> Dict[str, Any]:
    """Returns the exact pattern baseline (means, std devs and physical voltages) of the real commercial gasoline calibration dataset."""
    if not assets.scaler:
        return {"status": "error", "message": "Scaler not loaded"}
    
    means = assets.scaler.mean_
    stds = assets.scaler.scale_
    
    pattern = {}
    for i, s in enumerate(SENSORES):
        pattern[s] = {
            "mean_adc": round(float(means[i]), 2),
            "std_adc": round(float(stds[i]), 2),
            "voltage": round(float(means[i] * (4.096 / 32768.0)), 3) if i < 6 else round(float(means[i]), 1),
            "unit": "ADC" if i < 6 else ("°C" if s == "temp" else "%")
        }
        
    return {
        "status": "success",
        "calibration_samples": 50,
        "grifos_count": {"Grifo_1": 17, "Grifo_2": 17, "Grifo_3": 16},
        "quality_thresholds": {
            "ALTA": {"min_confidence": 90.0, "max_zscore": 1.5, "badge": "Clase A - Dentro de Norma ASTM D4814"},
            "MEDIA": {"min_confidence": 70.0, "max_zscore": 3.0, "badge": "Clase B - Desviación Tolerable / Advertencia"},
            "BAJA": {"min_confidence": 0.0, "max_zscore": 99.0, "badge": "Clase C - Fuera de Especificación / Adulterada"}
        },
        "pattern": pattern
    }


@app.post("/clear_buffer", status_code=status.HTTP_200_OK)
def clear_buffer() -> Dict[str, Any]:
    """Clears the sensor buffer and resets the latest result prediction status."""
    app.state.sensor_buffer.clear()
    app.state.latest_result = {
        "prediction": "Esperando datos...",
        "confidence": 0.0,
        "probabilities": {},
        "diagnostics": [],
        "buffer_size": 0,
        "latest_values": {k: 0.0 for k in SENSORES}
    }
    logger.info("Sensor buffer purged by client request.")
    return {
        "status": "success",
        "message": "Sensor buffer cleared and reset successful."
    }


if __name__ == "__main__":
    import uvicorn
    # Start ASGI server on execution
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
