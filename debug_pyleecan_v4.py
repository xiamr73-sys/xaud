import os
import sys
import matplotlib.cm as cm
import matplotlib

if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

os.environ["HOME"] = "/tmp"

try:
    from pyleecan.Classes.MachineSIPMSM import MachineSIPMSM
    print("✔ MachineSIPMSM found")
except ImportError:
    print("❌ MachineSIPMSM NOT found")

try:
    from pyleecan.Classes.SlotMFlat import SlotMFlat
    print("✔ SlotMFlat found")
except ImportError:
    print("❌ SlotMFlat NOT found")

try:
    from pyleecan.Classes.SlotM10 import SlotM10
    print("✔ SlotM10 found")
except ImportError:
    print("❌ SlotM10 NOT found")

