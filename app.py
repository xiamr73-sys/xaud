import matplotlib.cm
import matplotlib.pyplot as plt

# Patch matplotlib for pyleecan compatibility (matplotlib >= 3.9)
if not hasattr(matplotlib.cm, 'register_cmap'):
    import matplotlib
    def register_cmap(name=None, cmap=None, override_builtin=False):
        if name is None:
            name = cmap.name
        try:
            matplotlib.colormaps.register(cmap, name=name, force=override_builtin)
        except (ValueError, TypeError):
            pass
    matplotlib.cm.register_cmap = register_cmap

if not hasattr(matplotlib.cm, 'get_cmap'):
    import matplotlib
    def get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    matplotlib.cm.get_cmap = get_cmap

from flask import Flask, render_template, request, jsonify
from sim import simulate_bldc
from design import (
    propose_slot_pole,
    generate_dxf,
    flux_map,
    cogging_torque_estimate,
    efficiency_estimate,
    create_pyleecan_machine,
    pyleecan_plot,
    optimize_slot_pole,
    constraint_checks,
    assemble_zip,
    efficiency_with_material,
    ga_optimize,
)
import matplotlib
import matplotlib.cm as cm
if not hasattr(cm, "register_cmap"):
    def _register_cmap(cmap=None, name=None, colors=None, data=None, lut=None, **kwargs):
        try:
            if cmap is not None:
                matplotlib.colormaps.register(cmap)
            elif data is not None:
                from matplotlib.colors import LinearSegmentedColormap
                matplotlib.colormaps.register(LinearSegmentedColormap(name or "custom", data, lut=lut))
            elif colors is not None:
                from matplotlib.colors import ListedColormap
                matplotlib.colormaps.register(ListedColormap(colors, name or "custom"))
        except Exception:
            pass
    cm.register_cmap = _register_cmap
import os
PYLEECAN_ERROR = None
# Use /tmp for serverless environment compatibility (read-only filesystem)
SAFE_USER_DIR = os.path.join("/tmp", ".pyleecan")
os.makedirs(SAFE_USER_DIR, exist_ok=True)
os.environ.setdefault("PYLEECAN_USER_DIR", SAFE_USER_DIR)
os.environ.setdefault("PYLEECAN_CONFIG_DIR", SAFE_USER_DIR)
try:
    import pyleecan
    PYLEECAN_AVAILABLE = True
    PYLEECAN_VERSION = getattr(pyleecan, "__version__", "unknown")
except Exception as e:
    PYLEECAN_AVAILABLE = False
    PYLEECAN_VERSION = "unavailable"
    PYLEECAN_ERROR = repr(e)

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/simulate", methods=["POST"])
def simulate():
    data = {
        "voltage_v": request.form.get("voltage_v", "24"),
        "R_ohm": request.form.get("R_ohm", "0.2"),
        "Kt_Nm_per_A": request.form.get("Kt_Nm_per_A", "0.05"),
        "Ke_Vs_per_rad": request.form.get("Ke_Vs_per_rad", "0.05"),
        "B_Nm_s_per_rad": request.form.get("B_Nm_s_per_rad", "0.0005"),
        "v_bus_v": request.form.get("v_bus_v", request.form.get("voltage_v", "24")),
        "pwm_duty": request.form.get("pwm_duty", "1.0"),
    }
    result = simulate_bldc(data)
    return jsonify(result)


@app.route("/design", methods=["POST"])
def design():
    d_stator_in = float(request.form.get("d_stator_in_mm", "60"))
    d_stator_out = float(request.form.get("d_stator_out_mm", "120"))
    d_rotor_in = float(request.form.get("d_rotor_in_mm", "20"))
    d_rotor_out = float(request.form.get("d_rotor_out_mm", "58"))
    rotor_type = request.form.get("rotor_type", "IN")
    voltage_v = float(request.form.get("voltage_v", "24"))
    torque_req = float(request.form.get("torque_req_Nm", "5"))
    R_ohm = float(request.form.get("R_ohm", "0.2"))
    Kt = float(request.form.get("Kt_Nm_per_A", "0.05"))
    Ke = float(request.form.get("Ke_Vs_per_rad", "0.05"))
    B = float(request.form.get("B_peak_T", "0.9"))
    min_slot_w = float(request.form.get("min_slot_width_mm", "1.0"))
    slots_poles = propose_slot_pole(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, torque_req)
    slots = int(slots_poles["slots"])
    poles = int(slots_poles["poles"])
    dxf_b64 = generate_dxf(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, slots, poles, rotor_type=rotor_type)
    flux_b64 = flux_map(d_stator_in, d_rotor_out, poles, B, rotor_type=rotor_type, d_stator_out=d_stator_out, d_rotor_in=d_rotor_in)
    T_cog, cogging_b64 = cogging_torque_estimate(slots, poles, B, (d_stator_in - d_rotor_out) / 2.0)
    speed_rpm = float(request.form.get("design_speed_rpm", "3000"))
    steel_grade = request.form.get("steel_grade", "35WW270")
    eff = efficiency_with_material(voltage_v, R_ohm, Kt, Ke, torque_req, speed_rpm, steel_grade, B, mass_kg=1.0)
    materials = {
        "stator_core": steel_grade,
        "rotor_core": steel_grade,
        "magnet": request.form.get("magnet_grade", "N35"),
    }
    warns = constraint_checks(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, slots, min_slot_w)
    opts = optimize_slot_pole(slots, poles)
    
    # Pyleecan Geometry
    machine = create_pyleecan_machine(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, slots, poles, rotor_type)
    pyleecan_img_b64 = pyleecan_plot(machine)
    
    report = {
        "inputs": {
            "d_stator_in_mm": d_stator_in,
            "d_stator_out_mm": d_stator_out,
            "d_rotor_in_mm": d_rotor_in,
            "d_rotor_out_mm": d_rotor_out,
            "rotor_type": rotor_type,
            "torque_req_Nm": torque_req,
            "B_peak_T": B,
            "design_speed_rpm": speed_rpm,
        },
        "outputs": {
            "slots": slots,
            "poles": poles,
            "efficiency": eff,
            "cogging_torque_Nm": T_cog,
            "materials": materials,
            "warnings": warns,
            "optimize": opts,
        },
    }
    zip_b64 = assemble_zip(dxf_b64, flux_b64, cogging_b64, report)
    return jsonify(
        {
            "slots": slots,
            "poles": poles,
            "dxf_base64": dxf_b64,
            "flux_map_base64": flux_b64,
            "cogging_torque_Nm": T_cog,
            "cogging_curve_base64": cogging_b64,
            "efficiency": eff,
            "materials": materials,
            "warnings": warns,
            "optimize": opts,
            "zip_base64": zip_b64,
            "pyleecan_image_base64": pyleecan_img_b64,
        }
    )


@app.route("/auto_design", methods=["POST"])
def auto_design():
    # 1. Parse Inputs
    d_stator_in = float(request.form.get("d_stator_in_mm", "60"))
    d_stator_out = float(request.form.get("d_stator_out_mm", "120"))
    d_rotor_in = float(request.form.get("d_rotor_in_mm", "20"))
    d_rotor_out = float(request.form.get("d_rotor_out_mm", "58"))
    rotor_type = request.form.get("rotor_type", "IN")
    voltage_v = float(request.form.get("voltage_v", "24"))
    torque_req = float(request.form.get("torque_req_Nm", "5"))
    speed_req = float(request.form.get("design_speed_rpm", "3000"))
    max_current = float(request.form.get("max_current_a", "30"))
    generations = int(request.form.get("generations", "15"))
    cogging_req = float(request.form.get("cogging_req_Nm", "0.05"))
    stack_length = float(request.form.get("stack_length_mm", "40"))
    
    # 2. Run GA Optimization
    from design import ga_optimize_full, generate_efficiency_map, generate_torque_curve, judge_design_quality
    
    opt_res = ga_optimize_full(
        d_stator_in, d_stator_out, d_rotor_in, d_rotor_out,
        voltage_v, torque_req, speed_req, max_current,
        rotor_type=rotor_type, generations=generations, pop_size=40,
        max_cogging_torque_Nm=cogging_req, stack_length_mm=stack_length
    )
    
    # 3. Extract Optimized Params
    slots = int(opt_res["optimized_params"]["slots"])
    poles = int(opt_res["optimized_params"]["poles"])
    turns = int(opt_res["optimized_params"]["turns_per_slot"])
    mag_th = float(opt_res["optimized_params"]["magnet_thickness_mm"])
    R_ohm = float(opt_res["optimized_params"]["R_ohm"])
    Kt = float(opt_res["optimized_params"]["Kt"])
    Ke = float(opt_res["optimized_params"]["Ke"])
    eff = float(opt_res["optimized_params"]["efficiency"])
    tcog_val = float(opt_res["optimized_params"].get("cogging_torque_Nm", 0))
    stack_len = float(opt_res["optimized_params"].get("stack_length_mm", 0))
    
    # Return structure directly from ga_optimize_full which now contains everything
    return jsonify({
        "optimized_params": opt_res["optimized_params"],
        "ai_judgment": opt_res["optimized_params"]["ai_judgment"],
        "dxf_base64": opt_res["dxf"],
        "flux_map_base64": opt_res["plots"]["flux_map"],
        "efficiency_map_base64": opt_res["plots"]["efficiency_map"],
        "torque_curve_base64": opt_res["plots"]["torque_curve"],
         "mechanical_drawing_base64": opt_res["plots"]["mechanical_drawing"],
         "pyleecan_image_base64": None # Explicitly None
     })


@app.route("/optimize", methods=["POST"])
def optimize():
    d_stator_in = float(request.form.get("d_stator_in_mm", "60"))
    d_stator_out = float(request.form.get("d_stator_out_mm", "120"))
    d_rotor_in = float(request.form.get("d_rotor_in_mm", "20"))
    d_rotor_out = float(request.form.get("d_rotor_out_mm", "58"))
    rotor_type = request.form.get("rotor_type", "IN")
    voltage_v = float(request.form.get("voltage_v", "24"))
    torque_req = float(request.form.get("torque_req_Nm", "5"))
    R_ohm = float(request.form.get("R_ohm", "0.2"))
    Kt = float(request.form.get("Kt_Nm_per_A", "0.05"))
    Ke = float(request.form.get("Ke_Vs_per_rad", "0.05"))
    B = float(request.form.get("B_peak_T", "0.9"))
    min_slot_w = float(request.form.get("min_slot_width_mm", "1.0"))
    generations = int(request.form.get("generations", "6"))
    pop_size = int(request.form.get("pop_size", "24"))
    res = ga_optimize(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, voltage_v, torque_req, R_ohm, Kt, Ke, B, min_slot_w, rotor_type=rotor_type, generations=generations, pop_size=pop_size)
    return jsonify({"candidates": res})

@app.route("/stream_progress")
def stream_progress():
    from design import get_ga_progress
    import time, json
    
    def generate():
        while True:
            progress = get_ga_progress()
            data = json.dumps(progress)
            yield f"data: {data}\n\n"
            if progress["status"] == "completed":
                break
            time.sleep(0.5)
            
    return app.response_class(generate(), mimetype="text/event-stream")

@app.route("/pyleecan_info", methods=["GET"])
def pyleecan_info():
    return jsonify({"available": PYLEECAN_AVAILABLE, "version": PYLEECAN_VERSION, "error": PYLEECAN_ERROR})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
