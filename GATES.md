# GATES.md  ,  20/20 must be green (extends nirnay 1-19 + 20 guard ECE)

1-19: reuse nirnay (scale-runaway RMS <0.5, usage entropy >2.0, probe monotonicity, seed determinism, hash match, Banking77 ≥0.86, etc.).
20: guard ECE fitted ≤0.05 else fail release.

Hardened per-slice floors (2026-10-07): en/Roman/Devanagari/code-switch each ≥0.60; PII synthetic/real-format/obfuscated each ≥0.80; freeze bundle `SHA256SUMS`+`LICENSES.json`; G0 probe >0.60.
