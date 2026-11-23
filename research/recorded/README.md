# Recorded-data feasibility and replication

## Beihang

The supplied BS.zip directly contains the two bs1 receiver products, plus IMU arrays and a generated 5G product. Matching the official trajectory pinned to revision 7b0517bbda1e3fe3dc4539729d22b8813067a7e9 gives 183 consecutive usable epochs, 37–219 s. The all-zero initial BDS row is discarded. The inferred field mapping uses BDS column 81 for time and receiver columns 1–3 for Cartesian ECEF position. Discrepancy is the Euclidean distance in metres between receiver and trajectory positions on the same epoch. The provider's study and repository identify the dataset. A matching empirical correlation or trajectory is supporting evidence for a field interpretation; it is not a substitute for a receiver export dictionary.

| Check | Independent reconstruction | Interpretation |
|---|---:|---|
| Pre-120 s median discrepancy at −1, 0, +1 s truth offset | 8.833, 0.416, 9.468 m | Supports zero offset for the position comparison. |
| Peak discrepancy | 98.751069 m at 170 s | Measured discrepancy for this field interpretation and replay. |
| Clock differences and squared centered scores, lag-one correlations | 0.798078 and 0.654874 | Match archived rounded diagnostics using receiver column 13. |
| Endpoint, cash, adaptive and restart after evaluation activation at 120 s | All silent | Reconstructed outcome for 100 epochs with 42 reference differences in [10,80). The editor source mentions 41 scores. This agreement in decisions does not resolve the one-score calibration discrepancy. |
| Conditional AR first alert | Manuscript reports 121 s | The original fitted parameters and exact processing implementation were not independently established. |
| Four 5G RMS errors, metres | 0.010983, 0.002951, 0.013737, 0.007928 | Recomputed across 221 epochs. Distinguish these inputs from 2,500/3,000 processed samples in older detector tables. |
| IMU records | Four unique files | Repeated tactical, aviation and consumer data appear under different folder names; identical bytes are not new missions. |

The table bs1_first_crossing.csv gives the first observed crossing *from t=120 s*, for all threshold intervals identifiable from the sample, and its slack relative to the reported 121 s alarm. For example, every limit strictly above 3.519433 m and at most 24.525621 m (use unrounded CSV endpoints at ties) is first crossed at 151 s in this window. The observed margin relative to the reported alarm would be 30 seconds. For a sufficiently small limit already exceeded at 120 s, that alarm arrives after crossing. No operational threshold, reaction duration, or causal prevented harm was measured. These are sensitivity results for an untreated recorded path, not a retrospective selection of safety requirements. The 98.75 m maximum is not an alert threshold.

Trajectory: https://github.com/BUAASatNav/the-BDS-Spoofing-Dataset-bs-/tree/7b0517bbda1e3fe3dc4539729d22b8813067a7e9 . The downloader checks its digest. Reproduce with python beihang.py /path/to/BS.zip. For offline use supply --trajectory /path/to/trajectory_XYZ.mat. Input downloads and pre-existing training/held-out runs are distinct. See inventory.csv for checksums.

## TEXBAT

The University of Texas provides four official processed receiver solutions used here. Input URLs and SHA-256 digests are in texbat_files.csv. Use python texbat.py; its default cache is temporary. Original scenario descriptions: https://radionavlab.ae.utexas.edu/texbat/ . The supplied output reports receiver time from the first solution. First solution times are recorded individually in the CSV.

| Record | Evaluation activation (s since first fix) | Endpoint | Cash 0.5 | Adaptive | Restart |
|---|---:|---:|---:|---:|---:|
| cleanStatic | 110 | silent | silent | 202 | silent |
| ds2 | 115 | 136 | 154 | 140 | 151 |
| ds3 | 115 | silent | silent | 291 | silent |
| ds7 | 150 | 395 | 392 | 341 | 320 |

All 16 cells match the archived alarm table with clock differences labelled by their right-hand epochs, calibration at epochs 20–99, closest solution to each elapsed whole second and record-specific activation. These settings were reconstructed using the published results; matching is not a prospective blinded performance experiment. In particular a record-specific activation cannot be interpreted as an always-on deployment without an operational activation policy. AC(1) values for cleanStatic clock differences and their squared centered scores are 0.441881 and 0.598928. ds7's documented injection at about 110 s and physical time push at about 150 s are distinct anchors; these native scenario times also require registration to the receiver’s first-fix clock. Native SCV and estimated AR outputs have different decision and sampling chains and were not reproduced as original implementations. Position truth is not automatically time-error truth for a time-push scenario.

## Recorded certificate verdict

No run-independent population certificate follows by treating 183 bs1 epochs or sections of a common TEXBAT baseline as separately drawn missions. Under hypothetical iid mission sampling, one success in one mission with zero failures only yields a one-sided 95% upper bound of 0.95. Here even that sampling premise is unestablished. At a prespecified replay, the empirical error and threshold-slack curves are identified subject to alignment. To certify operation select the exposure distribution and frozen policy, specify a hardware/platform hazard threshold, verify clock/frame semantics, characterize reaction performance, and collect independent missions with complete outcomes or justify a bounded conditional process. For a 1% limit at one-sided 95% confidence, zero failures in 299 independent representative missions suffices for one prespecified endpoint.

## Clock-registration and coordinate-frame extension

Run python texbat.py --cache /path/to/cache then python field_audit.py --cache /path/to/cache --archive /path/to/BS.zip --trajectory /path/to/trajectory_XYZ.mat. The trajectory is the exact input checked by beihang.py. The latter audit downloads four corresponding GRID channel matrices. URLs and observed SHA-256 digests are in channel_files.csv. Receiver-relative offsets of the first fixes are 33.000553, 36.000633, 36.800229 and 33.000553 seconds. RF-to-initialization alignment is a separate timing condition. The common-window experiment uses activation 110 s and end 410 s from first fix in each file. The field_margin.pdf figure is regenerated by field_audit.py. Internal field consistency and reference trajectory alignment do not measure responses to intervention. Run python test_field.py for offline validation checks.
