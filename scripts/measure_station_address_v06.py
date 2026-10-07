"""Discovery only: one shared station address, not a reference inventory.

Census address-range geocode is approximate and does not prove building/station
existence. It never enters predictions, road counts, organiser target estimation
or reconstruction. Default uses a frozen response; --fetch records a new vintage.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import csv
import io

import duckdb
import requests

from measure_discovery_independent_locations import distance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/discovery_strengthening_v0.6"
URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
PARAMS = {"address": "13425 S Bryant Ave, Edmond, OK 73034", "benchmark": "Public_AR_Current", "format": "json"}
REGISTRY_URL = "https://apps.usfa.fema.gov/registry/api/download/national?cacheKey=1791378526054"


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--fetch-registry", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "census_station_address.json"
    if args.fetch:
        r = requests.get(URL, params=PARAMS, timeout=(10, 45))
        r.raise_for_status()
        response = r.json()
        save(path, response)
        save(OUT / "external_provenance.json", {
            "purpose": "Best Bias Discovery only: one previously selected exact station-address conflict. No reference road/facility inventory, component or target reconstruction. Excluded from every main-board prediction.",
            "sources": [{"url": URL, "params": PARAMS, "resolved_url": r.url,
                         "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                         "file": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
            "license_basis": "Public-domain Census TIGER geospatial data; federal Census geocoder produces one address-range interpolation. Census explicitly describes TIGER as public domain. This is not a station-location inventory or current facility verification.",
            "license_url": "https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html",
            "api_documentation_url": "https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html",
            "limitations_url": "https://www.census.gov/programs-surveys/geography/technical-documentation/complete-technical-documentation/census-geocoder.html",
            "accessed_on": "2026-10-07",
            "scope": "One supplied address only. MAF/TIGER underlies this Discovery-only geocode; no TIGER road layer is downloaded or measured, and no data is used for the main-board target.",
        })
    provenance = json.loads((OUT / "external_provenance.json").read_text(encoding="utf-8"))
    if args.fetch_registry:
        r = requests.get(REGISTRY_URL, timeout=(10, 60))
        r.raise_for_status()
        selected = []
        fields = ["FDID", "Fire dept name", "HQ addr1", "HQ addr2", "HQ city", "HQ state", "HQ zip", "HQ phone", "County", "Dept Type", "Organization Type"]
        for row in csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))):
            clean = {k.strip(): v.strip() for k, v in row.items()}
            if clean["FDID"] == "42011" and clean["HQ state"] == "OK":
                selected.append({k: clean[k] for k in fields})
        if len(selected) != 1 or selected[0]["Fire dept name"] != "Oak Cliff Fire Protection District":
            raise ValueError("Selected department identity changed")
        registry_path = OUT / "usfa_selected_department.json"
        save(registry_path, {"selection": {"FDID": "42011", "HQ state": "OK"}, "records": selected,
                             "scope": "One department identity/HQ address and role; no station inventory, counts, personnel statistics or coordinates retained.",
                             "currency": "Registry no longer accepts updates; source page says downloads reflect records added/changed before June 2026. Not current incident or facility-status proof."})
        provenance["usfa_registry"] = {
            "url": REGISTRY_URL, "page_url": "https://apps.usfa.fema.gov/registry/download",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "original_download_bytes": len(r.content),
            "original_download_sha256": hashlib.sha256(r.content).hexdigest(),
            "file": registry_path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
            "selection": "Exact OK FDID 42011, previously matched by name and shared supplied HQ address/ZIP/phone. FDIDs are state-specific. Trimmed header/value whitespace only; retain 11 institution fields.",
            "permission_basis": "FEMA's official-sites page lists USFA and says most FEMA material is copyright-free and may be copied/distributed without permission, except credited restricted content. No separate copyright notice was observed in this official registry CSV. This basis is specific to the FEMA publication policy, not a blanket inference from a .gov URL; preserve source/date/attribution.",
            "permission_url": "https://www.fema.gov/about/website-information",
            "permission_evidence_file": "runs/discovery_strengthening_v0.6/fema_reuse_policy.json",
            "no_endorsement": "USFA/FEMA did not endorse this discovery or validate our location interpretation.",
        }
        save(OUT / "external_provenance.json", provenance)
    if hashlib.sha256(path.read_bytes()).hexdigest() != provenance["sources"][0]["sha256"]:
        raise ValueError("Frozen Census response hash differs")
    response = json.loads(path.read_text(encoding="utf-8"))
    matches = response["result"]["addressMatches"]
    if len(matches) != 1:
        raise ValueError("Expected the frozen single address match")
    matched = matches[0]
    point = {"lon": matched["coordinates"]["x"], "lat": matched["coordinates"]["y"]}
    station = json.loads((ROOT / "runs/discovery_emergency/oak_cliff_case.json").read_text(encoding="utf-8"))
    registry_source = provenance["usfa_registry"]
    registry_path = ROOT / registry_source["file"]
    if hashlib.sha256(registry_path.read_bytes()).hexdigest() != registry_source["sha256"]:
        raise ValueError("Frozen USFA subset hash differs")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))["records"][0]
    db = duckdb.connect()
    db.execute("LOAD spatial")
    q = db.execute("""SELECT t.GEOID,s.ur_class,s.pop_total,s.svi_overall
        FROM read_parquet(?) t LEFT JOIN read_parquet(?) s ON t.GEOID=s.GEOID
        WHERE ST_Intersects(t.geometry,ST_Point(?,?))""",
        [str(ROOT / "data/screening/strata/eastern-ok/eastern-ok-census-tracts.parquet"),
         str(ROOT / "data/screening/strata/eastern-ok/eastern-ok-strata-tract-table.parquet"), point["lon"], point["lat"]])
    tracts = [dict(zip([v[0] for v in q.description], r)) for r in q.fetchall()]
    result = {
        "shared_supplied_address": PARAMS["address"], "matched_address": matched["matchedAddress"],
        "usfa_department_record": registry,
        "registry_role": "Registered local fire-protection district, mostly volunteer; HQ address, ZIP and phone match both supplied Station 1 identities. Registry validates department identity/HQ address, not numbered Station 1 geometry or active 2026 service.",
        "match_caveat": "Supplied street suffix AVE standardized to RD; preserve both. Coordinates are interpolated along an address range, which can include numbers without actual structures.",
        "benchmark": response["result"]["input"]["benchmark"], "census_address_point": point,
        "census_point_supplied_tract_matches": tracts,
        "suspect_id": station["a"]["id"], "comparator_id": station["b"]["id"],
        "suspect_to_census_address_km": round(distance(station["a"], point), 6),
        "comparator_to_census_address_km": round(distance(station["b"], point), 6),
        "suspect_tract": station["a"]["GEOID"], "suspect_urbanity": station["a"]["ur_class"],
        "fire_labels_before": station["a"]["same_category_before"],
        "fire_labels_after_individual_quarantine": station["a"]["same_category_after_excluding_this_id"],
        "inference": "Independent address-range evidence corroborates the Bryant-area comparator and contradicts the rural Western/Simmons point. It strengthens address-location consistency, not a surveyed station point or an observed dispatch failure.",
        "operational_application": "Before staging or mutual-aid mapping treats a supplied Station 1 identity as a local base, reconcile its shared address with its point and verify current facility status. Do not add a new station from this geocode or assume a tract has no fire service.",
        "no_claims": "No verified physical station coordinates, route/time, active service boundary, harmed population or actual misdispatch. No main-board prediction or submission.",
    }
    save(OUT / "station_address_results.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
