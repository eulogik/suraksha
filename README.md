# SURAKSHA 450M

Calibrated System-1 guard decision model for prompts + MCP tool calls. See `SURAKSHA_IMPLEMENTATION_PLAN.md` (build spec), `AGENTS.md` (agent instructions), `MEMORY.md` (living log).

```bash
pip install -e .
python -c "import torch; print(torch.backends.mps.is_available())"
suraksha-serve --port 8000
```

See `USAGE.md` for byte-exact prompt + curl + Ollama.
