import matplotlib.cm
import matplotlib.pyplot as plt
import os
import sys

# Patch matplotlib
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

os.environ["HOME"] = os.getcwd()

try:
    from pyleecan.Classes.MagnetType11 import MagnetType11
    from pyleecan.Classes.MagnetFlat import MagnetFlat
    print(f"MagnetType11 imported: {MagnetType11}")
    print(f"Is subclass? {issubclass(MagnetType11, MagnetFlat)}")
    print(f"MagnetType11 args: {MagnetType11.__init__.__code__.co_varnames}")
except Exception as e:
    print(e)
