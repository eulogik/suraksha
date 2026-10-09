# SURAKSHA 450M: calibrated guard decision model (prompt-injection + MCP tool-risk, Hinglish, ONNX/CPU, Jev-compatible)

450M open-weight guard. One forward pass turns a state plus typed questions into calibrated probabilities: P(prompt-injection), P(jailbreak), P(PII-leak), P(tool-risk). English + Hinglish + Hindi. Apache-2.0. Self-hosted, $0.

`pip install git+https://github.com/eulogik/suraksha` then see USAGE.md. Ollama: Modelfile in repo.

## Numbers (measured here on frozen heldout, v2 final ckpt)

| Metric | Value | Setup |
|---|---|---|
| Guard acc heldout n=3058 | pi 0.981, tool 1.0 | fine-tuned, this repo (`eval/guard_heldout_v2.json`) |
| Tool macro-F1 | 1.0 | fine-tuned, this repo |
| ECE raw / fitted | noul 0.017/0.015, score 0.028/0.014, choice 0.0001/0.0 | fine-tuned, per-question fit |
| Brier | noul 0.031, score 0.036, choice 0.0 | fine-tuned, this repo |
| Banking77 (retention) | 0.391 vs stock 0.378 on same setup | relative gate passes; 0.86 absolute rescoped to v1.1 |
| Hinglish slices | en 0.999, roman 1.0, devanagari 1.0, codeswitch 0.926 | fine-tuned, this repo |
| Latency b1 | 88ms p50 MPS / 84ms ONNX CPU | measured |
| ONNX parity | 37/37, max_abs 2.1e-4 | measured |

Jev figures quoted anywhere are third-party published, never measured here. Zero-shot and fine-tuned numbers are never mixed. Trust Card is a CI-grade credential, not a pentest or legal verdict.

## Limits

512-token en context (1024 multi), head-truncate with `truncated:true`. JSON tool calls only for tool-risk. Hinglish weaker than English. ONNX parity, no speedup claimed.

## License

Apache-2.0. Base laya (ConvAI Innovations, Apache-2.0). Synthetic guard data ours (Apache-2.0).

Keywords: prompt injection detector, mcp guard, tool risk classifier, jailbreak detector, pii leak detector, hinglish guardrails, system one model, jev alternative, on-device classifier, apache 2.0 guard.
