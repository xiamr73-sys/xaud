import os
import matplotlib
import matplotlib.cm as cm

# Patch
if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

os.environ["HOME"] = "/tmp"

try:
    from pyleecan.Classes.MagnetType10 import MagnetType10
    print("MagnetType10 args:", MagnetType10().__init__.__code__.co_varnames)
except ImportError:
    print("MagnetType10 not found")

try:
    from pyleecan.Classes.MagnetType11 import MagnetType11
    print("MagnetType11 args:", MagnetType11().__init__.__code__.co_varnames)
except ImportError:
    print("MagnetType11 not found")
