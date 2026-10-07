# GATES.md: 20/20 must be green (extends nirnay 1-19, plus 20 guard ECE)

Nirnay 1-19 reused verbatim in spirit: scale runaway RMS below 0.5, usage
entropy above 2.0, probe monotonicity, seed determinism, hash match,
Banking77 at least 0.86, temp range sanity, checkpoint resume bit-identical,
collapse abort fires, ONNX leg1 exact, and the rest per nirnay GATES.md.

20. Guard ECE fitted at most 0.05 on heldout, else no release.

Hardened per-slice floors (2026-10-07): en, Roman, Devanagari, and
code-switch each at least 0.60; PII synthetic, real-format, and obfuscated
each at least 0.80; freeze bundle is SHA256SUMS plus LICENSES.json;
G0 probe above 0.60 or stop.

`scripts/eval_checkpoint.py --strict` checks the numeric gates that can be
checked from one eval file (guard acc, tool macro-F1, fitted ECE, language
floors). The remaining gates are process gates (hashes pinned before
training, human review done, raw JSON published) and are checked by hand
at release time.
