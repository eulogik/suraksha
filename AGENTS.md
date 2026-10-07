# AGENTS.md: Suraksha 450M

## Working rules
- Never assume or guess. If you are not sure, open the file or run the check. Give it full effort, no lazy shortcuts, no sloppy mistakes.
- Never mark a task done without proof. Run the test, command, or check that shows it works, then say it is done.
- Write like a person, not a bot. No em dashes. Keep it casual and plain, match the repo voice. No AI sounding filler.

> Greenfield guard model. Only `SURAKSHA_IMPLEMENTATION_PLAN.md` exists as the spec besides the scaffold. That doc is the build spec. Read section 2, 4, 5 before any code.

## What this is
- Calibrated System-1 guard: `state + typed questions -> P(prompt-injection, jailbreak, PII-leak, tool-risk)` in one forward pass. 450M, EN+Hinglish+Hindi, ONNX CPU + GGUF Ollama, Jev `/v1/systemone` compatible, Apache-2.0, $0 on Mac mini M4 16GB.

## Do not reinvent
- Fork/reuse, do not train from scratch:
  - Base: `convaiinnovations/laya` (ModernBERT-large 421M, `max_len=512`) for `suraksha-en`; `laya-multilingual` (mmBERT 322M, `max_len=1024`) for `suraksha-multi` week 2. Keeps `laya.load()` / `Router(preload=True)` / `serve_decide.py` compat.
  - Recipe: copy `eulogik/nirnay` Phase G0/G1/G2 (LoRA + bottleneck + head + pointer + RLCD + temperature fit). Static side: call `eulogik/OpenTrustBench` core, do not reimplement 8-rule scanner / SARIF / Trust Card.
- New params about 30M + 4-option guard verbalizer only. No new tokenizer. `enable_byte_path=False` in v1.

## Layout (create as built, section 9)
```
src/suraksha/{agent.py,server.py,train.py,train_rlcd.py,data_synth_guard.py,freeze_data.py,export_onnx.py,merge_lora.py}
configs/g1_guard.json  scripts/{eval_checkpoint.py,fit_temperatures.py,verify_onnx_parity.py}
eval/ assets/ onnx/ gguf/ spaces/ papers/suraksha/ GATES.md logs/
```

## Commands (exact)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers peft datasets scikit-learn onnx onnxruntime huggingface_hub
python -c "import torch; print(torch.backends.mps.is_available())"  # must be True

python src/suraksha/data_synth_guard.py --base eulogik/Bharat-Tiny-LLM-v3 --in data/raw/en_inject.jsonl --out data/guard_hinglish.jsonl --n 5000 --seed 7
python src/suraksha/freeze_data.py --in data/ --out data/frozen/ --seed 7  # must emit SHA256SUMS + LICENSES.json, fail on unknown license
sha256sum data/frozen/*.jsonl > data/frozen/SHA256SUMS  # pin before training

python src/suraksha/train.py --config configs/g1_guard.json --seed 7 --device mps
python src/suraksha/train_rlcd.py --ckpt checkpoints/best_g1.pt --steps 50 --seed 7
python scripts/eval_checkpoint.py --checkpoint checkpoints/best_g2.pt --suite guard_heldout
python scripts/fit_temperatures.py --preds eval/guard_heldout.json --out checkpoints/temperatures.json

python src/suraksha/export_onnx.py --ckpt checkpoints/best_g2.pt --out onnx/ --int8
python scripts/verify_onnx_parity.py --torch checkpoints/best_g2.pt --onnx onnx/  # must be 37/37
python src/suraksha/merge_lora.py --ckpt checkpoints/best_g2.pt --out fp16/
# Modelfile: FROM ./suraksha-450m-Q4_K_M.gguf + PARAMETER num_ctx 1024
ollama create suraksha-450m -f Modelfile
```

## Architecture constraints
- Frozen Laya encoder + LoRA r16 on Q/V only. Trainable: LoRA (lr 5e-5) + bottleneck (1e-4) + head (2e-4). Keep nirnay fixes: LayerNorm-affine-free before VQ, load-balancing aux, deep supervision layers 4/8/12.
- G0: 1000 steps LoRA-only guard-noul. G1: 6000 steps full. G2: 50 RLCD steps (REINFORCE group-mean baseline, log+spherical+ranked-prob reward). Checkpoint every 500, abort if accuracy halves.
- Context: en `max_len=512, head_max_len=192`; multi `1024/256`. Over budget goes to head-truncate + `truncated:true` in response. Never silent-truncate.
- Per-`(type, n_options)` temperature fit after G2. Report ECE raw + fitted + reliability diagram always.

## API contract (Jev-compatible, frozen)
- `SurakshaAgent(device="mps", checkpoint_path="phase_g.pt").system_one(state, questions)`; `suraksha-serve` gives `POST /v1/systemone` on port 8000.
- `questions`: `prompt_injection/jailbreak/pii_leak` = `noul`; `tool_risk` = `choice[safe,write,privileged,exfiltrate]` on JSON `{tool,args,permission_scope}`; `severity` = `score[benign,suspicious,malicious]`.
- Accept `criteria` as list or dict, ignore unknown fields, 422 on malformed question. `out["routing"]["model"]` = `suraksha-en` / `suraksha-multi`.

## Data + release gates (fail = no release)
- Freeze taxonomy + `SHA256SUMS` + `LICENSES.json` before training. Allow: Apache-2.0/MIT/BSD/CC0/CC-BY-4.0 (attribute). Deny: NC/SA/GPL-data, unknown = build fail. Tool-risk labels by construction (we generate the JSON); injection by template. No LLM-judge labeling in v1. Hindi scoring uses script-aware normalization (`normalize_ortho.py` + Roman to Devanagari transliteration pairs, not paraphrase alone).
- Day-1 baseline: probe `laya-multilingual` on 500 Hinglish guard items before G0. If below 0.45, rescope to en-only v1 right away.
- Human check 1000 stratified (250 each: en / Roman / Devanagari / code-switch). Block G1 until done.
- Thresholds: guard acc at least 0.85 / macro-F1 at least 0.83 (n=3000 heldout, disjoint templates/tools/domains); per-slice floor: each of en/Roman/Devanagari/code-switch at least 0.60 and mean Hinglish at least 0.68; PII slices (synthetic / real-format / obfuscated incl. split/redacted/base64) each at least 0.80; ECE raw max 0.10, fitted max 0.05, Brier max 0.22; Banking77 at least 0.86 (no forgetting, CC-BY-4.0 attribute); latency b1 max 220ms MPS / 380ms CPU; ONNX parity 37/37.
- G0 gate: probe above 0.60 at 1000 steps or stop/reschedule. Schedule is gate based, not date based. En-only MVP first, multi/GGUF/Space are stretch. Kaggle 2xT4 free notebook (laya precedent) is the $0 fallback if M4 runs out of memory or gets slow.
- Test-heldout never in train. Publish `eval/*.json` raw + `assets/reliability.png`.

## Honesty + license
- Never mix zero-shot vs fine-tuned numbers. Third-party Jev figures: label `published, never measured here`. Trust Card is CI-grade, not pentest/legal verdict.
- Code + synthetic = Apache-2.0. `LICENSES.json` per source (allowlist above), listed in card. No verbatim real PII. Use synthetic with valid-checksum formats (PAN pattern, Aadhaar Verhoeff) + regex/entropy pre-check in `freeze_data.py` to catch accidental real secrets. No detector-evasion positioning (defender tool).

## Gotchas
- OOM on 16GB unified: batch 4 falls back to batch 2 + grad-accum 2, `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`. Frozen 421M fp32 about 1.6GB + about 30M trainable + adam about 0.5GB is the budget.
- ONNX v1 = parity, expect no speedup (nirnay saw same). Sell MPS+batching, do not claim a gain.
- GGUF via merged fp16 to `llama-quantize` Q4_K_M; precedent `ggml-org/Laya-GGUF` exists, follow that path.
- Hinglish: Roman + Devanagari code-switch; English checkpoint cannot read Devanagari so route to `-multi`, like laya Router does.
