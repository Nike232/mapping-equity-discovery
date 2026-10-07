# Mapping Equity — Best Bias Discovery v0.6

Participant **tomfng**; associated accepted numerical entry **2cQVvovS**. Published 7 October 2026 for consideration; **valid award delivery has not been confirmed**.

Read the [full methodology](https://github.com/Nike232/mapping-equity-discovery/blob/main/runs/discovery_strengthening_v0.6/discovery_writeup_v0.6.md), [public methodology post](https://zindi.world/competitions/bias-bounty-mapping-equity-challenge/discussions/35243) and [publication/reproduction record](https://github.com/Nike232/mapping-equity-discovery/blob/main/DELIVERY.md). This repository/package contains the Discovery evidence and the separate, already accepted all-zero numerical entry. The evidence is not a new main-board prediction.

For a fixed snapshot, use [release v0.6](https://github.com/Nike232/mapping-equity-discovery/releases/tag/v0.6): `mapping_equity_discovery_v0.6_review.zip`, 773,400 bytes, SHA-256 `23aa7411731445312eff97244bcf4ece3a045279460269e78ae79fec9889a39a`. Tag v0.6 pins commit `385053825e1122092258c93d9e68ecd002d359b3`. The ZIP and its `PACKAGE_CONTENTS.json` describe the pre-publication freeze; later documentation on `main` updates delivery status only. Original evidence, responses and findings remain unchanged.

Nine selected rural school identities have high-confidence points **17.395–544.008 km** from independently matched NCES administrative campus locations. Eight supplied comparators lie **7–55 m** from those locations. Three conflicts remain Rural→Rural, so urbanity alone does not reveal the community assignment error. Four rural tracts' school labels change **1→0** when individually excluding a reviewed point.

The strongest emergency case is **Oak Cliff Fire Protection District**. USFA independently records its institutional role, HQ address and phone. The shared address's Census interpolation is **6.533986 km** from the rural Station 1 point, versus **0.120234 km** from the supplied urban comparator. It strengthens the Bryant-area address evidence without certifying a station building, current activity or exact tract. The rural tract's fire labels also change **1→0**. These five count changes describe the supplied register, not real service absence or victims. Before treating such a point as a local response/staging base, reconcile its location with its identity and verify current assets with the responsible institution.

## Reproduce

From the extracted root with Python 3.11:

```text
python -m pip install -r requirements-discovery.txt
python scripts/reproduce_discovery_v06.py
```

The runner verifies frozen SHA-256 values and downloads missing **16 current permitted challenge Parquets (403,578,493 bytes)**. Frozen selective NCES responses, one Census address response and one USFA institution record support default reproduction without agency API queries. Execution uses open-source DuckDB spatial, pandas, numpy, requests and matplotlib; no paid API or proprietary model is required. No prediction or submission is created. The zero sample columns are formatting placeholders, never labels.

Expected school screen: 24,512 records; 24 grid flags (20 rural/four urban); 18.2× flag-prevalence ratio, 17.9× within first-source Meta. Seven flags have corroboration and 17 remain candidates. The flag ratio is not an error rate. Happy Camp's elementary-origin lookup is 38.972469 km to the suspect versus 0.403777 km between independently matched campuses. Overture confidence concerns place existence, not positional certification; maximum-confidence selection is our illustrative downstream policy.

The complete v0.4 recipe passed earlier. The v0.5 open-core stage and new v0.6 station-address stage passed from frozen responses. No redundant complete rerun or fresh-environment/network-download test is claimed. `PACKAGE_CONTENTS.json` records fixed-archive file hashes, including documentation at freeze time. A new environment needs network access for Python dependencies, DuckDB spatial and any missing challenge inputs; default reproduction does not fetch agency evidence.

## Evidence and source terms

| Evidence | Path |
|---|---|
| Latest methodology | `runs/discovery_strengthening_v0.6/discovery_writeup_v0.6.md` |
| Independent emergency address and role | `runs/discovery_strengthening_v0.6/station_address_results.json` |
| Frozen Census response and selected USFA record | `runs/discovery_strengthening_v0.6/census_station_address.json`, `usfa_selected_department.json` |
| New source parameters, dates, hashes and reuse basis | `runs/discovery_strengthening_v0.6/external_provenance.json`, `fema_reuse_policy.json` |
| Nine independent school comparisons | `runs/discovery_strengthening_v0.5/independent_location_results.json` |
| Happy Camp identity lookup and figure | `runs/discovery_strengthening_v0.5/happy_camp_identity_results.json`, `happy_camp_identity_lookup.png` |
| Lakeview metadata and independent comparison | `runs/discovery_strengthening_v0.5/lakeview_case_open_sources.json` |
| NCES exact queries and public-domain metadata | `runs/discovery_strengthening_v0.4/` and `runs/discovery_strengthening_v0.5/nces_*.json` |
| Original school/grid measurements and input hashes | `runs/discovery_scope/` |
| Supplied Station 1/road evidence | `runs/discovery_emergency/oak_cliff_case.json`, `oak_cliff_conflict.png` |
| Separate accepted numerical baseline | `runs/entry_v1/methodology.md`, `official_result.json` |

External evidence is **Discovery only**, excluded from all main-board predictions. The single address interpolation is transparently MAF/TIGER-derived; no TIGER road layer, withdrawn reference inventory, organiser component or target is reconstructed. NCES points are 2024–25 administrative address geocodes. The retired USFA registry reports records added/changed before June 2026; its department record validates a reported HQ identity, not numbered Station 1's surveyed geometry or active 2026 status. Census interpolation and the 120 m-away comparator cross a tract boundary, so neither is declared a verified station tract.

Preserve [source attribution and terms](https://github.com/Nike232/mapping-equity-discovery/blob/main/NOTICE.md): challenge CC-BY-SA 4.0; Overture/place per-source CDLA-Permissive-2.0; OpenStreetMap contributors and road-derived ODbL obligations; Census, CDC/ATSDR SVI, USFS; public-domain NCES; Census public-domain TIGER geospatial results; the specific [FEMA reuse policy](https://www.fema.gov/about/website-information) supporting the selected official USFA record. No blanket `.gov` copyright assumption or agency endorsement is made. Source README, metadata, parameters and access dates are included. Historical school safety PDFs, their contextual research draft and NERIS contractor data are excluded. Original Python code is MIT-licensed; that licence does not replace source-data terms. Codex assisted development and writing.

## Delivery

The associated numerical entry **2cQVvovS** was accepted with public RMSE **0.107246299**. No new official score or award result is claimed. The methodology/package and [Zindi post 35243](https://zindi.world/competitions/bias-bounty-mapping-equity-challenge/discussions/35243) are public. The post asks organisers to confirm receipt, eligibility and timestamp, or identify the required channel. The methodology's effective delivery channel and tie-break timestamp remain unconfirmed; public availability alone does not establish valid award delivery.
