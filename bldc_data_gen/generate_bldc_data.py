import numpy as np
import pandas as pd
import random
import re

# --- Configuration ---
NUM_SAMPLES = 10000
OUTPUT_FILE = "bldc_dataset.csv"

# Valid Slot/Pole Combinations (Common for BLDC)
SLOT_POLE_COMBOS = [
    "9N6P", "12N8P", "12N10P", "12N14P", 
    "18N16P", "24N20P", "24N22P", "36N30P"
]

def parse_combo(combo_str):
    """Parses '12N14P' into slots=12, poles=14"""
    match = re.match(r"(\d+)N(\d+)P", combo_str)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 12, 14 # Default fallback

def calculate_bldc_performance(row):
    """
    Physics engine to estimate motor performance based on geometry.
    """
    # Unpack inputs
    D_out_mm = row['stator_od']
    L_mm = row['stack_length']
    g_mm = row['airgap']
    N_coil = row['turns_per_coil'] # Turns per tooth/coil
    Br = row['magnet_rem']
    combo = row['slot_pole_combo']
    
    slots, poles = parse_combo(combo)
    
    # --- 1. Geometry Derivation ---
    # Convert to meters
    D_out = D_out_mm / 1000.0
    L = L_mm / 1000.0
    g = g_mm / 1000.0
    
    # Assumptions for internal geometry
    # Stator ID ratio (approx 0.6 of OD)
    D_in = D_out * 0.6
    # Rotor OD = Stator ID - 2*Airgap
    D_rotor = D_in - 2*g
    r_airgap = D_in / 2.0
    
    # --- 2. Magnetic Physics ---
    # Airgap Flux Density (Bg)
    # Bg approx Br * PC (Permeance Coefficient)
    # Simplified: Bg = Br * 0.8
    Bg = Br * 0.8
    
    # Flux per Pole (Phi)
    # Area_pole = (Circumference / Poles) * Length
    # Account for magnet coverage (alpha_p approx 0.7-0.8)
    alpha_p = 0.75
    pole_pitch = (np.pi * D_rotor) / poles
    area_pole = pole_pitch * alpha_p * L
    
    Phi = Bg * area_pole
    
    # --- 3. Winding & Kv Calculation ---
    # Winding Factor (kw) - simplified for concentrated winding
    # Usually 0.866 to 0.966 for these combos
    kw = 0.93 
    
    # Total Series Turns Per Phase (N_phase)
    # Assumption: 3-Phase, all coils in series (simplified)
    # Coils per phase = Slots / 3
    coils_per_phase = slots / 3.0
    N_phase = coils_per_phase * N_coil
    
    # Back-EMF Constant (Ke) in V/(rad/s)
    # E = 2 * N_phase * kw * Phi * (poles/2) * omega ? 
    # Standard formula: Ke = 2 * N_phase * B_avg * L * r
    # Or Ke = N_phase * kw * Phi * (poles / 2) * (2/pi)?
    # Let's use the robust one: Ke = k_shape * N_phase * Phi * P/2
    # For trapezoidal/sinusoidal, approx:
    Ke_rads = 2 * N_phase * kw * Phi * (poles / 2.0) / np.sqrt(2) # RMS approximation
    
    # Kv (RPM/V)
    # Kv = 60 / (2 * pi * Ke)
    if Ke_rads <= 0: Ke_rads = 0.001
    Kv = 9.55 / Ke_rads
    
    # --- 4. Torque Calculation ---
    # Torque Constant Kt (Nm/A)
    # Theoretically Kt = Ke (in SI units for 3-phase)
    Kt = Ke_rads
    
    # Rated Torque Estimation
    # We need Rated Current (I_rated).
    # Estimate Slot Area -> Copper Area -> Wire Gauge -> Current Capacity
    # Slot Pitch at ID
    slot_pitch_id = (np.pi * D_in) / slots
    # Tooth width (approx 0.5 pitch)
    w_tooth = slot_pitch_id * 0.5
    # Slot depth (approx (OD-ID)/2 - yoke)
    yoke = (D_out - D_in) / 6.0
    h_slot = (D_out - D_in) / 2.0 - yoke
    
    slot_area = (slot_pitch_id * 0.6) * h_slot # Rough rect area
    
    # Copper fill
    fill_factor = 0.4
    copper_area = slot_area * fill_factor
    # Wire area per turn (assuming N_coil turns fill the slot)
    # 2 coil sides per slot usually
    wire_area_mm2 = (copper_area * 1e6) / (2 * N_coil)
    
    # Current Density J (A/mm^2) - Randomize slightly for "design choice"
    J = np.random.uniform(5.0, 8.0) 
    I_rated = J * wire_area_mm2
    
    Torque_rated = Kt * I_rated
    
    # --- 5. Add Noise (Measurement Error) ---
    # +/- 5% Noise
    noise_kv = np.random.normal(1.0, 0.05)
    noise_tau = np.random.normal(1.0, 0.05)
    
    Kv_final = Kv * noise_kv
    Torque_final = Torque_rated * noise_tau
    
    return pd.Series({
        "Kv": round(Kv_final, 1),
        "Torque": round(Torque_final, 3),
        "Kt_theoretical": round(Kt, 4),
        "Bg": round(Bg, 2),
        "Weight_kg": round(np.pi * (D_out/2)**2 * L * 7800 * 0.6, 2) # Rough mass est
    })

def main():
    print(f"Generating {NUM_SAMPLES} samples...")
    
    # 1. Generate Random Inputs
    df = pd.DataFrame({
        "stator_od": np.random.uniform(40, 120, NUM_SAMPLES).round(1),
        "stack_length": np.random.uniform(10, 60, NUM_SAMPLES).round(1),
        "airgap": np.random.uniform(0.5, 1.0, NUM_SAMPLES).round(2),
        "turns_per_coil": np.random.randint(10, 100, NUM_SAMPLES),
        "magnet_rem": np.random.uniform(1.1, 1.3, NUM_SAMPLES).round(2),
        "slot_pole_combo": np.random.choice(SLOT_POLE_COMBOS, NUM_SAMPLES)
    })
    
    # 2. Apply Physics Engine
    # Use pandas apply for vectorization-like row processing
    outputs = df.apply(calculate_bldc_performance, axis=1)
    
    # 3. Combine Input + Output
    final_df = pd.concat([df, outputs], axis=1)
    
    # 4. Save
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Successfully generated {len(final_df)} samples to {OUTPUT_FILE}")
    print("\nSample Data:")
    print(final_df.head())

if __name__ == "__main__":
    main()
