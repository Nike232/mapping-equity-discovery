"""Download the two-region, current-data discovery screen; no scoring references."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "humane-intelligence/bias-bounty-mapping-equity-challenge/"
BASE = "https://data.source.coop/"
REGIONS = ["northern-ca", "eastern-wa"]
SUFFIXES = ["overture-pois.parquet", "overture-roads-unfiltered.parquet",
            "census-tracts.parquet", "strata-tract-table.parquet"]


def download(item):
    key = item["key"]
    destination = ROOT / "data" / "screening" / key.removeprefix(PREFIX)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == item["bytes"]:
        return destination
    with requests.get(BASE + key, stream=True, timeout=(20, 60),
                      headers={"User-Agent": "MappingEquityDiscovery/0.1"}) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)
    if destination.stat().st_size != item["bytes"]:
        raise ValueError(f"Incomplete file: {destination.name}")
    print("READY", destination.name, destination.stat().st_size, flush=True)
    return destination


def main():
    manifest = json.loads((ROOT / "data" / "metadata" / "screen_manifest.json").read_text())
    selected = [item for item in manifest
                if any(item["key"].endswith("-" + suffix) for suffix in SUFFIXES)]
    print("DOWNLOAD_BYTES", sum(item["bytes"] for item in selected), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, selected))
    db = duckdb.connect()
    db.execute("LOAD spatial")
    for region in REGIONS:
        strata = ROOT / "data" / "screening" / "strata" / region / f"{region}-strata-tract-table.parquet"
        tract = ROOT / "data" / "screening" / "strata" / region / f"{region}-census-tracts.parquet"
        places = ROOT / "data" / "screening" / "reference" / region / f"{region}-overture-pois.parquet"
        fields = [r[0] for r in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(strata)]).fetchall()]
        print("STRATA_FIELDS", region, json.dumps([c for c in fields if any(s in c.lower()
              for s in ["svi_", "trib", "ruca", "population", "wildfire", "risk", "hazard", "limited", "cvi_"])]), flush=True)
        print("TRACT_FIELDS", region, db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(tract)]).fetchall(), flush=True)
        result = db.execute("""
            SELECT categories.primary AS category, count(*) AS n,
                   count(*) FILTER (WHERE coalesce(array_length(list_filter(addresses,
                       a -> length(trim(coalesce(a.freeform, ''))) > 0)), 0) > 0) AS with_address,
                   count(*) FILTER (WHERE coalesce(array_length(phones), 0) > 0) AS with_phone
            FROM read_parquet(?) GROUP BY 1 ORDER BY n DESC
            """, [str(places)]).fetchdf()
        critical = result[result.category.str.contains("fire|ems|ambulance|school", case=False, na=False)]
        print("CRITICAL_CATEGORIES", region, critical.to_json(orient="records"), flush=True)
        result.to_csv(ROOT / "runs" / f"{region}_poi_fields.csv", index=False)


if __name__ == "__main__":
    main()
