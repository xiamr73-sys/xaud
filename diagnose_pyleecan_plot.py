import os
import sys
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm

# Monkey Patch
if not hasattr(cm, "register_cmap"):
    cm.register_cmap = matplotlib.colormaps.register
if not hasattr(cm, "get_cmap"):
    def _get_cmap(name=None, lut=None):
        return matplotlib.colormaps[name] if name else matplotlib.colormaps['viridis']
    cm.get_cmap = _get_cmap

os.environ["HOME"] = "/tmp"

try:
    from pyleecan.Classes.MachineSIPMSM import MachineSIPMSM
    from pyleecan.Classes.LamSlotWind import LamSlotWind
    from pyleecan.Classes.SlotW11 import SlotW11
    from pyleecan.Classes.Winding import Winding
    from pyleecan.Classes.LamSlotMag import LamSlotMag
    from pyleecan.Classes.SlotMFlat import SlotMFlat
    from pyleecan.Classes.MagnetFlat import MagnetFlat
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_machine_creation():
    try:
        # Default params from app
        d_si = 60
        d_so = 120
        d_ri = 20
        d_ro = 58
        slots = 12
        poles = 14
        rotor_type = "IN"

        print("Creating Machine...")
        machine = MachineSIPMSM(name="AI_Motor")
        
        # Stator
        machine.stator = LamSlotWind(
            Rint=d_si/2000, Rext=d_so/2000, 
            is_internal=False, is_stator=True, L1=0.04
        )
        machine.stator.slot = SlotW11(Zs=slots, H0=1e-3, H1=1.5e-3, H2=10e-3, W0=2e-3, W1=4e-3, W2=4e-3)
        machine.stator.winding = Winding(qs=3, p=poles//2) # Winding base
        
        # Rotor
        machine.rotor = LamSlotMag(
            Rint=d_ri/2000, Rext=d_ro/2000,
            is_internal=True, is_stator=False, L1=0.04
        )
        
        # SlotMFlat logic
        machine.rotor.slot = SlotMFlat(Zs=poles, W0=0.8, H0=3e-3)
        mag = MagnetFlat(Wmag=0.01, Hmag=0.003)
        machine.rotor.slot.magnet = [mag]

        print("Machine created. Plotting...")
        
        fig, ax = plt.subplots()
        machine.plot(fig=fig, ax=ax, is_show_fig=False)
        print("Plot successful")
        
    except Exception as e:
        print(f"Error during creation/plot: {e}")
        import traceback
        traceback.print_exc()

test_machine_creation()
