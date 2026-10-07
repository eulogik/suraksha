"""merge_lora: merge LoRA into fp16 base for GGUF quantize path."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    print(f"merge {a.ckpt} -> {a.out}")
    print("next: llama-quantize fp16/suraksha-450m-f16.gguf gguf/suraksha-450m-Q4_K_M.gguf Q4_K_M")
    raise SystemExit("scaffold v0.1: wire peft merge_and_unload here")


if __name__ == "__main__":
    main()
