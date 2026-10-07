# MEMORY.md  ,  Suraksha-450M (living doc)

> Append-only. Newest entry on top. Every training/eval/export run appends a dated receipt. Mirrors `eulogik/nirnay` convention (`logs/` + this file). Pre-registered targets live in `SURAKSHA_IMPLEMENTATION_PLAN.md` §2.3  ,  don't edit them retroactively.

## Status
- Phase: scaffold v0.1 built 2026-10-07 (no model weights yet). Next: freeze real taxonomy + data hashes (Day 1-2 milestone).
- Repo: not git-initialized as of 2026-10-07. Single file `SURAKSHA_IMPLEMENTATION_PLAN.md`.

## Validated receipts (2026-10-07, Mac mini M4 10c 16GB)
- HW: `Mac16,10 / Apple M4 / 16GB`, `torch 2.12.1`, `torch.backends.mps.is_available() == True`. Memory budget (§5.1) plausible.
- `convaiinnovations/laya`: exists, Apache-2.0, ModernBERT-large 421M / 512 ctx, `laya-multilingual` mmBERT 322M / 1024, `Router(preload=True)` pattern real, ~3-4.5k likes (plan says 5.3k  ,  close, don't quote exact). Precedent `ggml-org/Laya-GGUF` exists -> GGUF path credible.
- `eulogik/nirnay-450m`: exists, Banking77 0.8792 / ECE raw 0.089 / 209ms MPS / 361ms CPU as claimed.
- `eulogik/OpenTrustBench`: exists, 8 OWASP-mapped rules, Trust Cards A-F, SARIF, `--fail-on high`, CLI + action + Docker. Static-only (regex)  ,  confirms need for learned head.
- `Cloudflare/clef` 27B + `clef-flash` 9B: exist, Apache-2.0, released 2026-10-01. Timing claim checks out.

## Decisions log
- 2026-10-07 (hardening): license allowlist Apache-2.0/MIT/BSD/CC0/CC-BY-4.0, deny NC/SA/GPL-data, unknown=fail; `freeze_data.py` must emit `LICENSES.json` + `SHA256SUMS`. Human check 500->1000 stratified, blocks G1. Per-slice floors (each lang slice ≥0.60, each PII slice ≥0.80). Day-1 multilingual probe + G0 probe >0.60 gates. En-only MVP first, schedule gate-gated.
- 2026-10-07: Base = laya English root first, distill to multi week 2 (not joint training day-1). Reason: en checkpoint can't read Devanagari; avoids tanking en gates.
- 2026-10-07: `enable_byte_path=False` v1, `max_len=512/192` en, `1024/256` multi, head-truncate + `truncated:true`. Reason: keeps nirnay memory profile.
- 2026-10-07: Labels by construction/template only, no LLM-judge in v1. Reason: avoids bias leakage; makes tool-risk ground truth free.
- 2026-10-07: Created `AGENTS.md` (commands, gates, API contract). `opencode.json` instructions: none yet  ,  revisit once `src/` exists.

## Pre-registered gates (pass/fail, copy from spec + 2026-10-07 hardening)
- Guard acc ≥0.85, macro-F1 ≥0.83 (n=3000 heldout, disjoint templates/tools/domains).
- Per-slice floors: en/Roman/Devanagari/code-switch each ≥0.60, Hinglish mean ≥0.68. PII synthetic/real-format/obfuscated each ≥0.80.
- ECE raw ≤0.10, fitted ≤0.05, Brier ≤0.22.
- Banking77 ≥0.86. Latency b1 ≤220ms MPS / ≤380ms CPU. ONNX parity 37/37. G0 probe >0.60 else stop.
- Freeze bundle = `SHA256SUMS` + `LICENSES.json` pinned before training.

## Run log (append below)
### 2026-10-07  ,  scaffold v0.1 (seed 7, device mps)
- `pip install --break-system-packages laya==0.3.28` OK; `Agent.system_one` + `Router(preload)` + `guard_questions` API confirmed.
- `pytest tests/`: 5 passed (taxonomy, normalize, 422, Devanagari routing, server validation).
- `data_synth_guard --n 200` -> 400 rows; `freeze_data` dedupe 27/400 kept (template overlap expected), `SHA256SUMS`+`LICENSES.json` emitted; UNKNOWN-license fail path verified.
- `train.py --dry-run` OK; refuses without freeze bundle. Real G0/G1/RLCD/ONNX/GGUF are scaffold stubs (exit with wiring note).
### 2026-10-07, baseline smoke (stock laya zero shot, seed 7, device mps, n=500 synth rows)
- pi_acc 0.98 (250 text rows), tool_acc 1.0 (250 tool JSON rows). Slices: en 394 rows pi 1.0, roman 55 rows pi 0.91, devanagari 51 rows pi 1.0. Routing: en 449, multi 51.
- latency b1 full taxonomy: p50 214ms MPS, p95 252ms. Full payload in eval/baseline_laya.json (local, gitignored).
- caveat: templates are too easy (shared keywords like evil.com, Ignore previous), so these numbers overstate stock skill. Single hand probe without English cues scored noul 0.319 (miss). Do NOT use this as the gate. Real heldout needs disjoint templates plus unseen tools and obfuscated PII before G0.
### 2026-10-07, engine port + export verified (no full training yet)
- Vendored proven nirnay modules (concepts, lora, losses, rlcd, temps, c2f, deepsup, nope, bytes, hypercube, sgdr) plus guard_data and engine with guard mix, TOOL_RISK c2f, n_labels 4, byte path off.
- Engine smoke: run_phase_a steps=3 batch=2 on MPS, loss logged, ckpt written. Trained serving path via smoke ckpt returns sane guard probs.
- ONNX export on smoke ckpt: LEG1 raw-vs-wrapped 37/37, ORT parity 37/37 max_abs 1.9e-4, ort_cpu 87ms vs torch_cpu 110ms.
- `suraksha scan` verified: static via installed opentrustbench binary plus learned screen ranks evil.txt 1.0 over ok.txt 0.0.
- Data v2 frozen: 24k train / 3k test unique, disjoint tools and domains, all 4 language slices in test, 1000 stratified human review rows in data/review (unchecked, blocks G1).
<!-- template:
### YYYY-MM-DD  ,  <phase> (seed 7, device mps)
- data: `SHA256SUMS=` <hash>, `LICENSES.json=` <hash>, n_train=, n_test=
- ckpt: <path>, steps=, probe_acc=, banking77=, ece_raw/fitted=, brier=
- slices: en=, roman=, devanagari=, codeswitch=, pii_synth/format/obfus=
- latency: mps_b1=, cpu_b1=, onnx_parity= /37
- notes / abort reason:
-->

## Open risks / kill criteria (hardened 2026-10-07)
- Hinglish mean <0.68 or any lang slice <0.60 -> ship en-only v1, multi -> v1.1. Day-1 probe <0.45 triggers rescope before G0.
- ECE fitted >0.06 after 2 refits -> no release, publish negative result.
- PII any slice <0.80 -> block release; add context-embedded + obfuscated variants, never real PII.
- Unknown data license -> build fail. No `LICENSES.json` = no training.
- G0 probe ≤0.60 -> stop/reschedule. En-MVP first; multi/GGUF/Space stretch. Kaggle 2xT4 is $0 fallback.

## Honesty rules (repeat  ,  violated often)
- Raw `eval/*.json` + reliability PNG published every run. Zero-shot vs fine-tuned never mixed.
- Third-party Jev numbers always labeled `published, never measured here`.
- Trust Card = CI-grade credential, not certification.
