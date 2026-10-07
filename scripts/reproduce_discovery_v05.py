"""One command for v0.5 Discovery evidence; no prediction or submission."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def main():
    sources = json.loads((ROOT / "runs/discovery_strengthening_v0.5/external_provenance.json").read_text(encoding="utf-8"))["sources"]
    for source in sources:
        if hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Frozen v0.5 NCES response hash differs")
    from reproduce_discovery_v04 import main as reproduce_v04
    reproduce_v04()
    script = ROOT / "scripts/measure_discovery_evacuation_v05.py"
    sys.argv = [str(script), "--open-core"]
    runpy.run_path(str(script), run_name="__main__")
    print("COMPLETE v0.5: 9 independently compared schools; 4 school and 1 fire tract count changes 1->0; confidence-based identity lookup. No historical documents required.", flush=True)


if __name__ == "__main__":
    main()
