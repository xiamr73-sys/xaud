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
    from pyleecan.Classes.MachineSIPMSM import MachineSIPMSM
    import matplotlib.pyplot as plt
    machine = MachineSIPMSM()
    fig, ax = plt.subplots()
    print("Calling plot(fig=fig, is_show=False)...")
    machine.plot(fig=fig, is_show=False)
    print("Plot called.")
    # Check if axes have content
    print(f"Axes children: {len(ax.get_children())}")
except Exception as e:
    print(e)
