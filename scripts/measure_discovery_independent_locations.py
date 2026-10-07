"""Discovery only: selected NCES identities, coordinates and enrolment context.

Never imported by prediction code. No target construction or bulk reference
inventory. Default reproduction uses frozen public-domain responses; --fetch
refreshes this separate evidence folder and records retrieval time and hashes.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math

import duckdb
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/discovery_strengthening_v0.4"
SERVICE = "https://nces.ed.gov/arcgis/rest/services/CCD/CCD_Data/MapServer/0"
PREFIX = "Public_Schools_2025_CCD_Final."
MATCHES = {
    "Moe & Gene Johnson High School": "480001013567",
    "Seagoville Middle School": "481623001353",
    "Meadows Elementary School": "482566002874",
    "Happy Camp High School": "063694006277",
    "McCloud High School": "063694006278",
    "Horse Heaven Hills Middle School": "530393000750",
    "Piner Middle School": "484008004549",
    "U.S. Grant High School": "402277001139",
}
REGIONS = ["northern-ca", "eastern-wa", "maricopa-az", "eastern-ok", "south-central-tx"]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def get(url, params):
    response = requests.get(url, params=params, timeout=(10, 45))
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise ValueError(result["error"])
    return result, response.url


def fetch():
    fields = ["NCESSCH", "SURVYEAR", "SCH_NAME", "LSTREET1", "LCITY", "LSTATE", "LZIP", "PHONE",
              "LATCOD", "LONCOD", "MEMBER", "TOTAL", "SY_STATUS_TEXT", "VIRTUAL"]
    params = {"f": "pjson", "where": PREFIX + "NCESSCH IN (" + ",".join("'" + x + "'" for x in MATCHES.values()) + ")",
              "outFields": ",".join(PREFIX + f for f in fields), "returnGeometry": "true", "outSR": "4326"}
    provenance = []
    for name, url, query in [("nces_selected_school_locations.json", SERVICE + "/query", params),
                              ("nces_layer_metadata.json", SERVICE, {"f": "pjson"}),
                              ("nces_item_metadata.json", SERVICE + "/iteminfo", {"f": "pjson"})]:
        value, resolved = get(url, query)
        path = OUT / name
        save(path, value)
        provenance.append({"url": url, "params": query, "resolved_url": resolved,
                           "file": path.relative_to(ROOT).as_posix(),
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    save(OUT / "external_provenance.json", {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Best Bias Discovery only: eight previously reviewed identities, location comparison and enrolment context. Excluded from all scored predictions.",
        "license": "Public domain, explicitly stated in NCES EDGE layer description and item metadata",
        "selection": "Eight exact school IDs manually matched in v0.3 before retrieving coordinates; not a random sample or a complete error inventory.",
        "sources": provenance,
    })


def distance(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b["lon"]-a["lon"])/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(h, 1)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        fetch()
    response = json.loads((OUT / "nces_selected_school_locations.json").read_text(encoding="utf-8"))
    nces = {f["attributes"][PREFIX + "NCESSCH"]: f for f in response["features"]}
    cases = json.loads((ROOT / "runs/discovery_scope/reviewed_cases.json").read_text(encoding="utf-8"))
    db = duckdb.connect()
    db.execute("LOAD spatial")
    rows = []
    for case in cases:
        if case["label"] not in MATCHES:
            continue
        feature = nces[MATCHES[case["label"]]]
        attrs = {k.removeprefix(PREFIX): v for k, v in feature["attributes"].items()}
        point = {"lon": feature["geometry"]["x"], "lat": feature["geometry"]["y"]}
        locations = []
        for region in REGIONS:
            tracts = ROOT / f"data/screening/strata/{region}/{region}-census-tracts.parquet"
            strata = ROOT / f"data/screening/strata/{region}/{region}-strata-tract-table.parquet"
            q = db.execute("""SELECT t.GEOID, s.ur_class, s.pop_total, s.svi_overall
                FROM read_parquet(?) t LEFT JOIN read_parquet(?) s ON t.GEOID=s.GEOID
                WHERE ST_Intersects(t.geometry, ST_Point(?,?))""", [str(tracts), str(strata), point["lon"], point["lat"]])
            keys = [x[0] for x in q.description]
            locations.extend(dict(zip(keys, v), region=region) for v in q.fetchall())
        suspect = case["suspect_record"]
        rows.append({
            "label": case["label"], "suspect_id": case["suspect"], "nces_id": MATCHES[case["label"]],
            "nces_attributes": attrs, "nces_point": point, "nces_point_tract_matches": locations,
            "suspect_point": {k: suspect[k] for k in ["lon", "lat", "GEOID", "ur_class", "confidence", "pop_total", "svi_overall"]},
            "suspect_to_nces_km": round(distance(suspect, point), 3),
            "supplied_comparators_to_nces": [{"id": r["id"], "km": round(distance(r, point), 3)} for r in case["comparator_records"]],
            "record_count_before": case["tract_school_records_before"],
            "record_count_after_individual_quarantine": case["tract_school_records_after_reviewed_exclusion"],
            "sensitivity_scope": "Excludes only this suspect ID. No NCES school is added to the inventory; zero labels is not zero real schools.",
        })
    summary = {
        "version": "0.4", "cases": len(rows), "independent_discrepancy_km_min": min(r["suspect_to_nces_km"] for r in rows),
        "independent_discrepancy_km_max": max(r["suspect_to_nces_km"] for r in rows),
        "all_suspects_confidence_above_0_9": all(r["suspect_point"]["confidence"] > .9 for r in rows),
        "all_suspect_to_nces_over_5_km": all(r["suspect_to_nces_km"] > 5 for r in rows),
        "all_comparators_within_1_km": all(min(c["km"] for c in r["supplied_comparators_to_nces"]) < 1 for r in rows),
        "all_cases_have_comparator_within_60_m": all(min(c["km"] for c in r["supplied_comparators_to_nces"]) < .06 for r in rows),
        "same_urbanity_different_tract_cases": sum(any(t["ur_class"] == r["suspect_point"]["ur_class"] and t["GEOID"] != r["suspect_point"]["GEOID"] for t in r["nces_point_tract_matches"]) for r in rows),
        "campus_enrolment_context_2024_25": sum(r["nces_attributes"]["MEMBER"] for r in rows),
        "rows": rows,
        "limitations": "NCES administrative address geocodes for 2024-25, not surveyed entrance coordinates or current incident data. Enrolment is campus context, not a count of people harmed. Curated sample; no prevalence estimate. External geometry never enters scored predictions.",
    }
    save(OUT / "independent_location_results.json", summary)
    figure, ax = plt.subplots(figsize=(12.5, 6.5))
    figure.subplots_adjust(left=.29, right=.945, top=.78, bottom=.19)
    for i, row in enumerate(rows):
        suspect_m = row["suspect_to_nces_km"] * 1000
        comparator_m = min(c["km"] for c in row["supplied_comparators_to_nces"]) * 1000
        ax.plot([comparator_m, suspect_m], [i, i], color="#c9cdd0", lw=1.6, zorder=1)
        ax.scatter(comparator_m, i, color="#187e85", s=54, zorder=3, label="Nearest supplied comparator" if i == 0 else None)
        ax.scatter(suspect_m, i, color="#b84034", s=54, zorder=3, label="Reviewed suspect (confidence > 0.9)" if i == 0 else None)
        ax.annotate(f"{comparator_m:.0f} m", (comparator_m, i), xytext=(-8, -1), textcoords="offset points", ha="right", va="center", fontsize=8, color="#187e85")
        ax.annotate(f"{row['suspect_to_nces_km']:.1f} km", (suspect_m, i), xytext=(8, -1), textcoords="offset points", ha="left", va="center", fontsize=8, color="#b84034")
    ax.set_yticks(range(len(rows)), [r["label"] for r in rows], fontsize=10)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlim(2, 1100000)
    ax.set_xticks([10, 100, 1000, 10000, 100000], ["10 m", "100 m", "1 km", "10 km", "100 km"])
    ax.grid(axis="x", color="#e1e4e5", lw=.7)
    ax.set_axisbelow(True)
    ax.set_xlabel("Straight-line distance to the matched NCES 2024–25 administrative school point (log scale)", fontsize=9)
    ax.spines[["top", "right", "left"]].set_visible(False)
    figure.legend(loc="upper center", bbox_to_anchor=(.60, .93), ncol=2, frameon=False, fontsize=8.5)
    figure.suptitle("Eight school identities: high confidence, wrong community", fontweight="bold", fontsize=16, y=.98)
    ax.set_title("17.4–441.4 km discrepancies; nearest supplied comparators are 7–55 m from NCES", fontsize=10, pad=17)
    figure.text(.5, .025, "Selected cases, not an error-rate sample. NCES points are address geocodes, not surveyed entrances.\nDiscovery-only external evidence. Sources: NCES EDGE (public domain); supplied Overture 2026-08-19.0 (CDLA-Permissive-2.0).", ha="center", fontsize=8, color="#50585e")
    figure.savefig(OUT / "independent_school_locations.png", dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(json.dumps({k:v for k,v in summary.items() if k != "rows"}, ensure_ascii=False))
    for row in rows:
        print(json.dumps({"label": row["label"], "km": row["suspect_to_nces_km"], "comparators": row["supplied_comparators_to_nces"], "enrolment": row["nces_attributes"].get("MEMBER"), "nces_tract": row["nces_point_tract_matches"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
