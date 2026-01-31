import os
import sys
import matplotlib
import matplotlib.cm as cm

# 1. Monkey Patch matplotlib for Pyleecan compatibility
if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

# Mock HOME
os.environ["HOME"] = "/tmp"

print("Attempting to import pyleecan with patches...")
try:
    import pyleecan
    print(f"Pyleecan version: {pyleecan.__version__}")
except ImportError as e:
    print(f"Failed to import pyleecan: {e}")
    sys.exit(1)

# Check classes
classes_to_check = [
    "MachineBLDC", "LamSlotWind", "SlotW11", "WindingCW2L", 
    "LamSlotMag", "SlotM11", "Material", "Shaft", "Frame"
]

for cls_name in classes_to_check:
    try:
        exec(f"from pyleecan.Classes.{cls_name} import {cls_name}")
        print(f"✔ {cls_name} imported")
    except ImportError:
        print(f"❌ {cls_name} NOT found")
    except Exception as e:
        print(f"❌ {cls_name} error: {e}")

