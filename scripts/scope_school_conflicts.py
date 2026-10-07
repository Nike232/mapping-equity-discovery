"""Five-region discovery screen: school identity conflicts and tract count impact.

No targets, outside facility inventories, predictions or submission interface.
Candidate identity matches require human review; multi-campus and moves exist.
"""
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
from urllib.parse import urlsplit
import math
import re
import json

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_scope"
OUT.mkdir(parents=True, exist_ok=True)
REGIONS = ["northern-ca", "eastern-wa", "maricopa-az", "eastern-ok", "south-central-tx"]
SCHOOLS = ["elementary_school", "middle_school", "high_school", "school", "private_school", "public_school"]


def compact(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def address_keys(addresses):
    keys = set()
    for a in addresses or []:
        street = (a.get("freeform") or "").lower()
        postcode = (a.get("postcode") or "")[:5]
        for long, short in [("street", "st"), ("road", "rd"), ("avenue", "ave"), ("drive", "dr"), ("boulevard", "blvd"), ("lane", "ln")]:
            street = re.sub(rf"\b{long}\b", short, street)
        street = compact(street)
        if street and postcode:
            keys.add(street + "|" + postcode)
    return keys


def phone_keys(phones):
    return {re.sub(r"\D", "", p)[-10:] for p in phones or [] if len(re.sub(r"\D", "", p)) >= 10}


def web_keys(websites):
    result = set()
    for w in websites or []:
        if not w.strip():
            continue
        u = urlsplit(w if "://" in w else "https://" + w)
        result.add(u.netloc.lower().removeprefix("www.") + u.path.rstrip("/").lower())
    return result


def name_tokens(name):
    return set(re.findall(r"[a-z0-9]+", name.lower())) - {"school", "schools", "high", "middle", "elementary", "the", "of", "public"}


def distance_km(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b["lon"]-a["lon"])/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(h, 1)))


def main():
    db = duckdb.connect()
    db.execute("LOAD spatial")
    db.execute("SET threads=4")
    db.execute("SET memory_limit='4GB'")
    sample = pd.read_csv(ROOT / "data" / "metadata" / "SampleSubmission.csv", dtype={"GEOID": str})
    db.register("scored", sample[["GEOID"]])
    records = []
    for region in REGIONS:
        for view, folder, suffix in [("pois", "reference", "overture-pois"), ("tracts", "strata", "census-tracts"), ("strata", "strata", "strata-tract-table")]:
            path = str(ROOT / "data" / "screening" / folder / region / f"{region}-{suffix}.parquet").replace("'", "''")
            db.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{path}')")
        result = db.execute("""
            SELECT p.id, p.names.primary AS name, p.categories.primary AS category,
                p.confidence, p.operating_status, p.addresses, p.phones, p.websites, p.sources,
                ST_X(p.geometry) AS lon, ST_Y(p.geometry) AS lat,
                t.GEOID, s.ur_class, s.pop_total, s.svi_covered, s.svi_overall,
                s.tribal_pct, s.usfs_covered, s.usfs_BP_mean
            FROM pois p JOIN tracts t ON ST_Intersects(p.geometry, t.geometry)
            JOIN scored scored ON t.GEOID=scored.GEOID
            LEFT JOIN strata s ON t.GEOID=s.GEOID
            WHERE p.categories.primary IN (SELECT unnest(?))
              AND (p.operating_status IS NULL OR p.operating_status <> 'permanently_closed')
            QUALIFY row_number() OVER (PARTITION BY p.id ORDER BY t.GEOID)=1
        """, [SCHOOLS])
        fields = [x[0] for x in result.description]
        region_rows = [dict(zip(fields, row), region=region) for row in result.fetchall()]
        records.extend(region_rows)
        print("REGION", region, len(region_rows), flush=True)
    counts = Counter(r["GEOID"] for r in records)
    groups = defaultdict(list)
    for i, r in enumerate(records):
        r["tract_school_records"] = counts[r["GEOID"]]
        r["name_key"] = compact(r["name"])
        r["address_keys"] = sorted(address_keys(r["addresses"]))
        r["phone_keys"] = sorted(phone_keys(r["phones"]))
        r["web_keys"] = sorted(web_keys(r["websites"]))
        if r["name_key"]:
            groups[("name", r["name_key"])].append(i)
        for key in r["web_keys"]:
            groups[("web", key)].append(i)
    pairs = set()
    for members in groups.values():
        pairs.update(combinations(members, 2))
    candidates = []
    for i, j in sorted(pairs):
        a, b = records[i], records[j]
        separation = distance_km(a, b)
        if separation < 5:
            continue
        same_name = a["name_key"] == b["name_key"]
        shared_address = sorted(set(a["address_keys"]) & set(b["address_keys"]))
        shared_phone = sorted(set(a["phone_keys"]) & set(b["phone_keys"]))
        shared_web = sorted(set(a["web_keys"]) & set(b["web_keys"]))
        ta, tb = name_tokens(a["name"]), name_tokens(b["name"])
        similarity = len(ta & tb) / len(ta | tb) if ta | tb else 0
        if same_name and shared_address:
            tier = "same_name_street_postcode"
        elif same_name and shared_phone:
            tier = "same_name_phone"
        elif shared_web and similarity >= 0.6:
            tier = "similar_name_website_review"
        else:
            continue
        candidates.append({"a": a, "b": b, "distance_km": round(separation, 3),
            "tier": tier, "shared_address": shared_address, "shared_phone": shared_phone, "shared_web": shared_web})
    candidates.sort(key=lambda c: (min(c["a"]["tract_school_records"], c["b"]["tract_school_records"]),
                                  c["tier"] != "same_name_street_postcode", -c["distance_km"]))
    (OUT / "identity_candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    # Flat inventory contains only permitted fields; no reference-derived strata.
    inventory = pd.DataFrame([{k:v for k,v in r.items() if k not in {"sources", "addresses", "phones", "websites", "address_keys", "phone_keys", "web_keys"}} for r in records])
    inventory.to_csv(OUT / "school_inventory.csv", index=False)
    flattened = []
    for c in candidates:
        row = {k:v for k,v in c.items() if k not in {"a", "b"}}
        for side in ["a", "b"]:
            row.update({f"{side}_{k}": c[side][k] for k in ["id", "name", "region", "GEOID", "lon", "lat", "confidence", "operating_status", "ur_class", "svi_overall", "tract_school_records"]})
        flattened.append(row)
    pd.DataFrame(flattened).to_csv(OUT / "identity_candidates.csv", index=False)
    involved = {r["id"] for c in candidates for r in [c["a"], c["b"]]}
    summary = {"school_records": len(records), "scored_tracts": len(sample),
        "by_region": dict(Counter(r["region"] for r in records)), "candidate_pairs": len(candidates),
        "candidate_tiers": dict(Counter(c["tier"] for c in candidates)),
        "candidate_records": len(involved),
        "warning": "Candidates are not confirmed errors; names, websites and phones can be shared across valid campuses."}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary), flush=True)
    for c in candidates[:24]:
        print(json.dumps({"tier": c["tier"], "km": c["distance_km"],
            "a": {k:c["a"][k] for k in ["name", "id", "region", "confidence", "addresses", "tract_school_records", "ur_class"]},
            "b": {k:c["b"][k] for k in ["name", "id", "region", "confidence", "addresses", "tract_school_records", "ur_class"]}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
