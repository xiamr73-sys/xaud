import pandas as pd
import numpy as np
import random
import math

# --- Constants ---
mu_0 = 4 * math.pi * 1e-7
COPPER_RHO = 1.68e-8  # Ohm*m
SLOT_FILL_FACTOR_MEAN = 0.45
SLOT_FILL_FACTOR_STD = 0.05
CURRENT_DENSITY_J = 6e6  # A/m^2 (6 A/mm^2, typical for continuous)
B_G_MEAN = 0.85  # Tesla (Airgap Flux Density for Neodymium)
B_G_STD = 0.05

def generate_bldc_design(idx):
    """
    Generates a single random BLDC motor design and calculates performance metrics
    using analytical sizing equations.
    """
    
    # --- 1. Geometric Inputs (Randomized) ---
    # Stator Outer Diameter (30mm to 150mm)
    stator_od_mm = random.uniform(30, 150)
    stator_od = stator_od_mm / 1000.0
    
    # Aspect Ratio (L/D): 0.2 to 1.5
    aspect_ratio = random.uniform(0.2, 1.5)
    stack_length = stator_od * aspect_ratio
    stack_length_mm = stack_length * 1000.0
    
    # Stator ID Ratio (0.5 to 0.75 of OD)
    split_ratio = random.uniform(0.5, 0.75)
    stator_id = stator_od * split_ratio
    stator_id_mm = stator_id * 1000.0
    
    # Airgap (0.5mm to 1.0mm typically)
    airgap_mm = random.uniform(0.3, 1.0)
    airgap = airgap_mm / 1000.0
    
    rotor_od = stator_id - 2 * airgap
    rotor_radius = rotor_od / 2.0
    
    # Slots and Poles
    # Common combos: 9N6P, 12N14P, 12N10P, 24N20P, etc.
    # Let's pick from a set of valid combinations to be realistic
    valid_combos = [
        (9, 6), (12, 8), (12, 10), (12, 14), 
        (18, 12), (18, 16), (24, 20), (24, 22),
        (36, 30), (36, 24)
    ]
    slots, poles = random.choice(valid_combos)
    
    # Winding Details
    # Randomly choose voltage target to guide turns, but ultimately turns are random integer
    # Turns per phase. Assume 3 phase.
    # Total slots = slots. Slots per phase = slots / 3.
    # Turns per slot = random integer (10 to 100)
    turns_per_slot = random.randint(5, 80)
    
    # Winding connection: Series assumed for simplicity (or parallel paths = 1)
    parallel_paths = 1
    # Total Series Turns Per Phase (N_ph)
    # N_ph = (Slots/3) * turns_per_slot / parallel_paths
    turns_per_phase = (slots / 3.0) * turns_per_slot / parallel_paths
    
    # --- 2. Physics & Performance Calculation ---
    
    # A. Magnetic Flux Loading
    # B_g with noise (simulate magnet strength variation and saturation)
    B_g = random.gauss(B_G_MEAN, B_G_STD)
    
    # B. Back-EMF Constant (Ke)
    # Ideal Trapezoidal: E = 2 * N_ph * B_g * L * r * omega
    # Ke (V/(rad/s)) = 2 * N_ph * B_g * L * r
    # We add a "Winding Factor" (kw) approx 0.9 to 0.95 for BLDC
    kw = random.uniform(0.9, 0.96)
    
    Ke_rads = 2 * turns_per_phase * B_g * stack_length * rotor_radius * kw
    
    # Add noise to Ke (geometry tolerances)
    Ke_rads *= random.uniform(0.95, 1.05)
    
    # Kv (RPM/V)
    # Kv_rads = 1 / Ke_rads
    # Kv_rpm = Kv_rads * (60 / 2pi)
    Kv_rpm = (1.0 / Ke_rads) * (30 / math.pi) if Ke_rads > 0 else 0
    
    # Kt (Nm/A)
    # For square wave drive, Kt = Ke (in SI units)
    Kt_Nm_A = Ke_rads
    
    # C. Resistance & Max Current
    # Slot Area Geometry Approx
    # Slot Pitch at Stator ID
    slot_pitch = (math.pi * stator_id) / slots
    # Tooth width approx 0.4 to 0.6 of pitch
    tooth_width_ratio = random.uniform(0.4, 0.6)
    slot_width = slot_pitch * (1 - tooth_width_ratio)
    
    # Slot Depth approx (OD - ID)/2 - BackIron
    # BackIron approx equal to Tooth Width for flux path
    back_iron = slot_pitch * tooth_width_ratio * 0.8 # rough est
    slot_depth = (stator_od - stator_id)/2.0 - back_iron
    
    # Gross Slot Area
    slot_area = slot_width * slot_depth # Rectangular approx
    
    # Copper Area
    fill_factor = random.gauss(SLOT_FILL_FACTOR_MEAN, SLOT_FILL_FACTOR_STD)
    fill_factor = max(0.3, min(0.65, fill_factor)) # Clip
    copper_area_slot = slot_area * fill_factor
    
    # Wire Area (for one conductor)
    # Total conductors in slot = 2 * turns_per_slot (usually double layer) or 1 * turns (single)
    # Let's assume conductors_per_slot = turns_per_slot (simplified, treating 'turn' as loop in slot)
    # Actually, if we say "Turns per slot", usually means conductors going through.
    # Let's assume single tooth winding or distributed:
    # Total Copper Area = Conductors_per_slot * Wire_Section_Area
    # Let's define conductors_per_slot = 2 * turns_per_slot (Go and Return in different slots? No, concentrated winding coil sides)
    # Simplified: Wire Area = copper_area_slot / turns_per_slot
    wire_area = copper_area_slot / turns_per_slot
    
    # Resistance
    # Length of turn approx = 2*L + EndTurn. EndTurn ~ 2.5 * SlotPitch
    len_turn = 2 * stack_length + 2.5 * slot_pitch
    total_wire_len_phase = len_turn * turns_per_phase
    
    # R = rho * L / A
    resistance_phase = COPPER_RHO * total_wire_len_phase / wire_area
    
    # D. Rated Torque & Efficiency
    # Rated Current determined by Current Density J (Thermal Limit)
    rated_current = CURRENT_DENSITY_J * wire_area
    
    # Rated Torque
    # T = Kt * I
    rated_torque = Kt_Nm_A * rated_current
    
    # Efficiency Estimation at Rated Point
    # Losses:
    # 1. Copper Loss = 3 * I^2 * R
    copper_loss = 3 * (rated_current ** 2) * resistance_phase
    
    # 2. Iron Loss (Hysteresis + Eddy)
    # Very rough approx: P_fe approx proportional to Volume * Freq^1.5 * B^2
    # Freq at rated speed? What is rated speed?
    # Let's assume Rated Voltage is flexible, but let's fix a reference voltage to find "Rated Speed"
    # Or derive Rated Speed from J? No.
    # Let's pick a typical V_bus for this size motor to estimate Efficiency at that point.
    # Small motor (30mm) -> 12V. Large (150mm) -> 48V.
    ref_voltage = 12 if stator_od_mm < 60 else (24 if stator_od_mm < 100 else 48)
    
    # Speed at Rated Torque & Ref Voltage
    # V = E + I*R = Ke*w + I*R
    # Ke*w = V - I*R
    # w = (V - I*R) / Ke
    voltage_drop = rated_current * resistance_phase
    if voltage_drop >= ref_voltage * 0.9:
        # Motor implies too high resistance for this voltage class, effectively stalled
        rated_speed_rads = 0
        efficiency = 0
    else:
        bemf_at_rated = ref_voltage - voltage_drop
        rated_speed_rads = bemf_at_rated / Ke_rads
        rated_speed_rpm = rated_speed_rads * 30 / math.pi
        
        # Output Power
        p_out = rated_torque * rated_speed_rads
        
        # Iron Loss Estimation
        # Vol_stator ~ pi * (Ro^2 - Ri^2) * L
        vol_stator = math.pi * (stator_od**2 - stator_id**2) * stack_length
        # Freq = p * n / 120 = poles * rpm / 120
        freq = poles * rated_speed_rpm / 120.0
        # Specific loss approx 2-5 W/kg at 50Hz, 1.5T. 
        # Scaling: P_loss ~ C * Vol * f^1.5
        # C is random noise factor
        iron_loss = 0.05 * (vol_stator * 7800) * (freq ** 1.5) * random.uniform(0.8, 1.2)
        
        # Friction/Windage
        mech_loss = 0.001 * p_out + 0.01 * (rated_speed_rpm/1000)**2
        
        total_loss = copper_loss + iron_loss + mech_loss
        efficiency = p_out / (p_out + total_loss) if p_out > 0 else 0
    
    # --- 3. Pack Data ---
    design_data = {
        "id": idx,
        "stator_od_mm": round(stator_od_mm, 2),
        "stator_id_mm": round(stator_id_mm, 2),
        "stack_length_mm": round(stack_length_mm, 2),
        "slots": slots,
        "poles": poles,
        "turns_per_slot": turns_per_slot,
        "airgap_mm": round(airgap_mm, 3),
        "ref_voltage_v": ref_voltage,
        # Performance
        "kv_rpm_v": round(Kv_rpm, 1),
        "kt_nm_a": round(Kt_Nm_A, 4),
        "rated_torque_nm": round(rated_torque, 4),
        "rated_current_a": round(rated_current, 2),
        "resistance_ohm": round(resistance_phase, 4),
        "efficiency_est": round(efficiency, 4),
        "mass_est_kg": round(vol_stator * 7800 * 1.5, 3) # Rough mass (iron + copper + rotor)
    }
    
    return design_data

def main():
    NUM_SAMPLES = 10000
    print(f"Generating {NUM_SAMPLES} synthetic BLDC motor designs...")
    
    data = []
    for i in range(NUM_SAMPLES):
        if (i+1) % 1000 == 0:
            print(f"  Progress: {i+1}/{NUM_SAMPLES}")
        
        try:
            design = generate_bldc_design(i)
            data.append(design)
        except Exception as e:
            # Skip invalid geometry calculations (e.g. negative dimensions)
            continue
            
    # Save
    df = pd.DataFrame(data)
    
    # Add some noise to the final dataset to mimic measurement error
    # e.g. Kv measurement error +/- 2%
    df['kv_rpm_v'] = df['kv_rpm_v'] * np.random.uniform(0.98, 1.02, size=len(df))
    df['rated_torque_nm'] = df['rated_torque_nm'] * np.random.uniform(0.95, 1.05, size=len(df))
    
    filename = "bldc_motor_data_10k.csv"
    df.to_csv(filename, index=False)
    print(f"Done! Saved to {filename}")
    print(df.describe())

if __name__ == "__main__":
    main()
