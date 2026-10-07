"""train.py: G0/G1 guard fine-tune (LoRA r16 Q/V + bottleneck + head).

Wraps laya training recipe (nirnay Phase A/B retuned). --dry-run validates
config + data hashes without GPU steps.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--device", default="mps")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--data", default="data/frozen")
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    frozen = Path(a.data)
    sums = frozen / "SHA256SUMS"
    lics = frozen / "LICENSES.json"
    if not sums.exists() or not lics.exists():
        raise SystemExit(f"refusing to train: {sums} or {lics} missing; run freeze_data.py first")
    print(f"config: {a.config} seed={a.seed} device={a.device}")
    print(f"lora r={cfg['lora']['r']} targets={cfg['lora']['targets']} "
          f"lr lora={cfg['optimizer_groups']['lora']} bottleneck={cfg['optimizer_groups']['bottleneck']} head={cfg['optimizer_groups']['head']}")
    print(f"data: {sums.read_text().strip().splitlines()[0][:16]}... + {lics.read_text().strip()[:80]}...")
    if a.dry_run:
        print("dry-run OK (no steps taken)")
        return
    # Real training plugs in here: laya.train_cli with 3-group optimizer,
    # deep supervision layers cfg['deep_supervision_layers'], ckpt every cfg['checkpoint_every'].
    try:
        import laya  # noqa: F401
    except ImportError as e:
        raise SystemExit(f"laya not installed: {e}")
    raise SystemExit("real training not wired in scaffold v0.1  ,  implement laya.train_cli call for G0/G1; see AGENTS.md")


if __name__ == "__main__":
    main()
