# Numerical entry v1_zero_prior

Prepared 7 October 2026 for Bias Bounty Mapping Equity. This is a first-score baseline with constant `coverage_gap_score=0.0` for all 9,794 unique tracts in the latest platform sample. Zero is a deliberate lower-bound hypothesis, not learned from the sample's placeholder scores and not a claim of complete real-world coverage.

The prediction script reads only `GEOID` from the supplied sample. It does not read target/component values, strata, external discovery evidence or removed reference layers. It outputs only `GEOID,coverage_gap_score`. IDs stay as 11-digit strings, including leading zeros. Exact ID coverage, uniqueness and finite scores in [0,1] pass local format checks. There is no labelled local validation set or local RMSE, and no expected accuracy improvement is claimed.

All tracts, including zero-population, water-dominated or no-Overture-data tracts, receive the same prior. No components, reference counts, undefined flags or alternative weights are estimated. This is intentionally a baseline for obtaining the first official score, not a complete competitive prediction method.

Reproduce with Python's open-source standard library:

```text
python scripts/make_first_entry.py
```

The manifest records the input and output SHA-256, exact file, checks and limitations. The script never uploads. The external NCES corroboration and school-coordinate findings in discovery v0.2 are excluded from this scored computation. That discovery writeup remains a separate local artifact until its official delivery mechanism is confirmed; this numeric upload alone does not establish a valid special-prize entry.

Attribution: Humane Intelligence / Zindi / Radiant Earth challenge sample, downloaded through the official Data page. Challenge data is subject to its CC-BY-SA 4.0 terms. Codex assisted with drafting; no proprietary service is needed to run the script.

Official result verified on 7 October 2026: the user manually submitted this filename as entry `2cQVvovS` under `tomfng`. Public RMSE is **0.107246299**, with public rank **220** at the check. This is the first accepted numerical entry, so no improvement over an earlier accepted version can be claimed. All nine displayed bias-card rows are unavailable. There is still no local labelled RMSE or private score. The separate discovery writeup has not been delivered through a confirmed judging channel. See `official_result.json` for the recorded observations and source URLs.
