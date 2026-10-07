"""Discovery-only, openly licensed address corroboration for reviewed cases.

NCES public-domain metadata and selected identity/address fields only.
returnGeometry=false; no coordinates, enrolment, target construction, bulk
facility inventory or prediction code. Response is saved for dated review.
"""
from pathlib import Path
import hashlib
import json

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs" / "discovery_scope" / "address_corroboration"
SERVICE = "https://nces.ed.gov/arcgis/rest/services/CCD/CCD_Data/MapServer"
PREFIX = "Public_Schools_2025_CCD_Final."


def get_json(url, params):
    response = requests.get(url, params=params, timeout=(10, 30))
    response.raise_for_status()
    value = response.json()
    if "error" in value:
        raise ValueError(value["error"])
    return value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    queries = []
    school_name = f"UPPER({PREFIX}SCH_NAME)"
    # Curated school identities, selected manually before querying NCES.
    conditions = [f"{school_name} LIKE '%HAPPY CAMP HIGH%'", f"{school_name} LIKE '%MCCLOUD HIGH%'",
                  f"{school_name} LIKE '%HORSE HEAVEN%'"]
    conditions += [f"{PREFIX}NCESSCH IN ('480001013567','481623001353','402277001139')"]
    conditions += [f"({PREFIX}STABR='TX' AND ({school_name} LIKE '%PINER MIDDLE%' OR {school_name}='MEADOWS EL'))"]
    for layer, where, fields in [
        (0, " OR ".join(conditions), [PREFIX + f for f in ["NCESSCH", "SURVYEAR", "SCH_NAME", "LSTREET1", "LCITY", "LSTATE", "LZIP", "PHONE"]]),
        (6, "UPPER(NAME) LIKE '%SOUTHERN BOONE%'", ["LEAID", "NAME", "STREET", "CITY", "STATE", "ZIP", "SCHOOLYEAR"]),
    ]:
        metadata_url = f"{SERVICE}/{layer}/iteminfo"
        metadata = get_json(metadata_url, {"f": "pjson"})
        params = {"f": "pjson", "where": where, "outFields": ",".join(fields), "returnGeometry": "false"}
        response = get_json(f"{SERVICE}/{layer}/query", params)
        metadata_path = OUT / f"nces_layer_{layer}_metadata.json"
        response_path = OUT / f"nces_layer_{layer}_addresses.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        queries.append({"url": f"{SERVICE}/{layer}/query", "params": params,
                        "metadata_url": metadata_url, "license": "Public domain (explicit layer description and iteminfo)",
                        "response_file": response_path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(response_path.read_bytes()).hexdigest()})
        print(json.dumps({"layer": layer, "records": [x["attributes"] for x in response.get("features", [])]}, ensure_ascii=False), flush=True)
    (OUT / "provenance.json").write_text(json.dumps({"retrieved_on": "2026-10-07", "purpose": "Discovery-only manual identity/address corroboration; no external coordinates or model inputs", "queries": queries}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
