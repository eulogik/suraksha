"""train_rlcd.py: G2, 50 RLCD steps from the G1 checkpoint.

Wraps engine.run_phase_b (proven nirnay Phase B: REINFORCE with group-mean
baseline, log + spherical proper scoring + ranked prob score for severity).
Heavy run: needs --yes.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True, help="G1 checkpoint (phase_a.pt style)")
    p.add_argument("--steps", type=int, default=50)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--device", default="mps")
    p.add_argument("--data", default="data/frozen")
    p.add_argument("--out-dir", default="checkpoints/guard_rlcd")
    p.add_argument("--yes", action="store_true")
    a = p.parse_args()
    if not Path(a.ckpt).exists():
        raise SystemExit(f"ckpt missing: {a.ckpt}")
    if not a.yes:
        raise SystemExit(f"heavy run: {a.steps} RLCD steps on {a.device}. Re-run with --yes to start.")
    from .engine import run_phase_b

    out = Path(a.out_dir)
    result = run_phase_b(
        steps=a.steps,
        batch_size=4,
        guard_dir=a.data,
        out_dir=a.out_dir,
        lora_rank=16,
        seed=a.seed,
        device=a.device,
        phase_a_path=a.ckpt,
    )
    h = result["history"]
    print(f"G2_OK steps={len(h)} reward0={h[0]['reward_mean']:.4f} ckpt={result['ckpt']}")


if __name__ == "__main__":
    main()
