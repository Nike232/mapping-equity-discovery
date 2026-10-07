# Best Bias Discovery v0.6 — publication and reproduction

Participant **tomfng**; associated accepted numerical entry **2cQVvovS**. The methodology and evidence are **publicly published for consideration**. Organiser confirmation of valid award delivery, eligibility and the effective tie-break timestamp remains pending. This document synchronises publication metadata; findings and numerical evidence remain version **0.6**.

## Public entry points

| Material | Public location |
|---|---|
| Methodology post and receipt request | [Zindi discussion 35243](https://zindi.world/competitions/bias-bounty-mapping-equity-challenge/discussions/35243) |
| Full structured methodology | [v0.6 writeup](https://github.com/Nike232/mapping-equity-discovery/blob/main/runs/discovery_strengthening_v0.6/discovery_writeup_v0.6.md) |
| Code, evidence and source terms | [Public repository](https://github.com/Nike232/mapping-equity-discovery) |
| Immutable original review archive | [Release v0.6](https://github.com/Nike232/mapping-equity-discovery/releases/tag/v0.6) |

The release was published **7 October 2026 at 21:40:07 Asia/Shanghai (13:40:07 UTC)**. The post action was recorded between **21:44:37 and 21:44:38 Asia/Shanghai (13:44:37–13:44:38 UTC)**. Its page displays **7 Oct 2026, 21:44**, without an explicit zone label. These are publication observations, not an organiser-certified receipt timestamp. The last publication check found **0 replies** at 21:48:02 Asia/Shanghai; this is a historical check, not live monitoring.

All approved body words were verified after whitespace normalisation, together with the GitHub link. The forum rendered one paragraph; the structured full report is available in the repository. No new numerical submission accompanied publication. The associated all-zero numerical entry's public RMSE is **0.107246299**, not a Discovery score or award result.

## Fixed version

The release asset `mapping_equity_discovery_v0.6_review.zip` contains **70 files**, is **773,400 bytes**, and has SHA-256:

```text
23aa7411731445312eff97244bcf4ece3a045279460269e78ae79fec9889a39a
```

GitHub's asset digest matched the local archive. Tag **v0.6** pins commit **385053825e1122092258c93d9e68ecd002d359b3**. The original ZIP freezes evidence and pre-publication documentation. Its “prepared” status describes the freeze time. Later documentation on `main` records publication; findings, responses and the ZIP remain unchanged. `PACKAGE_CONTENTS.json` describes that archive, so old documentation hashes need not match later documentation on `main`. Use the release or tag v0.6 for the corresponding frozen snapshot. `.gitattributes` preserves frozen response bytes across Git checkouts.

## Reproduction

Extract the fixed archive and enter its root containing `requirements-discovery.txt` and `scripts/`. With Python 3.11:

```text
python -m pip install -r requirements-discovery.txt
python scripts/reproduce_discovery_v06.py
```

The same commands work from the current repository root. Missing permitted challenge inputs are downloaded and checked against frozen hashes: **16 Parquets, 403,578,493 bytes**. Default reproduction uses bundled selective NCES responses, one Census address response and one selected USFA department record. It does not query agency APIs, create predictions or submit to Zindi. A new environment needs network access for Python dependencies, DuckDB's spatial extension and any missing challenge inputs.

The runner regenerates evidence under `runs/discovery_scope/`, `runs/discovery_emergency/` and the v0.4–v0.6 strengthening folders. Expected results include 24,512 school records; 24 grid flags (20 rural/four urban); nine independent school comparisons at 17.395–544.008 km; four school and one fire tract label changes 1→0; Happy Camp campus-to-campus 0.403777 km and origin-to-suspect 38.972469 km; Oak Cliff suspect-to-address 6.533986 km and comparator-to-address 0.120234 km. These are evidence measurements, not organiser targets or representative error-rate estimates.

The full v0.4 pipeline passed previously. Added v0.5 open-core and v0.6 address/registry stages reproduced from frozen responses. A fresh-environment end-to-end v0.6 run is not claimed.

## Source and delivery boundaries

External evidence is **Discovery only**. The single address interpolation is explicitly MAF/TIGER-derived; no withdrawn road layer, replacement reference inventory, organiser component or target is reconstructed. NCES points are administrative geocodes. Census interpolation is not station-building certification, and the retired USFA register is not current operational-status proof. Terms, limitations and attribution are retained in the methodology, `NOTICE.md`, source README and frozen metadata.

The published Zindi post asks organisers to confirm whether the public methodology/package associated with **2cQVvovS** is valid delivery, identify any further required channel, and confirm the receipt/tie-break timestamp. Public availability and an accepted numerical CSV do not themselves establish award acceptance. Original publication observations remain in the project's publication record.
