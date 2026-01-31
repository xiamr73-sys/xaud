
# Motor Simulation Web App Context

## File: templates/index.html
```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>电机参数仿真</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <div class="container">
    <h1>全自动优化设计</h1>
    <form id="auto-design-form">
      <div class="grid">
        <label>转子类型
          <select name="rotor_type">
            <option value="IN">内转子</option>
            <option value="OUT">外转子</option>
          </select>
        </label>
        <label>定子内径 mm
          <input name="d_stator_in_mm" type="number" step="0.1" value="60">
        </label>
        <label>定子外径 mm
          <input name="d_stator_out_mm" type="number" step="0.1" value="120">
        </label>
        <label>转子内径 mm
          <input name="d_rotor_in_mm" type="number" step="0.1" value="20">
        </label>
        <label>转子外径 mm
          <input name="d_rotor_out_mm" type="number" step="0.1" value="58">
        </label>
        <label>额定电压 V
          <input name="voltage_v" type="number" step="0.1" value="24">
        </label>
        <label>最大电流 A
          <input name="max_current_a" type="number" step="0.1" value="30">
        </label>
        <label>扭矩要求 N·m
          <input name="torque_req_Nm" type="number" step="0.1" value="5">
        </label>
        <label>设计转速 rpm
          <input name="design_speed_rpm" type="number" step="1" value="3000">
        </label>
        <label>遗传算法迭代次数
          <input name="generations" type="number" step="1" value="15">
        </label>
        <label>齿槽转矩要求 N·m (Max)
          <input name="cogging_req_Nm" type="number" step="0.01" value="0.05">
        </label>
        <label>叠厚 mm
          <input name="stack_length_mm" type="number" step="1" value="40">
        </label>
      </div>
      <button type="submit">开始全自动设计与绘图</button>
    </form>
    
    <div id="auto-result" class="result hidden">
      <h3>AI 设计评估</h3>
      <div class="cards" style="background: #f0fdf4; border: 1px solid #bbf7d0;">
        <div class="card" style="flex: 2"><div class="k">综合评价</div><div class="v" id="ai_verdict" style="font-weight:bold; color:#166534">—</div></div>
        <div class="card" style="flex: 1"><div class="k">评分</div><div class="v" id="ai_score">—</div></div>
      </div>
      <div id="ai_details" style="margin: 10px 0; padding: 10px; color: #166534; font-size: 0.9em;"></div>

      <h3>优化结果参数</h3>
      <div class="cards">
        <div class="card"><div class="k">极槽配合</div><div class="v" id="auto_slots_poles">—</div></div>
        <div class="card"><div class="k">每槽匝数</div><div class="v" id="auto_turns">—</div></div>
        <div class="card"><div class="k">磁钢厚度</div><div class="v" id="auto_mag_th">—</div></div>
        <div class="card"><div class="k">相电阻 R</div><div class="v" id="auto_R">—</div></div>
        <div class="card"><div class="k">Kt / Ke</div><div class="v" id="auto_KtKe">—</div></div>
        <div class="card"><div class="k">额定效率</div><div class="v" id="auto_eff">—</div></div>
        <div class="card"><div class="k">齿槽转矩 (est)</div><div class="v" id="auto_tcog">—</div></div>
        <div class="card"><div class="k">定子轭厚</div><div class="v" id="auto_sy">—</div></div>
        <div class="card"><div class="k">转子轭厚</div><div class="v" id="auto_ry">—</div></div>
      </div>
      
      <h3>设计图纸与特性曲线</h3>
      <div class="grid-2">
        <div>
            <h4>Pyleecan 几何模型</h4>
            <img id="auto_pyleecan_img" style="width:100%">
        </div>
        <div>
            <h4>磁密云图 (估算)</h4>
            <img id="auto_flux_map" style="width:100%">
        </div>
        <div>
            <h4>效率 MAP</h4>
            <img id="auto_eff_map" style="width:100%">
        </div>
        <div>
            <h4>扭矩-转速特性</h4>
            <img id="auto_torque_curve" style="width:100%">
        </div>
      </div>
    </div>
  </div>
  <script>
    const autoForm = document.getElementById('auto-design-form');
    const autoResult = document.getElementById('auto-result');
    autoForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = autoForm.querySelector('button');
        const oldText = btn.textContent;
        btn.textContent = '优化计算中，请稍候...';
        btn.disabled = true;
        
        try {
            const fd = new FormData(autoForm);
            const r = await fetch('/auto_design', { method: 'POST', body: fd });
            const data = await r.json();
            
            const p = data.optimized_params;
            document.getElementById('auto_slots_poles').textContent = p.slots + '槽 / ' + p.poles + '极';
            document.getElementById('auto_turns').textContent = p.turns_per_slot;
            document.getElementById('auto_mag_th').textContent = p.magnet_thickness_mm.toFixed(2) + ' mm';
            document.getElementById('auto_R').textContent = p.R_ohm.toFixed(4) + ' Ω';
            document.getElementById('auto_KtKe').textContent = p.Kt.toFixed(3) + ' / ' + p.Ke.toFixed(3);
            document.getElementById('auto_eff').textContent = (p.efficiency * 100).toFixed(1) + '%';
            document.getElementById('auto_tcog').textContent = (p.cogging_torque_Nm || 0).toFixed(4) + ' Nm';
            
            // AI Judgment
            const ai = data.ai_judgment;
            if (ai) {
                document.getElementById('ai_verdict').textContent = ai.verdict;
                document.getElementById('ai_score').textContent = ai.score;
                document.getElementById('ai_details').innerHTML = ai.details.map(d => `<div>• ${d}</div>`).join('');
            }
            
            document.getElementById('auto_pyleecan_img').src = data.pyleecan_image_base64 || '';
            document.getElementById('auto_flux_map').src = data.flux_map_base64 || '';
            document.getElementById('auto_eff_map').src = data.efficiency_map_base64 || '';
            document.getElementById('auto_torque_curve').src = data.torque_curve_base64 || '';
            
            autoResult.classList.remove('hidden');
        } catch (err) {
            alert('优化失败: ' + err);
        } finally {
            btn.textContent = oldText;
            btn.disabled = false;
        }
    });
  </script>
</body>
</html>
```

## File: static/style.css
```css
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#0b1220;color:#e5e7eb}h1{font-size:20px;margin:0 0 16px}h2{font-size:18px;margin:24px 0 8px}.container{max-width:960px;margin:0 auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:12px}label{display:flex;flex-direction:column;font-size:12px;color:#9ca3af}input,select{margin-top:6px;border:1px solid #1f2937;background:#0f172a;color:#e5e7eb;padding:8px;border-radius:6px}button{background:#0ea5e9;color:#fff;border:0;padding:10px 14px;border-radius:8px;cursor:pointer}button:hover{background:#0284c7}.result.hidden{display:none}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0}.card{background:#0f172a;border:1px solid #1f2937;border-radius:8px;padding:12px}.card .k{font-size:12px;color:#9ca3af}.card .v{font-size:16px;margin-top:6px}img#plot{width:100%;border:1px solid #1f2937;border-radius:8px;background:#0f172a}
```

## File: app.py
```python
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
    slots = int(opt_res["slots"])
    poles = int(opt_res["poles"])
    turns = int(opt_res["turns_per_slot"])
    mag_th = float(opt_res["magnet_thickness_mm"])
    R_ohm = float(opt_res["R_ohm"])
    Kt = float(opt_res["Kt"])
    Ke = float(opt_res["Ke"])
    eff = float(opt_res["efficiency"])
    tcog_val = float(opt_res.get("cogging_torque_Nm", 0))
    stack_len = float(opt_res.get("stack_length_mm", 0))
    sy_mm = float(opt_res.get("stator_yoke_mm", 0))
    ry_mm = float(opt_res.get("rotor_yoke_mm", 0))
    
    # AI Judgment
    judgment = judge_design_quality(opt_res, voltage_v, torque_req, speed_req, max_current, d_stator_out)
    
    # 4. Generate Plots
    # DXF
    dxf_b64 = generate_dxf(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, slots, poles, rotor_type=rotor_type)
    
    # Flux Map (Analytical)
    # Estimate Peak Flux Density B_peak from magnet thickness
    # B_peak approx B_g
    g = (d_stator_in - d_rotor_out)/2.0 if rotor_type=="IN" else (d_rotor_in - d_stator_out)/2.0
    B_peak = 1.2 * mag_th / (mag_th + abs(g)) # approx
    flux_b64 = flux_map(d_stator_in, d_rotor_out, poles, B_peak, rotor_type=rotor_type, d_stator_out=d_stator_out, d_rotor_in=d_rotor_in)
    
    # Pyleecan Geometry
    machine = create_pyleecan_machine(d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, slots, poles, rotor_type)
    # Note: Pyleecan machine creation currently doesn't support setting magnet thickness or turns easily via the simple helper
    # But it gives the visual. Ideally we should update the helper to take mag_th, but let's stick to default visual for now or update it?
    # The user wants "corresponding mechanical drawing".
    # Let's try to update create_pyleecan_machine slightly if possible, but the geometry helper is fixed.
    # We will just show the geometry with correct slots/poles.
    pyleecan_img_b64 = pyleecan_plot(machine)
    
    # Efficiency Map
    eff_map_b64 = generate_efficiency_map(voltage_v, R_ohm, Kt, Ke, torque_req*1.5, speed_req*1.2)
    
    # Torque Curve
    torque_curve_b64 = generate_torque_curve(voltage_v, R_ohm, Kt, Ke, max_current, speed_req*1.5)
    
    return jsonify({
        "optimized_params": {
            "slots": slots,
            "poles": poles,
            "turns_per_slot": turns,
            "magnet_thickness_mm": mag_th,
            "R_ohm": R_ohm,
            "Kt": Kt,
            "Ke": Ke,
            "efficiency": eff,
            "cogging_torque_Nm": tcog_val,
            "stack_length_mm": stack_len
        },
        "ai_judgment": judgment,
        "dxf_base64": dxf_b64,
        "flux_map_base64": flux_b64,
        "efficiency_map_base64": eff_map_b64,
        "torque_curve_base64": torque_curve_b64,
        "pyleecan_image_base64": pyleecan_img_b64
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


@app.route("/pyleecan_info", methods=["GET"])
def pyleecan_info():
    return jsonify({"available": PYLEECAN_AVAILABLE, "version": PYLEECAN_VERSION, "error": PYLEECAN_ERROR})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
```
