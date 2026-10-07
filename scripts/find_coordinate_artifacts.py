"""Discovery-only grid-coordinate and address-state inconsistency screen.

Grid membership/state mismatch are candidate flags, not automatic deletions.
The integer Web Mercator tile grid is a mathematical property of coordinates;
no claim about the upstream process that produced those coordinates is made.
"""
from pathlib import Path
from collections import Counter
import math
import json
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_scope"
STATE_FIPS = {"04": "AZ", "06": "CA", "35": "NM", "40": "OK", "48": "TX", "53": "WA"}
FULL_STATES = {"ARIZONA": "AZ", "CALIFORNIA": "CA", "NEW MEXICO": "NM", "OKLAHOMA": "OK", "TEXAS": "TX", "WASHINGTON": "WA", "MISSOURI": "MO", "COLORADO": "CO", "KANSAS": "KS", "MISSISSIPPI": "MS"}


def tile_zoom(lon, lat):
    x = (lon + 180) / 360
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2
    for z in range(1, 19):
        xx, yy = x * 2**z, y * 2**z
        if abs(xx - round(xx)) < 1e-6 and abs(yy - round(yy)) < 1e-6:
            return z
    return None


def main():
    inventory = pd.read_csv(OUT / "school_inventory.csv", dtype={"GEOID": str})
    db = duckdb.connect()
    rows = []
    for region, sub in inventory.groupby("region"):
        path = str(ROOT / "data" / "screening" / "reference" / region / f"{region}-overture-pois.parquet")
        db.register("selected", sub[["id"]])
        result = db.execute("SELECT p.id, p.addresses, p.websites, p.phones, p.sources FROM read_parquet(?) p JOIN selected s USING(id)", [path])
        fields = [x[0] for x in result.description]
        context = sub.set_index("id").to_dict("index")
        for raw in result.fetchall():
            extra = dict(zip(fields, raw))
            r = dict(context[extra["id"]], **extra)
            r["minimum_tile_zoom"] = tile_zoom(r["lon"], r["lat"])
            r["point_state"] = STATE_FIPS[r["GEOID"][:2]]
            address_states = set()
            for a in r["addresses"] or []:
                state = (a.get("region") or "").strip().upper()
                if state:
                    address_states.add(FULL_STATES.get(state, state))
            r["address_states"] = sorted(address_states)
            r["address_state_mismatch"] = bool(address_states and r["point_state"] not in address_states)
            rows.append(r)
    flagged = [r for r in rows if r["minimum_tile_zoom"] is not None or r["address_state_mismatch"]]
    (OUT / "coordinate_flags.json").write_text(json.dumps(flagged, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    simple = [{k:v for k,v in r.items() if k not in {"sources", "addresses", "websites", "phones"}} for r in flagged]
    pd.DataFrame(simple).to_csv(OUT / "coordinate_flags.csv", index=False)
    tile = [r for r in rows if r["minimum_tile_zoom"] is not None]
    pd.DataFrame([{k:v for k,v in r.items() if k not in {"sources", "addresses", "websites", "phones"}} for r in tile]).to_csv(OUT / "tile_grid_candidates.csv", index=False)
    distribution = []
    for source in ["all", "meta"]:
        for urbanity in ["Rural", "Urban", "Unknown"]:
            subset = [r for r in rows
                      if (r["ur_class"] if r["ur_class"] in {"Rural", "Urban"} else "Unknown") == urbanity
                      and (source == "all" or (r["sources"] or [{}])[0].get("dataset") == source)]
            n_grid = sum(r["minimum_tile_zoom"] is not None for r in subset)
            distribution.append({"first_source": source, "ur_class": urbanity,
                                 "records": len(subset), "grid_flags": n_grid,
                                 "flag_rate": n_grid / len(subset) if subset else None})
    summary = {"school_records": len(rows), "rural_records": sum(r["ur_class"] == "Rural" for r in rows),
        "tile_grid_records": len(tile), "tile_grid_rural_records": sum(r["ur_class"] == "Rural" for r in tile),
        "tile_grid_high_confidence_records": sum(r["confidence"] >= .9 for r in tile),
        "tile_grid_source_counts": dict(Counter((r["sources"] or [{}])[0].get("dataset") for r in tile)),
        "address_state_mismatch_records": sum(r["address_state_mismatch"] for r in rows),
        "address_state_mismatch_high_confidence_records": sum(r["address_state_mismatch"] and r["confidence"] >= .9 for r in rows),
        "tile_zoom_limit": 18, "tile_integer_tolerance": 1e-6,
        "distribution": distribution,
        "tile_grid_by_region": dict(Counter(r["region"] for r in tile)),
        "interpretation": "Observed-coordinate candidates; no inferred upstream mechanism, error labels, or population impact."}
    (OUT / "coordinate_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    for r in flagged:
        if r["address_state_mismatch"] and r["confidence"] >= .9:
            print(json.dumps({k:r[k] for k in ["name", "id", "region", "confidence", "point_state", "address_states", "minimum_tile_zoom", "tract_school_records"]}), flush=True)


if __name__ == "__main__":
    main()
