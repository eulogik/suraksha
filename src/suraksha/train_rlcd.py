"""train_rlcd.py: 50 RLCD steps (REINFORCE group-mean baseline)."""
from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--steps", type=int, default=50)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    print(f"RLCD: ckpt={a.ckpt} steps={a.steps} seed={a.seed}")
    print("reward = log + spherical proper scoring + ranked prob score for severity; TD(1.0) over prefix slices")
    raise SystemExit("scaffold v0.1: wire laya proper_reward + td_lambda_targets here")


if __name__ == "__main__":
    main()
