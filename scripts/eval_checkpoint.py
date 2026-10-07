"""eval_checkpoint: guard_heldout + banking77_regression + per-slice metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--suite", default="guard_heldout")
    p.add_argument("--out", default="eval/guard_heldout.json")
    a = p.parse_args()
    Path("eval").mkdir(exist_ok=True)
    # Scaffold: emit schema so fit_temperatures + card tooling have a stable shape.
    payload = {"checkpoint": a.checkpoint, "suite": a.suite, "metrics": {},
               "note": "scaffold: fill with accuracy/macro-F1/Brier/ECE/AUROC + per-slice en/roman/devanagari/codeswitch + latency"}
    Path(a.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {a.out} (scaffold schema)")


if __name__ == "__main__":
    main()
