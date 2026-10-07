"""One command for the v0.4 award evidence; never creates a prediction."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_screen import download


def main():
    inputs = json.loads((ROOT / "runs/discovery_scope/provenance.json").read_text(encoding="utf-8"))["files"]
    inputs.append(json.loads((ROOT / "runs/discovery_emergency/oak_cliff_case.json").read_text(encoding="utf-8"))["road_input"])
    for record in inputs:
        path = ROOT / record["path"]
        if not path.exists():
            key = record["url"].removeprefix("https://data.source.coop/")
            download({"key": key, "bytes": record["bytes"]})
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            raise ValueError(f"Frozen input hash differs: {record['path']}")
    external = json.loads((ROOT / "runs/discovery_strengthening_v0.4/external_provenance.json").read_text(encoding="utf-8"))
    for source in external["sources"]:
        if hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Frozen NCES response hash differs")
    db = duckdb.connect()
    db.execute("INSTALL spatial")
    db.execute("LOAD spatial")
    db.close()
    for name in ["scope_school_conflicts.py", "find_coordinate_artifacts.py", "measure_scope_cases.py",
                 "screen_emergency_coordinate_conflicts.py", "measure_oak_cliff_case.py", "measure_discovery_independent_locations.py"]:
        print("REPRODUCE", name, flush=True)
        script = ROOT / "scripts" / name
        sys.argv = [str(script)]
        runpy.run_path(str(script), run_name="__main__")
    print("COMPLETE: discovery measurements and figures regenerated; no prediction or submission created.", flush=True)


if __name__ == "__main__":
    main()
