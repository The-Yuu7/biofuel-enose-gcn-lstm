import os
import pickle
import numpy as np
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from api import app, assets, SENSORES

client = TestClient(app)

def test_health_endpoint():
    """Verify that the health check endpoint returns status 200 and indicates model readiness."""
    with client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["scaler_loaded"] is True
        assert data["label_encoder_loaded"] is True

def test_root_endpoint():
    """Verify that the root endpoint serves the HTML dashboard successfully."""
    with client:
        response = client.get("/")
        assert response.status_code == 200
        assert "E-Nose" in response.text

def test_predict_alta_optimal():
    """Verify prediction with optimal inputs matching the reference profile (ALTA)."""
    with client:
        # Load the reference profile to simulate optimal conditions
        ref_path = os.path.join(os.path.dirname(__file__), "model", "perfil_referencia.pkl")
        if os.path.exists(ref_path):
            with open(ref_path, 'rb') as f:
                perfil_referencia = pickle.load(f)
            
            # Reconstruct optimal sequence
            if perfil_referencia.ndim == 2 and perfil_referencia.shape[0] == 30:
                ref_window_norm = perfil_referencia
            else:
                ref_vec = np.mean(perfil_referencia, axis=0) if perfil_referencia.ndim == 2 else perfil_referencia
                ref_window_norm = np.repeat(ref_vec[np.newaxis, :], 30, axis=0)
            ref_window = assets.scaler.inverse_transform(ref_window_norm)
        else:
            ref_window = np.zeros((30, 8))

        window_data = []
        for row in ref_window:
            window_data.append({
                "MQ2": float(row[0]),
                "MQ4": float(row[1]),
                "MQ135": float(row[2]),
                "MQ3": float(row[3]),
                "MQ7": float(row[4]),
                "MQ9": float(row[5]),
                "temp": float(row[6]),
                "humedad": float(row[7])
            })
            
        payload = {"window": window_data}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] in ["ALTA", "MEDIA"]
        assert data["confidence"] > 50.0
        assert isinstance(data["diagnostics"], list)

def test_predict_deviated():
    """Verify that deviated inputs trigger corresponding warnings and recommendations."""
    with client:
        # Reconstruct base profile and add positive deviations to MQ4 and MQ7
        if assets.perfil_referencia is not None:
            if assets.perfil_referencia.ndim == 2 and assets.perfil_referencia.shape[0] == 30:
                ref_window_norm = assets.perfil_referencia.copy()
            else:
                ref_vec = np.mean(assets.perfil_referencia, axis=0) if assets.perfil_referencia.ndim == 2 else assets.perfil_referencia
                ref_window_norm = np.repeat(ref_vec[np.newaxis, :], 30, axis=0)
            ref_window_norm[:, 1] += 2.5  # MQ4 anomaly
            ref_window_norm[:, 4] += 1.8  # MQ7 anomaly
            ref_window = assets.scaler.inverse_transform(ref_window_norm)
        else:
            ref_window = np.zeros((30, 8))

        window_data = []
        for row in ref_window:
            window_data.append({
                "MQ2": float(row[0]),
                "MQ4": float(row[1]),
                "MQ135": float(row[2]),
                "MQ3": float(row[3]),
                "MQ7": float(row[4]),
                "MQ9": float(row[5]),
                "temp": float(row[6]),
                "humedad": float(row[7])
            })
            
        payload = {"window": window_data}
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == "MEDIA"
        
        # Verify that diagnostic recommendations for MQ4 and MQ7 are triggered
        sensors_triggered = [d["sensor"] for d in data["diagnostics"]]
        assert "MQ4" in sensors_triggered
        assert "MQ7" in sensors_triggered
        
        # Verify specific recommendations details
        for d in data["diagnostics"]:
            if d["sensor"] == "MQ4":
                assert "reactor" in d["recommendation"].lower()
            if d["sensor"] == "MQ7":
                assert "temperatura" in d["recommendation"].lower()

def test_predict_invalid_size():
    """Verify that sending a window of incorrect length returns a 400 Bad Request error."""
    with client:
        # Window with only 10 steps instead of 30
        window_data = [
            {"MQ2": 0.0, "MQ4": 0.0, "MQ135": 0.0, "MQ3": 0.0, "MQ7": 0.0, "MQ9": 0.0, "temp": 0.0, "humedad": 0.0}
            for _ in range(10)
        ]
        payload = {"window": window_data}
        response = client.post("/predict", json=payload)
        assert response.status_code == 400
        assert "exactly 30 timesteps" in response.json()["detail"]

def test_sensor_data_streaming():
    """Verify that sending individual sensor data updates the rolling buffer and latest result."""
    with client:
        # 1. Verify initial status
        response = client.get("/latest_result")
        assert response.status_code == 200
        data = response.json()
        assert data["prediction"] == "Esperando datos..."
        assert data["buffer_size"] == 0

        # 2. Send 1 timestep
        payload = {
            "MQ2": 23000.0, "MQ4": 17000.0, "MQ135": 12000.0, "MQ3": 8000.0,
            "MQ7": 7000.0, "MQ9": 15000.0, "temp": 22.5, "humedad": 59.0
        }
        response = client.post("/sensor_data", json=payload)
        assert response.status_code == 200
        assert response.json()["buffer_size"] == 1

        # 3. Verify latest result updated
        response = client.get("/latest_result")
        assert response.json()["buffer_size"] == 1
        assert response.json()["latest_values"]["MQ2"] == 23000.0
