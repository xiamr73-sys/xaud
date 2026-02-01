import joblib
import pandas as pd
import numpy as np
import os

# --- Configuration ---
MODEL_FILE = "ai_core/bldc_model.pkl"

def predict():
    print("--- BLDC Motor Performance Predictor ---")
    
    if not os.path.exists(MODEL_FILE):
        print(f"Error: Model file {MODEL_FILE} not found. Please train model first.")
        return

    # 1. Load Model
    model = joblib.load(MODEL_FILE)
    print("AI Model loaded.")
    
    # 2. Define Test Input (Hardcoded as requested)
    # Scenario: A typical drone motor size
    test_input = pd.DataFrame([{
        'stator_od': 80.0,       # mm
        'stack_length': 30.0,    # mm
        'airgap': 0.7,           # mm
        'turns_per_coil': 25,    # turns
        'magnet_rem': 1.25,      # T (N40 approx)
        'slot_pole_combo': '12N14P'
    }])
    
    print("\n--- Input Parameters ---")
    print(test_input.to_string(index=False))
    
    # 3. Predict
    # Returns numpy array
    prediction = model.predict(test_input)
    
    # Unpack (Order matches training: Kv, Torque, Weight_kg)
    kv_pred = prediction[0][0]
    torque_pred = prediction[0][1]
    weight_pred = prediction[0][2]
    
    print("\n--- AI Prediction ---")
    print(f"Kv Rating:      {kv_pred:.1f} RPM/V")
    print(f"Rated Torque:   {torque_pred:.3f} Nm")
    print(f"Est. Weight:    {weight_pred:.3f} kg")

if __name__ == "__main__":
    predict()
