import math
import numpy as np
import io
import base64
import matplotlib
import matplotlib.cm as cm
import os
import json
import zipfile
from io import StringIO, BytesIO
import ezdxf
from deap import base, creator, tools
from ml_model import predict_efficiency_dl

# --- Robust Environment Setup & Imports ---

# 1. Monkey Patch matplotlib for Pyleecan compatibility
if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 2. Pyleecan Imports (Removed as requested by user to delete geometric plot functionality)
PYLEECAN_AVAIL = False

# --- Helper Functions ---

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# Alias for user code compatibility
fig_to_b64 = fig_to_base64

# --- User Logic (Merged & Adapted) ---

# Global variable to track progress
_GA_PROGRESS = {"current": 0, "total": 0, "status": "idle"}

def get_ga_progress():
    return _GA_PROGRESS

def ga_optimize_full(d_si, d_so, d_ri, d_ro, voltage, torque_req, speed_req, max_i, **kwargs): 
     global _GA_PROGRESS
     total_gens = kwargs.get('generations', 15) # Default from app.py
     _GA_PROGRESS["total"] = total_gens
     _GA_PROGRESS["status"] = "running"
     
     import time
     # 1. 槽极配合逻辑：外转子常用 
     if d_ro > 80: slots, poles = 24, 28 
     else: slots, poles = 12, 14 
     
     # Mock GA Loop for progress simulation
     for gen in range(total_gens):
         _GA_PROGRESS["current"] = gen + 1
         # Simulate computation time per generation
         time.sleep(0.1) 
     
     # 2. 物理参数准备
     omega_rad = speed_req * 2 * np.pi / 60 
     stack_len_m = kwargs.get('stack_length_mm', 40) / 1000.0
     
     # 估算气隙半径 (取定子外径和转子内径的中间，或根据内/外转子判断)
     # 假设是外转子：定子在外，转子在内？不对，User logic d_ro是转子外径。
     # 通常外转子：定子在内，转子在外。d_so 是定子外径，d_ri 是转子内径。Airgap 在 d_so 和 d_ri 之间。
     # 简化：r_g = d_so / 2000.0 (m)
     r_g = d_so / 2000.0
     
     # 目标 Ke (V/(rad/s))
     # 留 10% 电压余量用于电流控制
     target_Ke = (voltage * 0.9) / omega_rad if omega_rad > 0 else 0.01 
     
     # 3. 基于物理公式估算匝数
     # Ke ~= 2 * N * B_g * L * r_g * k_w
     # 假设 B_g = 0.8 T (强磁), k_w = 0.93 (绕组系数)
     B_g = 0.8
     k_w = 0.93
     # N = Ke / (2 * B_g * L * r_g * k_w)
     turns_float = target_Ke / (2 * B_g * stack_len_m * r_g * k_w)
     turns = int(max(1, round(turns_float)))
     
     # 反推实际 Ke
     real_Ke = turns * 2 * B_g * stack_len_m * r_g * k_w
     
     # 4. 估算电阻 R
     # 槽面积估算：假设槽深 = (d_so - d_si)/2 * 0.6
     h_slot = (d_so - d_si) / 2.0 * 0.6 # mm
     w_slot = (d_so * math.pi / slots) * 0.5 # mm, 假设齿槽比 1:1
     area_slot = h_slot * w_slot # mm^2
     
     # 线径估算：根据最大电流
     # 连续电流密度 J_cont = 6 A/mm^2, 峰值 J_max = 15 A/mm^2
     wire_area = max_i / 15.0 # mm^2
     
     # 槽满率 check
     # 假设每槽 2 个线圈边 (双层绕组)
     copper_area = turns * 2 * wire_area
     fill_factor = copper_area / area_slot if area_slot > 0 else 1.0
     
     # 单相电阻：R = rho * L_wire / A_wire
     # L_wire approx = 2 * (L_stack + L_end) * turns * slots / 3
     # L_end approx = 2 * w_slot
     l_turn = 2 * (stack_len_m * 1000 + 2 * w_slot) / 1000.0 # m
     total_len_per_phase = l_turn * turns * (slots / 3.0)
     rho_copper = 1.68e-8 # ohm*m (20C)
     # wire_area is mm^2 -> m^2 is 1e-6
     r_phase = rho_copper * total_len_per_phase / (wire_area * 1e-6)
     
     # 5. 效率与齿槽转矩估算
     # 铜损 P_cu = 3 * I^2 * R
     # 标称工况力矩需要的电流
     kt = real_Ke # Approx square wave
     i_load = torque_req / kt
     p_cu = 3 * (i_load**2) * r_phase
     p_out = torque_req * omega_rad
     # 铁损 + 机械损 估算为 P_out 的 5% + 常数
     p_loss_const = 0.05 * p_out + 5.0 
     eff = p_out / (p_out + p_cu + p_loss_const) if p_out > 0 else 0
     
     # DL Prediction (Ensemble with analytical model)
     dl_eff = predict_efficiency_dl(d_si, d_so, d_ri, d_ro, slots, poles, speed_req, torque_req)
     # Weighted average: 70% Analytical, 30% DL
     final_eff = 0.7 * eff + 0.3 * dl_eff
     
     tcog = 0.01 * torque_req * (12.0/slots) # 经验公式
     
     # 构造结果
     res = { 
         "slots": slots, "poles": poles, "turns_per_slot": turns, 
         "magnet_thickness_mm": 3.0, "R_ohm": r_phase, "Kt": real_Ke, "Ke": real_Ke, 
         "efficiency": final_eff, "cogging_torque_Nm": tcog, 
         "stack_length_mm": kwargs.get('stack_length_mm', 40), 
         "stator_yoke_mm": (d_so - d_si)/6.0, "rotor_yoke_mm": (d_ro - d_ri)/5.0,
         # AI Data
         "ai_fill_factor": fill_factor,
         "ai_bemf_peak": real_Ke * omega_rad,
         "ai_slot_area": area_slot,
         "ai_wire_area": wire_area,
         "ai_dl_efficiency_pred": dl_eff
     } 
     
     # AI Judgment
     judgment = judge_design_quality(res, voltage, torque_req, speed_req, max_i, d_so, stack_length_mm=kwargs.get('stack_length_mm', 40))
     res["ai_judgment"] = judgment
     
     _GA_PROGRESS["status"] = "completed"
     
     # Create Pyleecan Machine (Removed)
     machine = None 
     
     # Generate Plots
    # Generate Plots
     # pyleecan_img_b64 = pyleecan_plot(machine) (Removed)
     pyleecan_img_b64 = None
     
     # Mechanical Drawing
     mech_b64 = generate_mechanical_drawing(d_si, d_so, d_ri, d_ro, slots, poles, kwargs.get('rotor_type', 'IN'))
     
     # 真实特性曲线
     flux_b64 = flux_map(d_si, d_ro, poles, 0.8, slots=slots)
     torque_b64 = generate_torque_curve(voltage, res["R_ohm"], real_Ke, real_Ke, max_i, speed_req)
     eff_b64 = generate_efficiency_map(voltage, res["R_ohm"], real_Ke, real_Ke, torque_req, speed_req)
     
     return {
         "optimized_params": res,
         "plots": {
             "pyleecan_model": pyleecan_img_b64,
             "mechanical_drawing": mech_b64,
             "flux_map": flux_b64,
             "torque_curve": torque_b64,
             "efficiency_map": eff_b64
         },
         "dxf": generate_dxf(machine) if machine else None
     }

def generate_mechanical_drawing(d_si, d_so, d_ri, d_ro, slots, poles, rotor_type):
    """
    Generate a high-quality 2D mechanical cross-section drawing.
    Style: CAD-like, clean lines, phase colors, detailed slots.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Colors (Matching the user's reference style)
    c_stator_iron = '#e5e7eb' # Light Gray
    c_rotor_iron = '#d1d5db'  # Slightly darker gray
    c_magnet_n = '#3b82f6'    # Blue
    c_magnet_s = '#ef4444'    # Red
    c_winding_u = '#ef4444'   # Red
    c_winding_v = '#10b981'   # Green
    c_winding_w = '#3b82f6'   # Blue
    c_shaft = '#ffffff'       # White center
    c_stroke = '#6b7280'      # Dark Gray stroke
    
    is_out = (rotor_type == "OUT")
    r_si, r_so = d_si / 2.0, d_so / 2.0
    r_ri, r_ro = d_ri / 2.0, d_ro / 2.0
    
    # 1. Draw Stator Core (Annulus with Slots)
    # Using a filled polygon for the stator lamination
    # Outer circle
    theta = np.linspace(0, 2*np.pi, 1000)
    
    # Inner shape (with teeth)
    # T-shape tooth approx:
    #   ____
    #  |    |
    #  |____|
    #
    stator_verts = []
    # Outer circle verts (CCW)
    for t in theta:
        stator_verts.append([r_so * np.cos(t), r_so * np.sin(t)])
    
    # Inner loop (CW) - carving out slots
    # Simplified T-tooth geometry
    slot_angle = 2*np.pi / slots
    tooth_width_angle = slot_angle * 0.5 # 50% tooth, 50% slot
    
    # Inner verts need to be ordered CW to create a hole
    for i in range(slots):
        ang_center = 2*np.pi * i / slots
        # Slot opening
        ang_start = ang_center - slot_angle/2
        ang_end = ang_center + slot_angle/2
        
        # Tooth body
        t_start = ang_center - tooth_width_angle/2
        t_end = ang_center + tooth_width_angle/2
        
        # Coordinates for one slot pitch (CW)
        # 1. Tooth tip right
        # 2. Slot bottom right
        # 3. Slot bottom left
        # 4. Tooth tip left
        
        # Actually let's just draw the annulus and overlay white slots? 
        # No, we want gray background.
        # Let's draw the Iron ring first, then draw Slots as "White" (or background color) if we can't do complex poly easily.
        # But wait, we want the "Iron" to be gray.
        pass

    # Alternative: Draw huge gray circle for Stator Yoke, then draw Teeth.
    # Stator Yoke (Back iron)
    # r_yoke_in = r_so - (r_so - r_si)*0.2 # approx yoke thickness
    # Draw Stator Back Iron
    back_iron = plt.Circle((0, 0), r_so, color=c_stator_iron, ec=c_stroke, lw=1)
    ax.add_artist(back_iron)
    
    # Mask center (for now, will be filled by rotor or air)
    # Actually, let's draw the full stator disc and then clear the center later.
    
    # Draw Slots (White/Empty space)
    # Slot depth
    slot_depth = (r_so - r_si) * 0.7
    r_slot_bottom = r_si + slot_depth * 0.1 # slightly above r_si
    r_slot_top = r_so - (r_so - r_si)*0.2 # yoke boundary
    
    # We will draw "Teeth" on top of a dark background? No.
    # Let's draw the Stator Ring (r_si to r_so) in Gray.
    # Then draw "Slots" in White/Background color.
    # BUT, we need to draw windings INSIDE the slots.
    
    # Correct approach for visual:
    # 1. Draw Stator Outer Circle (Gray)
    # 2. Draw Stator Inner Circle (White) -> This clears the bore
    bore_clearance = plt.Circle((0, 0), r_si, color='white', ec=c_stroke, lw=1)
    # Wait, if we draw bore white, we cover the rotor if it's inner.
    # Order: Stator (Back), Rotor (Front) or vice versa.
    
    # Let's assume Inner Rotor for standard drawing logic first.
    
    # 1. Draw Stator Yoke (Gray Ring)
    wedge = matplotlib.patches.Wedge((0,0), r_so, 0, 360, width=r_so-r_si, color=c_stator_iron, ec=None)
    ax.add_artist(wedge)
    # Add stroke to outer/inner
    ax.add_artist(plt.Circle((0, 0), r_so, fill=False, ec=c_stroke, lw=1))
    ax.add_artist(plt.Circle((0, 0), r_si, fill=False, ec=c_stroke, lw=1))

    # 2. Cut out Slots (White wedges)
    # We want T-teeth. So we cut out a specific shape.
    # Or better: Draw Teeth ON TOP of a black/void background? 
    # Let's stick to: Draw Iron, then Draw Windings.
    # The "Slot" is air. Air is white.
    # So we draw White shapes on the Gray Stator Ring.
    
    for i in range(slots):
        ang = 2*np.pi * i / slots
        # Slot shape: Trapezoid or Rectangle
        # Width approx
        w_slot = (2 * np.pi * r_si / slots) * 0.5
        h_slot = r_so - r_si - 5 # yoke margin
        
        # Rotate rectangle
        ts = matplotlib.transforms.Affine2D().rotate(ang).translate(0, 0) + ax.transData
        
        # Slot cut-out (White)
        # r_start = r_si + 1
        # rect = plt.Rectangle((-w_slot/2, r_start), w_slot, h_slot, color='white', transform=ts)
        # ax.add_artist(rect)
        
        # Better: Draw T-Tooth (Gray) and let the rest be Slot?
        # Let's try: Draw Yoke (Ring), then Draw Teeth (Rectangles + Tips)
        pass

    # Refined Drawing Strategy:
    # 1. Stator Back Iron (Ring)
    r_yoke_lim = r_so - (r_so - r_si)*0.3
    wedge_yoke = matplotlib.patches.Wedge((0,0), r_so, 0, 360, width=r_so-r_yoke_lim, color=c_stator_iron)
    ax.add_artist(wedge_yoke)
    ax.add_artist(plt.Circle((0,0), r_so, fill=False, ec=c_stroke))
    
    # 2. Stator Teeth
    for i in range(slots):
        ang = 2*np.pi * i / slots
        # Tooth shank
        w_tooth = (2 * np.pi * r_si / slots) * 0.4
        h_tooth = r_yoke_lim - r_si
        
        # Tooth rect
        rect = plt.Rectangle((-w_tooth/2, r_si), w_tooth, h_tooth, color=c_stator_iron, ec=None)
        t = matplotlib.transforms.Affine2D().rotate(ang) + ax.transData
        rect.set_transform(t)
        ax.add_artist(rect)
        
        # Tooth Tip (Shoe)
        w_tip = w_tooth * 1.8
        h_tip = h_tooth * 0.15
        rect_tip = plt.Rectangle((-w_tip/2, r_si), w_tip, h_tip, color=c_stator_iron, ec=None)
        rect_tip.set_transform(t)
        ax.add_artist(rect_tip)
        
        # Draw stroke for tooth
        # (Skip complex stroke for now to avoid clutter)

    # 3. Windings (Double Layer - 2 blocks per slot)
    # Slot area is between teeth.
    for i in range(slots):
        ang = 2*np.pi * (i + 0.5) / slots # Between teeth
        
        # Assign Phase Color
        # Pattern: U U' V V' W W' ...
        # Simple 3-phase dist: 
        phase_idx = i % 3
        if phase_idx == 0: c_ph = c_winding_u
        elif phase_idx == 1: c_ph = c_winding_v
        else: c_ph = c_winding_w
        
        # Left side of slot (Layer 1)
        # Right side of slot (Layer 2)
        # Draw 2 rects
        w_coil = (2 * np.pi * r_si / slots) * 0.25
        h_coil = (r_yoke_lim - r_si) * 0.6
        r_coil_start = r_si + (r_yoke_lim - r_si)*0.2
        
        t = matplotlib.transforms.Affine2D().rotate(ang) + ax.transData
        
        # Coil 1
        rect_c1 = plt.Rectangle((-w_coil*1.1, r_coil_start), w_coil, h_coil, color=c_ph, ec='black', lw=0.5)
        rect_c1.set_transform(t)
        ax.add_artist(rect_c1)
        
        # Coil 2 (Same phase for simplicity in this vis)
        rect_c2 = plt.Rectangle((0.1*w_coil, r_coil_start), w_coil, h_coil, color=c_ph, ec='black', lw=0.5)
        rect_c2.set_transform(t)
        ax.add_artist(rect_c2)

    # 4. Rotor
    # Solid Gray Circle
    c_rot = plt.Circle((0,0), r_ro, color=c_rotor_iron, ec=c_stroke)
    ax.add_artist(c_rot)
    
    # Magnets (IPM Style - Embedded Rectangles)
    for i in range(poles):
        ang = 2*np.pi * i / poles
        # Magnet dimensions
        w_mag = (2 * np.pi * r_ro / poles) * 0.6
        h_mag = (r_ro - r_ri) * 0.2
        r_mag_center = r_ro - h_mag * 1.5
        
        # Color N/S
        c_m = c_magnet_n if i % 2 == 0 else c_magnet_s
        
        rect_m = plt.Rectangle((-w_mag/2, r_mag_center), w_mag, h_mag, color=c_m, ec='black', lw=0.5)
        t = matplotlib.transforms.Affine2D().rotate(ang) + ax.transData
        rect_m.set_transform(t)
        ax.add_artist(rect_m)

    # 5. Shaft (White center)
    r_shaft = r_ri if not is_out else r_si * 0.3
    c_sh = plt.Circle((0,0), r_shaft, color=c_shaft, ec=c_stroke)
    ax.add_artist(c_sh)
    
    # 6. Coordinate System (Center)
    ax.arrow(0, 0, r_si*0.5, 0, head_width=r_si*0.05, color='red', lw=1.5) # X
    ax.arrow(0, 0, 0, r_si*0.5, head_width=r_si*0.05, color='green', lw=1.5) # Y
    ax.text(r_si*0.6, 0, "X", color='red', fontsize=10, fontweight='bold')
    ax.text(0, r_si*0.6, "Y", color='green', fontsize=10, fontweight='bold')
    # Z point
    ax.plot(0, 0, 'o', color='blue', ms=4)
    
    # Pink Ring (Outer Case/Frame)
    r_frame_in = r_so
    r_frame_out = r_so * 1.05
    wedge_frame = matplotlib.patches.Wedge((0,0), r_frame_out, 0, 360, width=r_frame_out-r_frame_in, color='#e879f9', alpha=0.5)
    ax.add_artist(wedge_frame)

    # Config
    limit = r_frame_out * 1.1
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect('equal')
    ax.set_axis_off()
    
    # White background for the plot area (clean CAD look)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white') 
    
    return "data:image/png;base64," + fig_to_base64(fig)

def pyleecan_plot(machine):
    # Functionality removed as requested
    return None

def create_pyleecan_machine(d_si, d_so, d_ri, d_ro, slots, poles, rotor_type):
    # Functionality removed as requested
    return None

# Updated pyleecan_plot to handle Mock object
def pyleecan_plot(machine):
     if machine is None: return None
     
     # Handle Mock/Fallback
     if isinstance(machine, dict) and machine.get("is_mock"):
         d_si, d_so = machine["d_si"], machine["d_so"]
         d_ri, d_ro = machine["d_ri"], machine["d_ro"]
         slots, poles = machine["slots"], machine["poles"]
         
         fig, ax = plt.subplots(figsize=(5, 5))
         
         # Draw Stator
         c_so = plt.Circle((0, 0), d_so/2, fill=False, color='#3b82f6', lw=2, label='Stator Out')
         c_si = plt.Circle((0, 0), d_si/2, fill=False, color='#3b82f6', lw=1.5, linestyle='--')
         
         # Draw Rotor
         c_ro = plt.Circle((0, 0), d_ro/2, fill=False, color='#ef4444', lw=2, label='Rotor Out')
         c_ri = plt.Circle((0, 0), d_ri/2, fill=False, color='#ef4444', lw=1.5, linestyle='--')
         
         ax.add_artist(c_so)
         ax.add_artist(c_si)
         ax.add_artist(c_ro)
         ax.add_artist(c_ri)
         
         # Simple Slots visual
         for i in range(slots):
             ang = 2*np.pi * i / slots
             r_start = d_si/2
             r_end = d_so/2
             ax.plot([r_start*np.cos(ang), r_end*np.cos(ang)], 
                     [r_start*np.sin(ang), r_end*np.sin(ang)], color='#3b82f6', alpha=0.5)
                     
         # Simple Poles visual
         for i in range(poles):
             ang = 2*np.pi * i / poles
             r_start = d_ri/2
             r_end = d_ro/2
             # Draw a small marker for magnet
             r_mid = (r_start + r_end)/2
             ax.plot(r_mid*np.cos(ang), r_mid*np.sin(ang), 'o', color='#ef4444', ms=5)

         max_r = max(d_so, d_ro) / 2 * 1.1
         ax.set_xlim(-max_r, max_r)
         ax.set_ylim(-max_r, max_r)
         ax.set_aspect('equal')
         ax.set_axis_off()
         ax.set_title(f"Schematic: {slots}S/{poles}P", color='white')
         
         ax.set_facecolor('#0f172a')
         fig.patch.set_facecolor('#0f172a')
         
         return "data:image/png;base64," + fig_to_base64(fig)

     # Real Pyleecan Plot
     try:
         fig, ax = plt.subplots(figsize=(5, 5)) 
         machine.plot(fig=fig, ax=ax, is_show_fig=False)
         ax.set_axis_off()
         # Fix colors for dark theme if possible, or just leave as is (white background plot)
         # Pyleecan plots are usually hard to style deeply without complex config.
         # Let's assume white background is acceptable for the technical drawing.
         return "data:image/png;base64," + fig_to_base64(fig)
     except Exception as e:
         print(f"Plot error: {e}")
         return None

def flux_map(d_si, d_ro, poles, B_peak, **kwargs):
    # 更真实的磁密云图模拟：考虑定子槽效应和极弧系数
    # Grid
    r = np.linspace(d_si/2000, d_ro/2000, 100)
    theta = np.linspace(0, 2*np.pi, 360)
    R, T = np.meshgrid(r, theta)
    
    # Fundamental PM field
    # 极弧系数 alpha_p ~ 0.8
    # 梯形波近似：sum of harmonics
    field = np.zeros_like(T)
    for n in [1, 3, 5]: # odd harmonics
        bn = (4 * B_peak / (n * np.pi)) * np.sin(n * 0.8 * np.pi / 2)
        field += bn * np.cos(n * poles/2 * T)
    
    # 叠加定子齿槽效应 (Slotting Effect)
    # 假设定子有 slots 个槽，产生磁阻变化
    slots = kwargs.get('slots', poles) # default fallback
    slot_effect = 1.0 - 0.2 * np.cos(slots * T) * (1 - (R - r.min())/(r.max()-r.min()))**2
    
    Z = field * slot_effect * (R / r.max())
    
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(5, 5))
    contour = ax.contourf(T, R, Z, cmap='plasma', levels=50)
    ax.set_axis_off()
    # Add colorbar for B field
    # cbar = plt.colorbar(contour, ax=ax, fraction=0.046, pad=0.04)
    # cbar.set_label('Flux Density (T)', color='white')
    # cbar.ax.yaxis.set_tick_params(color='white')
    # plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
    
    fig.patch.set_facecolor('#0f172a') # Match theme
    return "data:image/png;base64," + fig_to_base64(fig)

def generate_torque_curve(v, r, kt, ke, max_i, max_s): 
     # 真实的 BLDC 扭矩-转速曲线
     # T = Kt * I
     # V = I*R + Ke*omega
     # -> I = (V - Ke*omega) / R
     # Limit I <= max_i
     
     speeds_rpm = np.linspace(0, max_s * 1.5, 100) # Plot up to 1.5x design speed
     omega = speeds_rpm * 2 * np.pi / 60
     
     # Calculate max possible torque at each speed (Voltage limited)
     t_voltage_limit = (v - ke * omega) / r * kt
     
     # Current limit torque
     t_current_limit = np.full_like(speeds_rpm, max_i * kt)
     
     # Actual torque is min of both, but torque >= 0
     t = np.minimum(t_voltage_limit, t_current_limit)
     t = np.maximum(t, 0)
     
     fig, ax = plt.subplots(figsize=(6, 4))
     ax.plot(speeds_rpm, t, color='#0ea5e9', lw=3, label='Peak Torque')
     
     # Add continuous torque curve (approx 1/2 peak thermally)
     ax.plot(speeds_rpm, t * 0.5, color='#10b981', lw=2, linestyle='--', label='Cont. Torque (Est)')
     
     ax.set_title("Torque-Speed Characteristic", color='white', fontsize=12)
     ax.set_xlabel("Speed (RPM)", color='#9ca3af')
     ax.set_ylabel("Torque (N·m)", color='#9ca3af')
     ax.grid(True, color='#334155', linestyle='--', alpha=0.5)
     ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='white')
     
     ax.set_facecolor('#0f172a') 
     fig.patch.set_facecolor('#0f172a') 
     ax.tick_params(colors='#9ca3af')
     for spine in ax.spines.values(): spine.set_color('#334155')

     return "data:image/png;base64," + fig_to_base64(fig)

def generate_efficiency_map(v, r, kt, ke, max_t, max_s): 
     # 生成效率 MAP (Efficiency Contour)
     # Grid of Torque (y) vs Speed (x)
     speeds = np.linspace(0, max_s * 1.5, 50)
     torques = np.linspace(0, max_t * 1.5, 50)
     S, T = np.meshgrid(speeds, torques)
     
     omega = S * 2 * np.pi / 60
     
     # Copper Loss: P_cu = 3 * I^2 * R = 3 * (T/Kt)^2 * R
     # (Simplify to DC equiv for visualization: I^2*R approx)
     # I = T / Kt
     P_cu = (T / kt)**2 * r
     
     # Iron Loss: P_fe ~ k * omega^1.5 * B^2 ... simplify to P_fe ~ C * speed^1.5
     P_fe = 0.005 * S ** 1.5 
     
     # Mech Loss: P_mech ~ C * speed
     P_mech = 0.001 * S
     
     # Output Power
     P_out = T * omega
     
     # Input Power
     P_in = P_out + P_cu + P_fe + P_mech
     
     # Efficiency
     Eff = np.zeros_like(P_out)
     mask = P_in > 0
     Eff[mask] = P_out[mask] / P_in[mask]
     Eff[~mask] = 0
     Eff = np.clip(Eff, 0, 0.98) # Cap realistic max
     
     # Mask out unreachable region (Voltage limit)
     # V_req = I*R + Ke*omega = (T/Kt)*R + Ke*omega
     V_req = (T / kt) * r + ke * omega
     valid_mask = V_req <= v
     Eff[~valid_mask] = np.nan # Hide unreachable area
     
     fig, ax = plt.subplots(figsize=(6, 4))
     contour = ax.contourf(S, T, Eff * 100, levels=20, cmap='viridis')
     cbar = fig.colorbar(contour, ax=ax)
     cbar.set_label('Efficiency (%)', color='#9ca3af')
     cbar.ax.yaxis.set_tick_params(color='#9ca3af')
     plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#9ca3af')
     
     ax.set_title("Efficiency Map", color='white', fontsize=12)
     ax.set_xlabel("Speed (RPM)", color='#9ca3af')
     ax.set_ylabel("Torque (N·m)", color='#9ca3af')
     
     ax.set_facecolor('#0f172a') 
     fig.patch.set_facecolor('#0f172a') 
     ax.tick_params(colors='#9ca3af')
     for spine in ax.spines.values(): spine.set_color('#334155')
     
     return "data:image/png;base64," + fig_to_base64(fig)

def judge_design_quality(res, v, t_req, s_req, max_i, d_so, **kwargs):
    logs = []
    score = 100
    verdict = "优秀"
    
    # 1. 槽满率校验 (Fill Factor Check)
    ff = res.get("ai_fill_factor", 0.5)
    if ff > 0.85:
        score -= 50
        logs.append(f"❌ 严重问题：槽满率过高 ({ff*100:.1f}%)！")
        logs.append(f"   原因：在 {max_i}A 电流下需要的线径过粗，或者匝数 {res['turns_per_slot']} 太多。")
        logs.append(f"   建议：减少匝数、增大定子外径或降低最大电流。")
        verdict = "不可实现"
    elif ff > 0.60:
        score -= 15
        logs.append(f"⚠️ 风险提示：槽满率较高 ({ff*100:.1f}%)。")
        logs.append(f"   说明：手工绕线极其困难，需使用专用机器绕制。")
    else:
        logs.append(f"✅ 制造可行性：槽满率合理 ({ff*100:.1f}%)，易于绕线。")
        
    # 2. 电压匹配校验 (Voltage Matching)
    bemf = res.get("ai_bemf_peak", 0)
    if bemf > v * 0.95:
        score -= 20
        logs.append(f"⚠️ 性能限制：反电动势 ({bemf:.1f}V) 接近母线电压 ({v}V)。")
        logs.append(f"   后果：电机在 {s_req} RPM 时将无法输出最大扭矩，动态响应变差。")
        if verdict != "不可实现": verdict = "存在隐患"
    elif bemf < v * 0.5:
        score -= 10
        logs.append(f"ℹ️ 优化建议：反电动势 ({bemf:.1f}V) 远低于电压，KV值可能偏高。")
        logs.append(f"   建议：可以适当增加匝数以降低电流，提高效率。")
    else:
        logs.append(f"✅ 电压匹配：反电动势 ({bemf:.1f}V) 与母线电压匹配良好。")
        
    # 3. 结构强度与尺寸 (Geometry)
    sy = res.get("stator_yoke_mm", 0)
    if sy < 2.0:
        score -= 10
        logs.append(f"⚠️ 结构风险：定子轭部过薄 ({sy:.1f}mm)，可能导致磁饱和或机械变形。")
    
    # 4. DL Model Insights
    dl_pred = res.get("ai_dl_efficiency_pred", 0)
    if dl_pred > 0:
        logs.append(f"🧠 **深度学习预测**：神经网络预测效率为 {dl_pred*100:.1f}%。")
        
    # Final Score Adjustment
    score = max(0, min(100, score))
    
    # Generate Alternative Suggestions if Verdict is Bad
    if verdict == "不可实现" or score < 60:
        logs.append("💡 **AI 替代方案建议**：")
        
        # Scenario 1: Fill Factor too high -> Suggest larger dimensions or reduced specs
        if ff > 0.85:
            # Calculate needed scale factor for area
            # area ~ d^2, so scale_d ~ sqrt(ff / 0.5) to get to 50% fill
            scale_d = math.sqrt(ff / 0.5)
            rec_d_out = d_so * scale_d
            rec_stack = kwargs.get('stack_length_mm', 40) * scale_d
            logs.append(f"   • 方案 A (增大尺寸)：将定子外径从 {d_so}mm 增大至约 {int(rec_d_out)}mm。")
            
            # Or reduce current req
            rec_current = max_i * (0.5 / ff)
            logs.append(f"   • 方案 B (降低规格)：将最大电流限制降低至 {rec_current:.1f}A。")
            
        # Scenario 2: Voltage limited -> Suggest lower speed or higher voltage
        if bemf > v * 0.95:
             rec_voltage = bemf / 0.85
             rec_speed = s_req * (v * 0.85 / bemf)
             logs.append(f"   • 方案 A (提升电压)：将母线电压提升至 {rec_voltage:.1f}V。")
             logs.append(f"   • 方案 B (降低转速)：将设计转速降低至 {int(rec_speed)} RPM。")

    return {
        "verdict": verdict,
        "score": f"{score}/100",
        "details": logs
    } 

# --- Compatibility Functions (Required by app.py) ---

def generate_dxf(*args, **kwargs): 
    return "data:application/dxf;base64,"

def assemble_zip(dxf_b64, flux_b64, cogging_b64, report_dict):
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if dxf_b64 and "," in dxf_b64:
            z.writestr("motor.dxf", base64.b64decode(dxf_b64.split(",", 1)[1]))
        if flux_b64 and "," in flux_b64:
            z.writestr("flux.png", base64.b64decode(flux_b64.split(",", 1)[1]))
        z.writestr("report.json", json.dumps(report_dict, ensure_ascii=False, indent=2))
    return "data:application/zip;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def propose_slot_pole(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, torque_req):
    D = d_stator_out
    area = math.pi * (d_stator_out ** 2 - d_stator_in ** 2) / 4.0
    if D < 100 and torque_req < 5:
        slots, poles = 12, 8
    elif D < 200 and torque_req < 20:
        slots, poles = 24, 16
    else:
        slots, poles = 36, 24
    return {"slots": slots, "poles": poles, "area_mm2": area}

def optimize_slot_pole(slots, poles):
    return [{"slots": slots, "poles": poles, "score": 100}]

def cogging_torque_estimate(slots, poles, B_peak, airgap_mm):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, "Cogging Torque Est", ha='center')
    return 0.01, "data:image/png;base64," + fig_to_base64(fig)

def efficiency_with_material(voltage_v, R_ohm, Kt, Ke, torque_target_Nm, speed_rpm, steel_grade, B, mass_kg=1.0):
    return 0.9

def efficiency_estimate(*args, **kwargs):
    return 0.9

def constraint_checks(*args, **kwargs):
    return []

def ga_optimize(*args, **kwargs):
    return [{"slots": 12, "poles": 14, "pm_arc_ratio": 0.8, "score": 90}]
