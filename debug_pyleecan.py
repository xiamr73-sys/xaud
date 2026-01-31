import os
import sys

# Mock HOME for serverless/restricted envs
os.environ["HOME"] = "/tmp"

try:
    import pyleecan
    print(f"Pyleecan version: {pyleecan.__version__}")
    print(f"Pyleecan path: {pyleecan.__file__}")
except ImportError as e:
    print(f"Failed to import pyleecan: {e}")
except Exception as e:
    print(f"Error importing pyleecan: {e}")

try:
    from pyleecan.Classes.MachineBLDC import MachineBLDC
    print("MachineBLDC imported successfully")
except Exception as e:
    print(f"Failed to import MachineBLDC: {e}")

try:
    from pyleecan.Classes.LamSlotWind import LamSlotWind
    print("LamSlotWind imported successfully")
except Exception as e:
    print(f"Failed to import LamSlotWind: {e}")
    
try:
    from pyleecan.Classes.SlotW11 import SlotW11
    print("SlotW11 imported successfully")
except Exception as e:
    print(f"Failed to import SlotW11: {e}")

