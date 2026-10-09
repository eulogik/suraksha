# I fine-tuned Laya into a guard model on a Mac mini (SURAKSHA 450M)

Chat LLMs are saturated. The useful corner right now is small decision models: fast, calibrated, offline. I took ConvAI's Laya 421M and turned it into a guard that scores prompt-injection, jailbreak, PII-leak, and MCP tool-call risk in one forward pass, in English plus Hinglish plus Hindi. Cost: $0, one Mac mini M4.

## What it does

You hand it a state plus typed questions. It returns a probability per risk, calibrated, in about 88ms. For MCP builders the pattern is one line: if P(tool-risk) crosses your threshold, escalate instead of executing.

## Numbers, all measured

Frozen heldout, 3058 cases, disjoint templates and unseen tools: injection 0.98, tool-risk 1.0, severity 0.98, worst fitted ECE 0.022. The real story is severity (0.76 stock to 0.98) and calibration (0.13 to 0.02). Banking77 retention 0.39 vs stock 0.38 on the same setup. ONNX parity 37/37.

## What broke along the way

Two box kills ate training runs (checkpoints survived). The VQ bottleneck thinned late in v1, so I shipped the healthy best checkpoint instead. Banking rehearsal mixed 4-wide and 77-wide batches and stalled the backend until I bucketed batches by width. All of it is in the repo MEMORY.md, including the negative bits.

## Try it

Model: huggingface.co/eulogik/suraksha-450m. Code: github.com/eulogik/suraksha. `pip install git+https://github.com/eulogik/suraksha` and you get the agent, a Jev-compatible server, and a scan CLI that pairs the OpenTrustBench static card with the learned score.

Built by Eulogik (eulogik.com). Apache-2.0.
