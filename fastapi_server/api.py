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
    
    # Initialize state variables for rolling window live monitoring
    app.state.sensor_buffer = []
    app.state.latest_result = {
        "prediction": "Esperando datos...",
        "confidence": 0.0,
        "probabilities": {},
        "diagnostics": [],
        "buffer_size": 0,
        "latest_values": {k: 0.0 for k in SENSORES}
    }
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
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

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schemas for request validation
class TimestepData(BaseModel):
    MQ2: float = Field(..., description="Sensor MQ2 reading")
    MQ4: float = Field(..., description="Sensor MQ4 reading")
    MQ135: float = Field(..., description="Sensor MQ135 reading")
    MQ3: float = Field(..., description="Sensor MQ3 reading")
    MQ7: float = Field(..., description="Sensor MQ7 reading")
    MQ9: float = Field(..., description="Sensor MQ9 reading")
    temp: float = Field(..., description="Reactor temperature in °C")
    humedad: float = Field(..., description="Relative humidity percentage")


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
            return HTMLResponse(content=f.read(), status_code=status.HTTP_200_OK)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Frontend index.html file not found."
    )


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
    diferencias = perfil_actual - assets.perfil_referencia
    
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
            ventana_normalizada = assets.scaler.transform(raw_window)
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
    """
    buffer = app.state.sensor_buffer
    buffer.append(request)
    
    if len(buffer) > TIMESTEPS:
        buffer.pop(0)
        
    if len(buffer) == TIMESTEPS:
        try:
            raw_window = np.array([
                [t.MQ2, t.MQ4, t.MQ135, t.MQ3, t.MQ7, t.MQ9, t.temp, t.humedad]
                for t in buffer
            ])
            prediction_res = process_prediction(raw_window)
            
            app.state.latest_result = {
                "prediction": prediction_res["prediction"],
                "confidence": prediction_res["confidence"],
                "probabilities": prediction_res["probabilities"],
                "diagnostics": prediction_res["diagnostics"],
                "buffer_size": len(buffer),
                "latest_values": request.model_dump()
            }
            logger.info("Auto-analysis complete. Quality: %s", prediction_res["prediction"])
        except Exception as err:
            logger.error("Error during auto-analysis: %s", err)
    else:
        # Just update latest values for visualization
        app.state.latest_result["buffer_size"] = len(buffer)
        app.state.latest_result["latest_values"] = request.model_dump()
        
    return {
        "status": "success",
        "buffer_size": len(buffer)
    }


@app.get("/latest_result", status_code=status.HTTP_200_OK)
def get_latest_result() -> Dict[str, Any]:
    """Returns the latest prediction result and current sensor values."""
    return app.state.latest_result


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
