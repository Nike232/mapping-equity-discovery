"""Discovery-only: do the reviewed school-coordinate mechanisms affect emergency labels?

One directed screen of existing allowed challenge files. Candidates are not
verified fire stations, EMS bases, location errors, or scoring targets.
"""
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
import json

import duckdb
import pandas as pd
from find_coordinate_artifacts import tile_zoom, STATE_FIPS, FULL_STATES
from scope_school_conflicts import compact, phone_keys, address_keys, distance_km

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_emergency"
REGIONS = ["northern-ca", "eastern-wa", "maricopa-az", "eastern-ok", "south-central-tx"]
CATEGORIES = ["fire_department", "ambulance_and_ems_services"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect()
    db.execute("LOAD spatial")
    db.execute("SET threads=4")
    sample = pd.read_csv(ROOT / "data/metadata/SampleSubmission.csv", dtype={"GEOID": str}, usecols=["GEOID"])
    db.register("scored", sample)
    by_id = {}
    for region in REGIONS:
        for view, folder, suffix in [("pois", "reference", "overture-pois"), ("tracts", "strata", "census-tracts"), ("strata", "strata", "strata-tract-table")]:
            path = str(ROOT / "data/screening" / folder / region / f"{region}-{suffix}.parquet").replace("'", "''")
            db.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{path}')")
        result = db.execute("""
            SELECT p.id, p.names.primary AS name, p.categories.primary AS category,
                   p.confidence, p.operating_status, p.addresses, p.phones, p.websites, p.sources,
                   ST_X(p.geometry) AS lon, ST_Y(p.geometry) AS lat,
                   t.GEOID, s.ur_class, s.pop_total, s.svi_overall, s.usfs_BP_mean
            FROM pois p JOIN tracts t ON ST_Intersects(p.geometry,t.geometry)
            JOIN scored ON t.GEOID=scored.GEOID
            LEFT JOIN strata s ON t.GEOID=s.GEOID
            WHERE p.categories.primary IN (SELECT unnest(?))
              AND (p.operating_status IS NULL OR p.operating_status <> 'permanently_closed')
            QUALIFY row_number() OVER (PARTITION BY p.id ORDER BY t.GEOID)=1
        """, [CATEGORIES])
        fields = [c[0] for c in result.description]
        for values in result.fetchall():
            r = dict(zip(fields, values), region=region)
            by_id.setdefault(r["id"], r)
    records = list(by_id.values())
    counts = Counter((r["GEOID"],r["category"]) for r in records)
    names = defaultdict(list)
    for i,r in enumerate(records):
        r["tract_same_category_records"] = counts[r["GEOID"],r["category"]]
        r["minimum_tile_zoom"] = tile_zoom(r["lon"],r["lat"])
        r["point_state"] = STATE_FIPS[r["GEOID"][:2]]
        address_states = {(a.get("region") or "").strip().upper() for a in r["addresses"] or []}
        r["address_states"] = sorted({FULL_STATES.get(s,s) for s in address_states if s})
        r["address_state_mismatch"] = bool(r["address_states"] and r["point_state"] not in r["address_states"])
        if compact(r["name"]):
            names[r["category"],compact(r["name"])].append(i)
    pairs = []
    for members in names.values():
        for i,j in combinations(members,2):
            a,b = records[i],records[j]
            phone = sorted(phone_keys(a["phones"]) & phone_keys(b["phones"]))
            address = sorted(address_keys(a["addresses"]) & address_keys(b["addresses"]))
            if not (phone or address):
                continue
            km = distance_km(a,b)
            if km >= 5:
                pairs.append({"a":a,"b":b,"distance_km":round(km,3),"shared_phone":phone,"shared_address":address})
    flags = [r for r in records if r["minimum_tile_zoom"] is not None or r["address_state_mismatch"]]
    flags.sort(key=lambda r:(r["tract_same_category_records"],r["ur_class"]!="Rural",-(r["confidence"] or 0)))
    pairs.sort(key=lambda r:(min(r["a"]["tract_same_category_records"],r["b"]["tract_same_category_records"]),-r["distance_km"]))
    for name,values in [("coordinate_candidates",flags),("identity_candidates",pairs)]:
        (OUT / f"{name}.json").write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding="utf-8")
    summary = {"question":"Can the school-coordinate finding be extended to direct emergency-service labels?",
               "categories":CATEGORIES,"unique_records":len(records),"category_counts":dict(Counter(r["category"] for r in records)),
               "grid_flags":sum(r["minimum_tile_zoom"] is not None for r in records),
               "address_state_mismatch_flags":sum(r["address_state_mismatch"] for r in records),
               "identity_pairs_at_least_5km":len(pairs),
               "status":"Directed candidate screen only. No external data, targets, predictions, or confirmed errors."}
    (OUT / "summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary),flush=True)
    for r in flags:
        print("FLAG",json.dumps(r,ensure_ascii=False),flush=True)
    for r in pairs[:8]:
        print("PAIR",json.dumps(r,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
