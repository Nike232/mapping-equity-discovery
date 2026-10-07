"""Discovery only: named evacuation-campus lookup and Lakeview location conflict.

Default uses frozen selective public-domain responses. --fetch first records
name/address identity matching without geometry, then retrieves three exact IDs.
No prediction, removed reference inventory, target, route or incident delay.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math

import duckdb
import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from find_coordinate_artifacts import tile_zoom
from measure_discovery_independent_locations import distance, SERVICE, PREFIX, REGIONS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/discovery_strengthening_v0.5"
IDS = {
    "elementary_origin": "f22af2bd-6e41-4b50-875b-6ea17ade8014",
    "high_school_suspect": "61281033-1be5-4ac5-8f3e-5a410a791fff",
    "high_school_comparator": "249bb167-b742-4eb0-a38d-96e6476f84c6",
    "lakeview_suspect": "c5484503-726f-4b8c-9612-1a6965679451",
}
NCES_IDS = {"elementary_origin": "061653002087", "high_school": "063694006277",
            "lakeview": "481281006371"}


def save(path, value):
    # Original inventory has missing pandas values; JSON must use null.
    value = json.loads(json.dumps(value, ensure_ascii=False, default=lambda x: x.item() if hasattr(x, "item") else str(x)),
                       parse_constant=lambda _: None)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def fetch():
    fields = ["NCESSCH", "SURVYEAR", "SCH_NAME", "LSTREET1", "LCITY", "LSTATE", "LZIP", "PHONE", "MEMBER"]
    where_identity = (f"(UPPER({PREFIX}SCH_NAME) LIKE '%LAKEVIEW%' AND UPPER({PREFIX}LCITY)='AMARILLO')"
                      f" OR UPPER({PREFIX}SCH_NAME) LIKE '%HAPPY CAMP%'")
    identity = {"f": "pjson", "where": where_identity,
                "outFields": ",".join(PREFIX + f for f in fields), "returnGeometry": "false"}
    locations = dict(identity, where=PREFIX + "NCESSCH IN (" + ",".join("'" + x + "'" for x in NCES_IDS.values()) + ")",
                     returnGeometry="true", outSR="4326")
    sources = []
    for name, url, query in [
        ("nces_identity_selection.json", SERVICE + "/query", identity),
        ("nces_selected_locations.json", SERVICE + "/query", locations),
        ("nces_layer_metadata.json", SERVICE, {"f": "pjson"}),
        ("nces_item_metadata.json", SERVICE + "/iteminfo", {"f": "pjson"}),
    ]:
        response = requests.get(url, params=query, timeout=(10, 45))
        response.raise_for_status()
        value = response.json()
        if "error" in value:
            raise ValueError(value["error"])
        path = OUT / name
        save(path, value)
        sources.append({"url": url, "params": query, "resolved_url": response.url,
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "file": path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    save(OUT / "external_provenance.json", {
        "purpose": "Best Bias Discovery only: one newly matched Lakeview identity and two named Happy Camp campuses. Excluded from every main-board prediction.",
        "license": "Public domain, explicitly stated in NCES EDGE layer description and item metadata",
        "selection": "Lakeview name, district URL, Amarillo locality, Lair Road and ZIP matched before coordinates were obtained; 6409 versus 6407 street-number discrepancy retained. Happy Camp identities already established; elementary origin is named on the safety-plan cover. Exact-ID locations requested after the no-geometry identity query. Curated cases, not a prevalence sample.",
        "sources": sources,
    })


def tract_matches(db, point):
    rows = []
    for region in REGIONS:
        tracts = ROOT / f"data/screening/strata/{region}/{region}-census-tracts.parquet"
        strata = ROOT / f"data/screening/strata/{region}/{region}-strata-tract-table.parquet"
        q = db.execute("""SELECT t.GEOID, s.ur_class, s.pop_total, s.svi_overall
             FROM read_parquet(?) t LEFT JOIN read_parquet(?) s ON t.GEOID=s.GEOID
             WHERE ST_Intersects(t.geometry, ST_Point(?,?))""",
             [str(tracts), str(strata), point["lon"], point["lat"]])
        rows.extend(dict(zip([x[0] for x in q.description], r), region=region) for r in q.fetchall())
    return rows


def figure(e, contextual=True):
    origin = e["nces_elementary_point"]
    def xy(point):
        return ((point["lon"]-origin["lon"])*111.195*math.cos(math.radians(origin["lat"])),
                (point["lat"]-origin["lat"])*111.195)
    wrong = xy(e["supplied_records"]["high_school_suspect"])
    comparator = xy(e["supplied_records"]["high_school_comparator"])
    school = xy(e["nces_high_school_point"])
    native_origin = xy(e["supplied_records"]["elementary_origin"])
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.5))
    fig.subplots_adjust(left=.07, right=.98, top=.75, bottom=.20, wspace=.30)
    axes[0].scatter(0, 0, s=80, marker="s", color="#1b7780", zorder=3)
    axes[0].scatter(*wrong, s=80, color="#b53d32", zorder=3)
    axes[0].plot([0, wrong[0]], [0, wrong[1]], color="#b53d32", lw=1.7)
    axes[0].annotate("Elementary origin /\nverified high-school area", (0, 0), xytext=(8, -27), textcoords="offset points", fontsize=9)
    axes[0].annotate("Higher-confidence\nhigh-school record", wrong, xytext=(-10, 28), textcoords="offset points", ha="right", fontsize=9, color="#b53d32")
    axes[0].text(.05, .025, f"Origin → suspect: {e['nces_origin_to_suspect_km']:.3f} km\nConfidence {e['supplied_records']['high_school_suspect']['confidence']:.4f}", transform=axes[0].transAxes, fontsize=10, color="#b53d32")
    axes[0].set_xlim(-4, 24)
    axes[0].set_ylim(-40, 6)
    axes[0].set_title("Location chosen by highest supplied confidence", fontsize=11, pad=14)
    axes[1].scatter(0, 0, s=80, marker="s", color="#1b7780", label="NCES elementary point", zorder=4)
    axes[1].scatter(*native_origin, s=70, marker="x", color="#1b7780", label="Supplied elementary point", zorder=5)
    axes[1].scatter(*school, s=110, marker="o", facecolors="none", edgecolors="#40494e", linewidths=1.8, label="NCES high-school point", zorder=4)
    axes[1].scatter(*comparator, s=35, color="#b28b29", label="Supplied associated comparator", zorder=5)
    axes[1].plot([0, school[0]], [0, school[1]], color="#40494e", lw=1.5)
    axes[1].annotate("Elementary", (0, 0), xytext=(7, -18), textcoords="offset points", fontsize=9)
    axes[1].annotate("High-school campus area", school, xytext=(6, 15), textcoords="offset points", fontsize=9)
    axes[1].text(.04, .05, f"NCES campus-to-campus: {e['nces_campus_to_campus_km']:.3f} km\nComparator confidence {e['supplied_records']['high_school_comparator']['confidence']:.4f}", transform=axes[1].transAxes, fontsize=10)
    axes[1].set_xlim(-.65, .22)
    axes[1].set_ylim(-.22, .36)
    axes[1].set_title("Local detail: same named destination identity", fontsize=11, pad=14)
    axes[1].legend(loc="upper right", fontsize=7.2, frameon=False)
    for ax in axes:
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Approximate east/west offset from elementary point (km)", fontsize=8)
        ax.set_ylabel("Approximate north/south offset (km)", fontsize=8)
        ax.grid(color="#e2e5e6", lw=.6)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("A documented evacuation destination has the more confident point in the wrong community" if contextual else "Same school identity: higher confidence chooses the wrong community", fontsize=14, fontweight="bold", y=.97)
    fig.text(.5, .895, "2021–22 Happy Camp elementary safety plan, physical p.34: high-school gymnasium is one named evacuation destination" if contextual else "Supplied school name/phone pair compared with selected public-domain NCES campus points", ha="center", fontsize=9)
    fig.text(.5, .03, "Counterfactual lookup, not an observed evacuation. Distances are straight-line; NCES administrative campus points do not locate a gym entrance.\nHistorical plan is not proof of an active 2026 designation. Source: supplied Overture; NCES EDGE public-domain 2024–25 points. No basemap." if contextual else "School-location lookup sensitivity, not an observed incident, verified evacuation destination, travel time or entrance location.\nSource: supplied Overture (CDLA-Permissive-2.0); NCES EDGE public-domain 2024–25 administrative points. No basemap.", ha="center", fontsize=8, color="#50585e")
    fig.savefig(OUT / ("happy_camp_evacuation_lookup.png" if contextual else "happy_camp_identity_lookup.png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--open-core", action="store_true", help="Generate only numerical exhibits without historical contextual claims")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        fetch()
    response = json.loads((OUT / "nces_selected_locations.json").read_text(encoding="utf-8"))
    nces = {f["attributes"][PREFIX + "NCESSCH"]: f for f in response["features"]}
    def point(key):
        g = nces[NCES_IDS[key]]["geometry"]
        return {"lon": g["x"], "lat": g["y"]}
    def attributes(key):
        return {k.removeprefix(PREFIX): v for k, v in nces[NCES_IDS[key]]["attributes"].items()}
    inventory = pd.read_csv(ROOT / "runs/discovery_scope/school_inventory.csv", dtype={"GEOID": str})
    indexed = inventory.set_index("id")
    db = duckdb.connect()
    db.execute("LOAD spatial")
    records = {key: dict(indexed.loc[value], id=value) for key, value in IDS.items()}
    for region in ["northern-ca", "south-central-tx"]:
        path = ROOT / f"data/screening/reference/{region}/{region}-overture-pois.parquet"
        q = db.execute("SELECT id, addresses, websites, phones, sources FROM read_parquet(?) WHERE id IN (SELECT unnest(?))",
                       [str(path), list(IDS.values())])
        for values in q.fetchall():
            raw = dict(zip([x[0] for x in q.description], values))
            key = next(k for k, v in IDS.items() if v == raw["id"])
            records[key].update(raw)
    e = {
        "scenario": "Counterfactual resolving the named high-school destination in a historical elementary evacuation plan using supplied same-name/phone records and highest confidence. Not observed operational use.",
        "nces_elementary_id": NCES_IDS["elementary_origin"], "nces_high_school_id": NCES_IDS["high_school"],
        "nces_elementary_attributes": attributes("elementary_origin"), "nces_high_school_attributes": attributes("high_school"),
        "nces_elementary_point": point("elementary_origin"), "nces_high_school_point": point("high_school"),
        "supplied_records": {k: records[k] for k in ["elementary_origin", "high_school_suspect", "high_school_comparator"]},
        "nces_campus_to_campus_km": round(distance(point("elementary_origin"), point("high_school")), 6),
        "nces_origin_to_suspect_km": round(distance(point("elementary_origin"), records["high_school_suspect"]), 6),
        "supplied_origin_to_suspect_km": round(distance(records["elementary_origin"], records["high_school_suspect"]), 6),
        "supplied_origin_to_comparator_km": round(distance(records["elementary_origin"], records["high_school_comparator"]), 6),
        "comparator_to_nces_high_school_km": round(distance(records["high_school_comparator"], point("high_school")), 6),
        "elementary_supplied_to_nces_km": round(distance(records["elementary_origin"], point("elementary_origin")), 6),
        "highest_confidence_selected_id": max((IDS["high_school_suspect"], IDS["high_school_comparator"]), key=lambda x: indexed.loc[x, "confidence"]),
        "illustrative_threshold_0_93_retained_ids": [r["id"] for k, r in records.items() if k.startswith("high_school_") and r["confidence"] >= .93],
        "nces_origin_tracts": tract_matches(db, point("elementary_origin")),
        "nces_destination_tracts": tract_matches(db, point("high_school")),
        "limitations": "Historical plan; active designation, actual use and harm not established. NCES points are administrative school geocodes, not gym doors. No road route, travel time, gym capacity or evacuation-delay estimate. Associated comparator is a school apparel page, not a separately validated campus or public shelter.",
    }
    e["distance_ratio_suspect_to_campus"] = round(e["nces_origin_to_suspect_km"] / e["nces_campus_to_campus_km"], 3)
    if not args.open_core:
        save(OUT / "happy_camp_evacuation_results.json", e)
    core = dict(e, scenario="School-identity lookup sensitivity: select the highest-confidence supplied same-name/phone high-school point and measure from the matched elementary campus. Emergency use is a hypothetical application, not a verified designation or incident.",
                limitations="NCES points are administrative geocodes, not entrances. Associated comparator is an apparel page, not a new campus. No evacuation designation, public shelter eligibility, route, capacity, travel time or harm is established. Only openly licensed challenge records and public-domain NCES data support this core exhibit.")
    save(OUT / "happy_camp_identity_results.json", core)
    suspect = records["lakeview_suspect"]
    before = inventory[inventory.GEOID == suspect["GEOID"]]
    after = before[before.id != suspect["id"]]
    lakeview = {
        "label": "Lakeview Elementary School", "suspect_id": IDS["lakeview_suspect"], "nces_id": NCES_IDS["lakeview"],
        "suspect_record": suspect, "nces_attributes": attributes("lakeview"), "nces_point": point("lakeview"),
        "nces_point_tract_matches": tract_matches(db, point("lakeview")),
        "suspect_to_nces_km": round(distance(suspect, point("lakeview")), 3),
        "minimum_tile_zoom": tile_zoom(suspect["lon"], suspect["lat"]),
        "record_count_before": len(before), "record_count_after_individual_quarantine": len(after),
        "identity_evidence": "Name, Canyon ISD website, Amarillo locality, Lair Road and ZIP match NCES 481281006371 and current official school profile. Supplied street number 6409 differs from NCES/current official 6407; no supplied phone. Retain both values; no silent correction.",
        "official_url": "https://lv.canyonisd.net/campus-profile", "accessed_on": "2026-10-07",
        "limitations": "No supplied matched comparator; selective public-domain NCES corroboration only. Empty tract matches means outside the supplied challenge geometries, not absent school. Quarantine changes school-labelled records, not true school/service presence. No external inventory is inserted.",
    }
    if not args.open_core:
        save(OUT / "lakeview_case.json", lakeview)
    core_lakeview = {k: v for k, v in lakeview.items() if k not in ["official_url", "accessed_on", "identity_evidence"]}
    core_lakeview["identity_evidence"] = "Supplied Lakeview name, Canyon ISD URL, Amarillo locality, Lair Road and ZIP match public-domain NCES 481281006371. Supplied 6409 versus NCES 6407 street-number disagreement and missing supplied phone retained. No school webpage is required for this exhibit."
    save(OUT / "lakeview_case_open_sources.json", core_lakeview)
    old = json.loads((ROOT / "runs/discovery_strengthening_v0.4/independent_location_results.json").read_text(encoding="utf-8"))
    rows = old["rows"] + [{k: lakeview[k] for k in ["label", "suspect_id", "nces_id", "nces_attributes", "nces_point", "nces_point_tract_matches", "suspect_to_nces_km", "record_count_before", "record_count_after_individual_quarantine"]}]
    rows[-1]["suspect_point"] = {k: suspect[k] for k in ["lon", "lat", "GEOID", "ur_class", "confidence", "pop_total", "svi_overall"]}
    rows[-1]["supplied_comparators_to_nces"] = []
    summary = {
        "version": "0.5", "independent_school_cases": len(rows),
        "independent_discrepancy_km_min": min(r["suspect_to_nces_km"] for r in rows),
        "independent_discrepancy_km_max": max(r["suspect_to_nces_km"] for r in rows),
        "all_school_suspects_confidence_above_0_9": all(r["suspect_point"]["confidence"] > .9 for r in rows),
        "school_tracts_label_count_1_to_0": sum(r["record_count_before"] == 1 and r["record_count_after_individual_quarantine"] == 0 for r in rows),
        "fire_tracts_label_count_1_to_0": 1,
        "school_campus_enrolment_context_2024_25": sum(r["nces_attributes"]["MEMBER"] for r in rows),
        "rows": rows,
        "scope": "Eight v0.4 cases plus one newly matched Lakeview school. Selected evidence, not an error-rate sample. All external geometry is Discovery only. Elementary-origin enrolment is separate context, excluded from this nine-campus total.",
    }
    save(OUT / "independent_location_results.json", summary)
    if not args.open_core:
        figure(e)
    figure(e, contextual=False)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))
    print(json.dumps({k: e[k] for k in ["nces_campus_to_campus_km", "nces_origin_to_suspect_km", "supplied_origin_to_suspect_km", "supplied_origin_to_comparator_km", "distance_ratio_suspect_to_campus", "highest_confidence_selected_id", "illustrative_threshold_0_93_retained_ids"]}, ensure_ascii=False))
    print(json.dumps({k: lakeview[k] for k in ["label", "suspect_to_nces_km", "minimum_tile_zoom", "record_count_before", "record_count_after_individual_quarantine", "nces_point_tract_matches"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
