import pandas as pd
import numpy as np
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# --- Configuration ---
DATA_FILE = "bldc_dataset.csv"
MODEL_FILE = "ai_core/bldc_model.pkl"

def train():
    print("--- Phase 2: AI Training Started ---")
    
    # 1. Load Data
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please run data generation first.")
        return

    df = pd.read_csv(DATA_FILE)
    print(f"Loaded {len(df)} samples.")
    
    # 2. Preprocessing
    # Features (X)
    feature_cols = ['stator_od', 'stack_length', 'airgap', 'turns_per_coil', 'magnet_rem', 'slot_pole_combo']
    X = df[feature_cols]
    
    # Targets (Y)
    # Target columns based on the CSV generated in Phase 1
    # Check generated CSV header: Kv, Torque, Kt_theoretical, Bg, Weight_kg
    # User requested: Kv_rating (Kv), Rated_Torque (Torque), Efficiency (Not in simplified script, assume 'Weight_kg' or similar proxy? 
    # Actually, in Phase 1 simple script I generated: Kv, Torque, Kt_theoretical, Bg, Weight_kg.
    # Efficiency was not in the simplified Phase 1 script (it was in the initial complex one).
    # Let's train on what we have: Kv, Torque, Weight.
    target_cols = ['Kv', 'Torque', 'Weight_kg'] 
    Y = df[target_cols]
    
    print(f"Training Features: {feature_cols}")
    print(f"Target Variables: {target_cols}")
    
    # Split Data
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    
    # 3. Pipeline Construction
    # We need to handle categorical 'slot_pole_combo'
    categorical_features = ['slot_pole_combo']
    numerical_features = ['stator_od', 'stack_length', 'airgap', 'turns_per_coil', 'magnet_rem']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])
    
    # Model: Random Forest wrapped in MultiOutput
    # RandomForest natively supports multi-output but wrapper is explicit
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', MultiOutputRegressor(RandomForestRegressor(n_estimators=100, random_state=42)))
    ])
    
    # 4. Training
    print("Training Random Forest model...")
    model.fit(X_train, y_train)
    
    # 5. Evaluation
    print("\n--- Evaluation Results ---")
    y_pred = model.predict(X_test)
    
    # Calculate metrics for each target
    # y_test is a DataFrame, y_pred is a numpy array
    metrics = {}
    for i, col in enumerate(target_cols):
        mae = mean_absolute_error(y_test[col], y_pred[:, i])
        r2 = r2_score(y_test[col], y_pred[:, i])
        metrics[col] = {'mae': mae, 'r2': r2}
        
        # Human readable print
        print(f"Target: {col}")
        print(f"  > MAE (Avg Error): ±{mae:.2f}")
        print(f"  > R² Score: {r2:.4f}")
        
    # 6. Save Model
    joblib.dump(model, MODEL_FILE)
    print(f"\nModel saved successfully to: {MODEL_FILE}")

if __name__ == "__main__":
    train()
