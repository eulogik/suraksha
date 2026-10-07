"""merge_lora: fold custom LoRA adapters into base linears, save fp16 encoder.

GGUF path: merged fp16 dir -> llama-quantize Q4_K_M (see AGENTS.md).
Our LoRA is custom (LoRALinear), not peft, so folding is explicit:
W_new = W_base + scaling * (B @ A).
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import torch
import torch.nn as nn


def _fold(module: nn.Module) -> int:
    from suraksha.lora import LoRALinear

    folded = 0
    for name, child in list(module.named_children()):
        if isinstance(child, LoRALinear):
            with torch.no_grad():
                delta = (child.lora_B @ child.lora_A) * child.scaling
                merged = nn.Linear(child.base.in_features, child.base.out_features,
                                   bias=child.base.bias is not None)
                merged.weight.copy_(child.base.weight + delta.to(child.base.weight.dtype))
                if child.base.bias is not None:
                    merged.bias.copy_(child.base.bias)
            setattr(module, name, merged)
            folded += 1
        else:
            folded += _fold(child)
    return folded


def main() -> None:
    import sys
    sys.path.insert(0, "src")
    from suraksha.agent import SurakshaAgent

    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="cpu")
    a = p.parse_args()
    agent = SurakshaAgent(device=a.device, checkpoint_path=a.ckpt)
    bundle = agent._trained_for_en()
    if bundle is None:
        raise SystemExit(f"no trained payload at {a.ckpt}")
    model, base, _meta = bundle
    n = _fold(model.base.encoder)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({k: v.cpu().to(torch.float16) for k, v in model.base.encoder.state_dict().items()},
               out / "encoder_fp16.pt")
    (out / "merge_report.json").write_text(
        __import__("json").dumps({"folded_linears": n, "ckpt": a.ckpt}, indent=2) + "\n")
    print(f"MERGE_OK folded={n} -> {out}/encoder_fp16.pt")
    print("next: llama-quantize fp16/suraksha-450m-f16.gguf gguf/suraksha-450m-Q4_K_M.gguf Q4_K_M")


if __name__ == "__main__":
    main()
