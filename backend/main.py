from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import os
import sys

# Add parent directory to path to allow imports if needed, 
# though for model loading we just need the file path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="BLDC AI Simulator")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables ---
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_core", "bldc_model.pkl")
# Path to frontend build artifacts
FRONTEND_DIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

model = None

# --- Startup Event ---
@app.on_event("startup")
def load_model():
    global model
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"Model loaded from {MODEL_PATH}")
    else:
        print(f"WARNING: Model file not found at {MODEL_PATH}")

# --- Pydantic Models ---
class MotorInput(BaseModel):
    stator_od: float = Field(default=80.0, description="Stator Outer Diameter (mm)")
    stack_length: float = Field(default=30.0, description="Stack Length (mm)")
    airgap: float = Field(default=0.7, description="Airgap length (mm)")
    turns_per_coil: int = Field(default=25, description="Turns per coil")
    magnet_rem: float = Field(default=1.25, description="Magnet Remanence (Tesla)")
    slot_pole_combo: str = Field(default="12N14P", description="Slot/Pole Combination (e.g. 12N14P)")

class MotorPrediction(BaseModel):
    kv_rating: float
    rated_torque: float
    weight_kg: float
    status: str = "success"

# --- API Endpoints (Must be defined BEFORE static files) ---

@app.get("/api/health")
def read_root():
    return {"status": "online", "model_loaded": model is not None}

@app.post("/predict", response_model=MotorPrediction)
def predict_performance(input_data: MotorInput):
    if model is None:
        raise HTTPException(status_code=503, detail="AI Model not loaded")
    
    # Prepare DataFrame
    # Column names must match training features exactly:
    # ['stator_od', 'stack_length', 'airgap', 'turns_per_coil', 'magnet_rem', 'slot_pole_combo']
    input_df = pd.DataFrame([input_data.dict()])
    
    try:
        # Predict
        prediction = model.predict(input_df)
        
        # Unpack result (Kv, Torque, Weight)
        kv = float(prediction[0][0])
        torque = float(prediction[0][1])
        weight = float(prediction[0][2])
        
        return MotorPrediction(
            kv_rating=round(kv, 1),
            rated_torque=round(torque, 3),
            weight_kg=round(weight, 3)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# --- Static Files & Frontend Serving ---
# Only mount if the build directory exists (Production Mode)
if os.path.exists(FRONTEND_DIST_PATH):
    print(f"Serving frontend from {FRONTEND_DIST_PATH}")
    # Mount assets (js, css, etc.)
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST_PATH, "assets")), name="assets")
    
    # Catch-all route for SPA (Single Page Application)
    # This serves index.html for any other route (like / or /about)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Check if file exists in dist root (like favicon.ico)
        file_path = os.path.join(FRONTEND_DIST_PATH, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
             return FileResponse(file_path)
        
        # Otherwise serve index.html
        return FileResponse(os.path.join(FRONTEND_DIST_PATH, "index.html"))
else:
    print(f"Frontend build not found at {FRONTEND_DIST_PATH}. Running in API-only mode.")
    # Optional: Serve a simple placeholder or the standalone html if dist is missing
    @app.get("/")
    def serve_standalone():
        standalone_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend_standalone.html")
        if os.path.exists(standalone_path):
            return FileResponse(standalone_path)
        return {"message": "Frontend not built and standalone file not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
