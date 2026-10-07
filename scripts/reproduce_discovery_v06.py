"""Reproduce the award core, including selected emergency-address evidence."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def main():
    from reproduce_discovery_v05 import main as reproduce_v05
    reproduce_v05()
    script = ROOT / "scripts/measure_station_address_v06.py"
    sys.argv = [str(script)]
    runpy.run_path(str(script), run_name="__main__")
    print("COMPLETE v0.6: selected registered fire-department identity and independent address-range comparison. No prediction or submission.", flush=True)


if __name__ == "__main__":
    main()
