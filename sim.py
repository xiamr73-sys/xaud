import math
from io import BytesIO
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _to_complex(r, x):
    return complex(r, x)


def _thevenin(V_phase, R1, X1, Xm):
    Z1 = _to_complex(R1, X1)
    Zm = _to_complex(0.0, Xm)
    Zp = (Z1 * Zm) / (Z1 + Zm)
    Vth = V_phase * abs(Zm / (Z1 + Zm))
    Rth = Zp.real
    Xth = Zp.imag
    return Vth, Rth, Xth


def simulate_induction_motor(params):
    f = float(params.get("frequency_hz", 50))
    poles = int(params.get("poles", 4))
    V_line = float(params.get("voltage_v", 380))
    R1 = float(params.get("R1_ohm", 1.2))
    X1 = float(params.get("X1_ohm", 2.5))
    R2 = float(params.get("R2_ohm", 1.0))
    X2 = float(params.get("X2_ohm", 2.0))
    Xm = float(params.get("Xm_ohm", 60.0))
    V_phase = V_line / math.sqrt(3.0)
    Vth, Rth, Xth = _thevenin(V_phase, R1, X1, Xm)
    ws = 2.0 * math.pi * f
    rpm_sync = 120.0 * f / poles
    s = np.linspace(0.001, 0.2, 400)
    R2s = R2 / s
    num = 3.0 * (Vth ** 2) * R2s
    den = ws * ((Rth + R2s) ** 2 + (Xth + X2) ** 2)
    T = num / den
    rpm = (1.0 - s) * rpm_sync
    idx = int(np.argmax(T))
    Tmax = float(T[idx])
    s_max = float(s[idx])
    rpm_at_Tmax = float(rpm[idx])
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.plot(rpm, T, color="#0ea5e9")
    ax.set_xlabel("转速 rpm")
    ax.set_ylabel("电磁转矩 N·m")
    ax.grid(True, alpha=0.3)
    ax.axvline(rpm_at_Tmax, color="#f59e0b", linestyle="--")
    ax.scatter([rpm_at_Tmax], [Tmax], color="#f59e0b")
    buf = BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "rpm": rpm.tolist(),
        "torque": T.tolist(),
        "t_max": Tmax,
        "s_max": s_max,
        "rpm_t_max": rpm_at_Tmax,
        "image_base64": "data:image/png;base64," + img_b64,
        "rpm_sync": rpm_sync,
    }


def simulate_bldc(params):
    V = float(params.get("voltage_v", 24.0))
    V_bus = float(params.get("v_bus_v", V))
    duty = float(params.get("pwm_duty", 1.0))
    R = float(params.get("R_ohm", 0.2))
    Kt = float(params.get("Kt_Nm_per_A", 0.05))
    Ke = float(params.get("Ke_Vs_per_rad", 0.05))
    B = float(params.get("B_Nm_s_per_rad", 0.0005))
    V_eff = min(V, V_bus * max(min(duty, 1.0), 0.0))
    omega0 = V_eff / Ke
    omega = np.linspace(0.0, omega0, 400)
    I = (V_eff - Ke * omega) / R
    T = Kt * I - B * omega
    T = np.maximum(T, 0.0)
    rpm = omega * 60.0 / (2.0 * math.pi)
    T_stall = float(Kt * (V_eff / R))
    rpm_no_load = float(omega0 * 60.0 / (2.0 * math.pi))
    T_mpp = 0.5 * T_stall
    rpm_mpp = 0.5 * rpm_no_load
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    ax.plot(rpm, T, color="#0ea5e9")
    ax.set_xlabel("转速 rpm")
    ax.set_ylabel("电磁转矩 N·m")
    ax.grid(True, alpha=0.3)
    ax.axvline(rpm_mpp, color="#f59e0b", linestyle="--")
    ax.scatter([rpm_mpp], [T_mpp], color="#f59e0b")
    buf = BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "rpm": rpm.tolist(),
        "torque": T.tolist(),
        "t_stall": T_stall,
        "rpm_no_load": rpm_no_load,
        "t_mpp": T_mpp,
        "rpm_mpp": rpm_mpp,
        "image_base64": "data:image/png;base64," + img_b64,
        "v_eff": V_eff,
    }
