---
license: apache-2.0
language:
- en
- hi
tags:
- guardrails
- prompt-injection
- jailbreak
- pii
- mcp
- hinglish
- synthetic
task_categories:
- text-classification
---

# suraksha-guard-38k: frozen guard training data (English + Hinglish + Hindi)

Guard mix behind [SURAKSHA 450M](https://huggingface.co/eulogik/suraksha-450m) by [Eulogik](https://eulogik.com). Template-generated with ground truth by construction: tool-risk labels come from the generated tool JSON, injection labels come from the template. No LLM-judge labeling. Code: [github.com/eulogik/suraksha](https://github.com/eulogik/suraksha).

## Files

- `guard_train.jsonl`: 24,252 unique rows (deduplicated from 38,000 generated).
- `guard_test.jsonl`: 3,058 unique rows, disjoint templates, unseen tools, unseen exfil domains.
- `SHA256SUMS`, `LICENSES.json`: freeze bundle pinned before training.

Row shape: `{state, questions, expected, labels, split}`. Prompt rows carry `prompt_injection` (bool) plus `severity` (0-2). Tool rows carry `tool_risk` (safe/write/privileged/exfiltrate) plus `severity`.

## Coverage

English plus Roman Hinglish plus Devanagari plus code-switch. PII is synthetic only (faker-style PAN/Aadhaar/phone/keys, plain plus split plus redacted plus base64). No verbatim real PII. Test tools (shell_exec, db_query, send_email, upload_file) never appear in train. Test domains never appear in train.

## License

Apache-2.0 (ours, synthetic). Banking77 rehearsal rows used in training are PolyAI CC-BY-4.0 and live outside this dataset.

Keywords: guardrails dataset, prompt injection data, hinglish dataset, mcp tool risk data, synthetic security data.
