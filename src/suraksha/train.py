"""train.py: G0/G1 guard fine-tune on the vendored nirnay engine.

Schedule (configs/g1_guard.json): G0 1000 steps warmup, then G1 resume to
7000 total. Same proven stack as nirnay Phase A (LoRA r16 Q/V + concept
bottleneck + deep supervision + c2f cheap path for choice-4, 3-group
optimizer, probe every 250 with best retention and collapse abort).

Note: warmup trains the full stack jointly (nirnay proved this stable);
a LoRA-only first stage is not in the engine, so G0 is a short full-stack
warmup with a probe gate, not a frozen-head stage.

--dry-run verifies config + freeze bundle without touching the M4.
Full runs are heavy: this CLI prints an estimate and needs confirmation
unless --yes is passed.
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
    p.add_argument("--phase", choices=("g0", "g1"), default="g0")
    p.add_argument("--out-dir", default="checkpoints/guard")
    p.add_argument("--yes", action="store_true", help="skip heavy-run confirmation")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--guard-limit", type=int, default=None)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    frozen = Path(a.data)
    sums = frozen / "SHA256SUMS"
    lics = frozen / "LICENSES.json"
    if not sums.exists() or not lics.exists():
        raise SystemExit(f"refusing to train: {sums} or {lics} missing; run freeze_data.py first")
    g0, g1_total = int(cfg.get("g0_steps", 1000)), int(cfg.get("g1_steps", 6000)) + int(cfg.get("g0_steps", 1000))
    steps = g0 if a.phase == "g0" else g1_total
    print(f"config: {a.config} seed={a.seed} device={a.device} phase={a.phase} steps={steps}")
    print(f"lora r={cfg['lora']['r']} batch={cfg['batch_size']} "
          f"lr rest(LoRA+head)={cfg['optimizer_groups']['head']} "
          f"pretrained={cfg['optimizer_groups']['lora']} bottleneck={cfg['optimizer_groups']['bottleneck']}")
    print(f"freeze: {sums.read_text().strip().splitlines()[0][:16]}... licenses={lics.read_text().strip()[:100]}...")
    if a.dry_run:
        print("dry-run OK (no steps taken)")
        return
    if not a.yes:
        raise SystemExit(f"heavy run: ~{steps} steps on {a.device}. Re-run with --yes to start.")
    from .engine import PhaseACollapse, run_phase_a

    try:
        result = run_phase_a(
            steps=steps,
            batch_size=int(cfg.get("batch_size", 4)),
            guard_dir=a.data,
            guard_limit=a.guard_limit,
            out_dir=a.out_dir,
            lora_rank=int(cfg["lora"]["r"]),
            lr=float(cfg["optimizer_groups"]["head"]),
            seed=a.seed,
            device=a.device,
            checkpoint_every=int(cfg.get("checkpoint_every", 500)),
            resume=(a.phase == "g1"),
            overwrite=a.overwrite,
            probe_every=int(cfg.get("probe_every", 250)),
            pretrained_lr=float(cfg["optimizer_groups"]["lora"]),
            concepts_lr=float(cfg["optimizer_groups"]["bottleneck"]),
        )
    except PhaseACollapse as exc:
        raise SystemExit(f"GUARD_ABORT {exc}")
    h = result["history"]
    print(f"GUARD_{a.phase.upper()}_OK steps={len(h)} loss0={h[0]['loss']:.4f} "
          f"lossN={h[-1]['loss']:.4f} ckpt={result['ckpt']}")


if __name__ == "__main__":
    main()
