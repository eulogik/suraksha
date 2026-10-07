# SURAKSHA 450M: calibrated guard decision model (prompt-injection + MCP tool-risk, Hinglish, ONNX/CPU, Jev-compatible)

450M open-weight guard. One forward pass turns a state plus typed questions into calibrated probabilities: P(prompt-injection), P(jailbreak), P(PII-leak), P(tool-risk). English + Hinglish + Hindi. Apache-2.0. Self-hosted, $0.

`pip install git+https://github.com/eulogik/suraksha` then see USAGE.md. Ollama: Modelfile in repo.

## Numbers (measured here; PENDING until G2 + temp fit land)

| Metric | Value | Setup |
|---|---|---|
| Guard acc heldout n=3058 | PENDING (gate >= 0.85) | fine-tuned, this repo |
| Tool macro-F1 | PENDING (gate >= 0.83) | fine-tuned, this repo |
| ECE raw / fitted | PENDING / PENDING (gates <= 0.10 / <= 0.05) | fine-tuned, this repo |
| Brier | PENDING (gate <= 0.22) | fine-tuned, this repo |
| Banking77 (no forgetting) | PENDING (gate >= 0.86) | fine-tuned, this repo |
| Hinglish slice | PENDING (gate mean >= 0.68, each slice >= 0.60) | fine-tuned, this repo |
| Latency b1 | PENDING (gates <= 220ms MPS / <= 380ms CPU) | measured |
| ONNX parity | PENDING (gate 37/37) | measured |

Jev figures quoted anywhere are third-party published, never measured here. Zero-shot and fine-tuned numbers are never mixed. Trust Card is a CI-grade credential, not a pentest or legal verdict.

## Limits

512-token en context (1024 multi), head-truncate with `truncated:true`. JSON tool calls only for tool-risk. Hinglish weaker than English. ONNX parity, no speedup claimed.

## License

Apache-2.0. Base laya (ConvAI Innovations, Apache-2.0). Synthetic guard data ours (Apache-2.0).

Keywords: prompt injection detector, mcp guard, tool risk classifier, jailbreak detector, pii leak detector, hinglish guardrails, system one model, jev alternative, on-device classifier, apache 2.0 guard.
