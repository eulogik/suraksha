---
license: apache-2.0
language:
- en
- hi
tags:
- laya
- system-one
- calibrated-decisions
- guardrails
- prompt-injection
- mcp
- hinglish
- edge-ai
- onnx
- gguf
- owasp
- text-classification
pipeline_tag: text-classification
base_model: convaiinnovations/laya
datasets:
- eulogik/suraksha-guard-38k
model-index:
- name: suraksha-450m
  results:
  - task:
      type: text-classification
    dataset:
      name: suraksha guard heldout
      type: eulogik/suraksha-guard-38k
      split: test
    metrics:
    - name: prompt_injection_accuracy
      type: accuracy
      value: 0.981
    - name: tool_risk_accuracy
      type: accuracy
      value: 1.0
    - name: tool_risk_macro_f1
      type: f1
      value: 1.0
    - name: severity_accuracy
      type: accuracy
      value: 0.984
    - name: ece_fitted_worst_head
      type: ece
      value: 0.022
---

# SURAKSHA 450M: calibrated guard decision model (prompt-injection + MCP tool-risk, Hinglish, ONNX/CPU, Jev-compatible)

450M open-weight guard by [Eulogik](https://eulogik.com). One forward pass turns a state plus typed questions into calibrated probabilities: P(prompt-injection), P(jailbreak), P(PII-leak), P(tool-risk). English plus Hinglish plus Hindi. Apache-2.0, self-hosted, $0.

Code and full evals: [github.com/eulogik/suraksha](https://github.com/eulogik/suraksha). Dataset: [eulogik/suraksha-guard-38k](https://huggingface.co/datasets/eulogik/suraksha-guard-38k). GGUF: [eulogik/suraksha-450m-GGUF](https://huggingface.co/eulogik/suraksha-450m-GGUF) (74/74 parity, serve with recent llama-server).

## What is in this repo

- `phase_b.pt`: v2 final guard checkpoint (LoRA r16 + concept bottleneck + head, 7000 steps + 50 RLCD on a Mac mini M4).
- `suraksha-guard.onnx`: CPU artifact, 37/37 parity with torch, 84ms per decision.
- `temperatures.json`: per-bucket fitted temperatures.
- `eval/*.json`: raw heldout results. `assets/reliability.png`: reliability diagram.

Loading needs the suraksha package (custom head): `pip install git+https://github.com/eulogik/suraksha`, then `SurakshaAgent(device="mps", checkpoint_path="phase_b.pt")`. See the GitHub README for byte-exact usage, server, scan CLI, and Ollama.

## Numbers (measured, frozen heldout n=3058)

| Metric | Value |
|---|---|
| Prompt-injection acc | 0.981 |
| Tool-risk acc / macro-F1 | 1.0 / 1.0 |
| Severity acc | 0.984 |
| ECE fitted worst head | 0.022 |
| Brier worst head | 0.060 |
| Hinglish worst slice | 0.926 codeswitch |
| Banking77 retention | 0.391 vs stock 0.378 same setup |
| Latency b1 | 88ms MPS / 84ms ONNX CPU |
| ONNX parity | 37/37 |

Jev figures quoted in docs are third-party published, never measured here. Zero-shot and fine-tuned numbers are never mixed. Trust Card output is a CI-grade credential, not a pentest or legal verdict.

## Limits

512-token en context (1024 multi), head-truncate with `truncated:true`. JSON tool calls only for the risk head. Hinglish trails English. ONNX gives parity, no speedup claimed.

## License

Apache-2.0. Base laya (ConvAI Innovations, Apache-2.0). Banking77 rehearsal rows (PolyAI, CC-BY-4.0).

Keywords: prompt injection detector, mcp guard, tool risk classifier, jailbreak detector, pii leak detector, hinglish guardrails, system one model, jev alternative, on-device classifier, apache 2.0 guard.
