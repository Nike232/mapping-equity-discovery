"""Quantify manually corroborated identities; does not infer target scores.

Point-pair separation is not surveyed positional error. Counts and nearest
labels are sensitivity calculations on this bundle, not true service access.
"""
from pathlib import Path
import json
import math

import duckdb
import pandas as pd

from find_coordinate_artifacts import tile_zoom

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_scope"
CASES = [
    {"label": "Moe & Gene Johnson High School", "suspect": "2b483ffc-45d6-41a3-9e15-252141a28c15",
     "comparators": ["c19efedd-c59a-4d99-b92c-1d6af4d8fdf3"],
     "identity_evidence": "same school identity and school phone; comparator is a school-associated FFA record at the official campus street address, not an independently surveyed campus point",
     "official_url": "https://www.hayscisd.net/o/jhs",
     "official_fact": "4260 FM 967, Buda TX 78610; 512-268-8512",
     "caveat": "Suspect street text differs from official current address; comparator is a school-associated record."},
    {"label": "Seagoville Middle School", "suspect": "cc1ded36-062a-4468-a18e-695aa1bb52f4",
     "comparators": ["94000e77-d576-49fc-94fd-55e2f403010c", "d11dcf4f-7028-4d14-8de7-ec3d583db8c5"],
     "identity_evidence": "same name, street, ZIP and school phone; two campus-area comparator records from Meta and BrightQuery",
     "official_url": "https://seagovillemiddle.dallasisd.org/our-school/school-contact-information",
     "official_fact": "950 Woody Road, Dallas TX 75253; 972-892-7100",
     "caveat": "Two comparator points differ by hundreds of metres; none is treated as survey truth."},
    {"label": "Meadows Elementary School", "suspect": "d6cab405-9f77-4901-87cb-5fb928dd0a80",
     "comparators": ["e3de1695-c160-42d0-8b1a-7aec399ad959"],
     "identity_evidence": "same name, street, ZIP and school phone",
     "official_url": "https://mes.killeenisd.org/o/meadows",
     "official_fact": "423 27th St, Fort Cavazos/Fort Hood TX 76544; 254-336-1870",
     "caveat": "Point tract has population 35 and no SVI value; do not lead population impact with this military-area example."},
    {"label": "Happy Camp High School", "suspect": "61281033-1be5-4ac5-8f3e-5a410a791fff",
     "comparators": ["249bb167-b742-4eb0-a38d-96e6476f84c6"],
     "identity_evidence": "same name, phone, locality and ZIP; similar street address",
     "official_url": "https://www.happycamp-highschool.com/o/hchs/page/contact",
     "official_fact": "234 Indian Creek Rd, Happy Camp CA 96039; 530-493-2697",
     "caveat": "Nearby school-labelled records include an apparel-store name; nearest label is not validated service access."},
    {"label": "McCloud High School", "suspect": "c47dc5d8-1fd4-4221-be96-22dc15e07be9",
     "comparators": ["2d59cc6b-6a64-4a5e-881a-0b125f312b24"],
     "identity_evidence": "same name, address and official website; district and campus phone fields differ",
     "official_url": "https://www.mccloud-highschool.com/",
     "official_fact": "133 Campus Way, McCloud CA 96057; district phone 530-926-3006",
     "caveat": "Not detected by the zoom-18 grid flag; detector is incomplete."},
    {"label": "Horse Heaven Hills Middle School", "suspect": "3724a7c0-8fcd-47ba-9aab-65d61b89a5e7",
     "comparators": ["85ae45a2-b961-43ab-8964-83a6ad0fceb6"],
     "identity_evidence": "same school-specific official website; abbreviated suspect name",
     "official_url": "https://horseheavenhills.ksd.org/contact-us",
     "official_fact": "3500 S Vancouver St, Kennewick WA 99337; 509-222-6800",
     "caveat": "Suspect has no street address or phone; website match is the principal identity evidence."},
    {"label": "Piner Middle School", "suspect": "7637046a-2843-45ca-9e34-20f7f7778081",
     "comparators": ["e14a283c-ec81-4aa8-b338-d0b86977a01c"],
     "identity_evidence": "same exact name and school phone; point is in Oklahoma, while address and official school are in Sherman Texas",
     "official_url": "https://www.shermanisd.net/schools/middle-schools",
     "official_fact": "402 W Pecan, Sherman TX; 903-891-6470",
     "caveat": "Suspect street is malformed and its ZIP differs from comparator; official district page also differs on ZIP, so phone/name/state are used."},
    {"label": "U.S. Grant High School", "suspect": "a233c100-53ac-4a63-9d3f-5c236c1617c1",
     "comparators": ["30a3fba5-c733-4019-bdd3-ac0272ed4bfc"],
     "identity_evidence": "same school phone; suspect links official school-specific URL; comparator is an alumni/memorial record with the official school street address",
     "official_url": "https://grant.okcps.org/our-school/general-information/contact-us",
     "official_fact": "5016 S Pennsylvania Ave, Oklahoma City OK 73119; 405-587-2200",
     "caveat": "Comparator is an alumni/memorial record, not independently verified campus geometry; suspect has no address."},
    {"label": "Southern Boone School District", "suspect": "fdca9dbd-4348-492d-8c21-d461c767e760",
     "comparators": [],
     "identity_evidence": "name, official website, street address and school phone identify Missouri district; provided point is in Oklahoma",
     "official_url": "https://www.sbschools.us/",
     "official_fact": "5275 West Red Tail Drive, Ashland MO 65010; 573-657-2147",
     "caveat": "District office rather than campus; no counterpart in package. No separation to an external ground-truth coordinate is calculated."},
]
NCES_IDS = {
    "Moe & Gene Johnson High School": "480001013567",
    "Seagoville Middle School": "481623001353",
    "Meadows Elementary School": "482566002874",
    "Happy Camp High School": "063694006277",
    "McCloud High School": "063694006278",
    "Horse Heaven Hills Middle School": "530393000750",
    "Piner Middle School": "484008004549",
    "U.S. Grant High School": "402277001139",
    "Southern Boone School District": "2928560",
}


def great_circle_km(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(h, 1)))


def main():
    inventory = pd.read_csv(OUT / "school_inventory.csv", dtype={"GEOID": str})
    indexed = inventory.set_index("id")
    nces_school_response = json.loads((OUT / "address_corroboration" / "nces_layer_0_addresses.json").read_text(encoding="utf-8"))
    nces_district_response = json.loads((OUT / "address_corroboration" / "nces_layer_6_addresses.json").read_text(encoding="utf-8"))
    nces = {}
    for item in nces_school_response["features"]:
        attributes = {k.split(".")[-1]: v for k, v in item["attributes"].items()}
        nces[attributes["NCESSCH"]] = attributes
    for item in nces_district_response["features"]:
        nces[item["attributes"]["LEAID"]] = item["attributes"]
    suspects = {c["suspect"] for c in CASES}
    all_ids = sorted(suspects | {x for c in CASES for x in c["comparators"]})
    db = duckdb.connect()
    raw_records = {}
    for region in inventory.region.unique():
        path = str(ROOT / "data" / "screening" / "reference" / region / f"{region}-overture-pois.parquet")
        result = db.execute("SELECT id, addresses, websites, phones, sources FROM read_parquet(?) WHERE id IN (SELECT unnest(?))", [path, all_ids])
        fields = [x[0] for x in result.description]
        for values in result.fetchall():
            raw = dict(zip(fields, values))
            raw_records[raw["id"]] = raw
    remaining = inventory[~inventory.id.isin(suspects)]
    # Vectorized haversine over only 24,512 provided school-labelled records.
    import numpy as np
    remaining_lon, remaining_lat = np.radians(remaining.lon.to_numpy()), np.radians(remaining.lat.to_numpy())
    cases, flat = [], []
    for spec in CASES:
        a = indexed.loc[spec["suspect"]]
        case = dict(spec, verified_on="2026-10-07", suspect_record=dict(a, **raw_records[spec["suspect"]]))
        case["nces_address_corroboration"] = dict(nces[NCES_IDS[spec["label"]]], retrieved_on="2026-10-07", license="Public domain", purpose="Discovery identity/address only; no geometry")
        case["suspect_record"]["minimum_tile_zoom"] = tile_zoom(a.lon, a.lat)
        before = inventory[inventory.GEOID == a.GEOID]
        after = remaining[remaining.GEOID == a.GEOID]
        case["tract_school_records_before"] = len(before)
        case["tract_school_records_after_reviewed_exclusion"] = len(after)
        case["binary_school_label_presence_changes"] = bool(len(before) and not len(after))
        p = math.radians(a.lat)
        h = np.sin((remaining_lat-p)/2)**2 + math.cos(p)*np.cos(remaining_lat)*np.sin((remaining_lon-math.radians(a.lon))/2)**2
        distances = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
        nearest_i = int(np.argmin(distances))
        nearest = remaining.iloc[nearest_i]
        case["nearest_remaining_school_label"] = {"id": nearest.id, "name": nearest["name"],
                                                   "distance_km": round(float(distances[nearest_i]), 3),
                                                   "warning": "Unverified label; straight-line distance from suspect point, not tract origin, route, or service access."}
        case["comparator_records"] = []
        for comparator_id in spec["comparators"]:
            b = indexed.loc[comparator_id]
            case["comparator_records"].append(dict(b, **raw_records[comparator_id],
                separation_km=round(great_circle_km(a.lon, a.lat, b.lon, b.lat), 3)))
        cases.append(case)
        first = case["comparator_records"][0] if case["comparator_records"] else {}
        flat.append({"label": spec["label"], "suspect_id": spec["suspect"], "region": a.region, "GEOID": a.GEOID,
                     "confidence": a.confidence, "operating_status": a.operating_status,
                     "ur_class": a.ur_class, "pop_total": a.pop_total, "svi_overall": a.svi_overall,
                     "tract_school_records_before": len(before), "tract_school_records_after_reviewed_exclusion": len(after),
                     "binary_school_label_presence_changes": case["binary_school_label_presence_changes"],
                     "comparator_id": first.get("id"), "separation_km": first.get("separation_km"),
                     "nearest_remaining_school_label": nearest["name"], "nearest_remaining_school_label_km": case["nearest_remaining_school_label"]["distance_km"],
                     "minimum_tile_zoom": case["suspect_record"]["minimum_tile_zoom"], "official_url": spec["official_url"], "nces_id": NCES_IDS[spec["label"]]})
    # Replace missing pandas/numpy values with JSON null before writing.
    serialized = json.dumps(cases, ensure_ascii=False, default=lambda v: v.item() if hasattr(v, "item") else str(v))
    clean = json.loads(serialized, parse_constant=lambda _: None)
    (OUT / "reviewed_cases.json").write_text(json.dumps(clean, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    pd.DataFrame(flat).to_csv(OUT / "reviewed_cases.csv", index=False)
    for row in flat:
        print(json.dumps(row, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
