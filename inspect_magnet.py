import os
import matplotlib
import matplotlib.cm as cm

if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

os.environ["HOME"] = "/tmp"

try:
    from pyleecan.Classes.MagnetFlat import MagnetFlat
    print("Init args:", MagnetFlat().__init__.__code__.co_varnames)
except Exception as e:
    print(f"Error: {e}")
