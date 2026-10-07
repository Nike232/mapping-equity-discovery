"""One zero-gap prior baseline. Creates files; never uploads or submits.

Read only GEOID from the latest challenge sample. Its placeholder scores,
component values, external discovery evidence and withdrawn layers are unused.
Zero is an explicit lower-bound hypothesis, not a fitted/validated estimate.
"""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "metadata" / "SampleSubmission.csv"
OUT = ROOT / "runs" / "entry_v1"
OUTPUT = OUT / "mapping_equity_v1_zero_prior.csv"


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        geoids = [row["GEOID"] for row in csv.DictReader(stream)]
    if len(geoids) != 9794 or len(set(geoids)) != len(geoids):
        raise ValueError("Latest 9,794 unique GEOID universe required")
    if not all(len(g) == 11 and g.isdecimal() for g in geoids):
        raise ValueError("GEOID must remain an 11-digit string")
    OUT.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["GEOID", "coverage_gap_score"])
        writer.writerows((g, "0.0") for g in geoids)
    with OUTPUT.open(encoding="utf-8", newline="") as stream:
        result = list(csv.DictReader(stream))
    output_ids = [r["GEOID"] for r in result]
    scores = [float(r["coverage_gap_score"]) for r in result]
    if output_ids != geoids or not all(math.isfinite(x) and 0 <= x <= 1 for x in scores):
        raise ValueError("Submission schema/universe/range check failed")
    manifest = {
        "version": "v1_zero_prior", "prepared_on": "2026-10-07",
        "competition": "bias-bounty-mapping-equity-challenge", "rows": len(result),
        "unique_geoids": len(set(output_ids)), "missing_ids": 0, "extra_ids": 0,
        "columns": ["GEOID", "coverage_gap_score"], "prediction": "constant 0.0",
        "score_min": min(scores), "score_max": max(scores), "non_finite": 0,
        "input": SOURCE.relative_to(ROOT).as_posix(),
        "input_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "output_bytes": OUTPUT.stat().st_size,
        "prediction_inputs": "GEOID only; no sample score/component or external data read",
        "rationale": "Explicit zero-gap prior to establish the first valid official RMSE; not a learned model, not a claim that actual gaps are zero",
        "change_from_existing_rejected_upload": "Replaces nonmatching 1,030 generic IDs and TargetF1/TargetRAUC with this competition's complete tract universe and target schema",
        "validation": "Schema, exact ordered ID coverage, uniqueness, finite [0,1] outputs only; no local target labels or RMSE",
        "expected_benefit": "First valid official score and entry ID; performance improvement and prize eligibility of the discovery writeup are not established",
        "limitations": "Uncalibrated constant prediction ignores tract variation. Discovery v0.2 remains separate and its writeup submission mechanism is unresolved.",
        "submission_authorization": "User explicitly requested 提交一版 on 2026-10-07; one manual browser submission only",
        "status": "prepared; no upload performed by this script"
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["version", "rows", "missing_ids", "extra_ids", "output", "output_sha256", "output_bytes"]}), flush=True)


if __name__ == "__main__":
    main()
