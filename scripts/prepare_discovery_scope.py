"""Fetch the 15 permitted five-region inputs and record reproducible hashes.

No roads/buildings, outside school inventory, target columns or submissions.
Place sources carry their own license/attribution inside the input Parquet.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform

from prepare_screen import download, PREFIX, BASE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_scope"
SUFFIXES = ["overture-pois.parquet", "census-tracts.parquet", "strata-tract-table.parquet"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    manifest = []
    for name in ["screen_manifest.json", "extension_manifest.json"]:
        manifest.extend(json.loads((ROOT / "data" / "metadata" / name).read_text(encoding="utf-8")))
    selected = sorted({item["key"]: item for item in manifest
                       if any(item["key"].endswith("-" + suffix) for suffix in SUFFIXES)}.values(),
                      key=lambda item: item["key"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(download, selected))
    files = [{"path": path.relative_to(ROOT).as_posix(), "url": BASE + item["key"],
              "bytes": path.stat().st_size, "sha256": sha256(path)}
             for item, path in zip(selected, paths)]
    sample = ROOT / "data" / "metadata" / "SampleSubmission.csv"
    files.append({"path": sample.relative_to(ROOT).as_posix(),
                  "url": "https://zindi.world/competitions/bias-bounty-mapping-equity-challenge/data",
                  "bytes": sample.stat().st_size, "sha256": sha256(sample),
                  "note": "Latest platform download; sample target/component values are not used."})
    provenance = {"frozen_on": "2026-10-07", "scope": "Discovery-only five-region school coordinate audit",
                  "overture_release": "2026-08-19.0", "python": platform.python_version(),
                  "dependencies": {name: importlib.metadata.version(name) for name in ["duckdb", "pandas", "numpy", "requests"]},
                  "selected_strata_fields": ["GEOID", "ur_class", "pop_total", "svi_covered", "svi_overall", "tribal_pct", "usfs_covered", "usfs_BP_mean"],
                  "data_attribution": "Humane Intelligence / Zindi / Radiant Earth challenge package; Census, CDC/ATSDR SVI, USFS and Overture Maps. Preserve source_README.md and per-place sources licenses/IDs.",
                  "files": files}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps({"input_files": len(selected), "input_bytes": sum(x["bytes"] for x in selected),
                      "provenance": "runs/discovery_scope/provenance.json"}), flush=True)


if __name__ == "__main__":
    main()
