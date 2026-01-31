import matplotlib.cm
import matplotlib.pyplot as plt
import os
import sys

# Patch matplotlib for pyleecan compatibility
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

# Hack HOME
os.environ["HOME"] = os.getcwd()

try:
    from design import create_pyleecan_machine, pyleecan_plot, ga_optimize, PYLEECAN_AVAIL
    from deap import creator
    print("Imports successful")
    print(f"PYLEECAN_AVAIL: {PYLEECAN_AVAIL}")
    print(f"Creator in design? {'creator' in dir()}")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Test Pyleecan Plot
if PYLEECAN_AVAIL:
    print("Testing Pyleecan Plot...")
    try:
        machine = create_pyleecan_machine(60, 120, 20, 58, 24, 16, "IN")
        if machine:
            print("Machine created")
            b64 = pyleecan_plot(machine)
            if b64:
                print(f"Plot successful, length: {len(b64)}")
            else:
                print("Plot returned None")
        else:
            print("Machine creation failed")
    except Exception as e:
        print(f"Plot test failed: {e}")
        import traceback
        traceback.print_exc()

# Test GA
print("Testing GA...")
try:
    # d_stator_in, d_stator_out, d_rotor_in, d_rotor_out, voltage_v, torque_req, R_ohm, Kt, Ke, B, min_slot_width_mm
    res = ga_optimize(60, 120, 20, 58, 24, 5, 0.2, 0.05, 0.05, 0.9, 1.0, generations=1, pop_size=2)
    print(f"GA result: {len(res)} candidates")
except Exception as e:
    print(f"GA test failed: {e}")
    import traceback
    traceback.print_exc()
