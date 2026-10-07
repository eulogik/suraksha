"""fit_temperatures: per-(type, n_options) temperature fit on frozen train rows.

Runs the agent, groups log-probs by temp bucket, fits one scalar T per
bucket (NLL grid fit in temps.fit_temperature), writes JSON for
SurakshaAgent(calibration_path=...). Refit from scratch; never hand edit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import numpy as np
from suraksha.agent import SurakshaAgent  # noqa: E402
from suraksha.temps import fit_temperature, temp_bucket  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--test-file", default="data/frozen/guard_train.jsonl")
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="mps")
    p.add_argument("--limit", type=int, default=2000)
    a = p.parse_args()

    rows = [json.loads(l) for l in open(a.test_file, encoding="utf-8")][:a.limit]
    agent = SurakshaAgent(device=a.device, checkpoint_path=a.checkpoint)
    buckets: dict[str, list[tuple[np.ndarray, int]]] = {}
    for r in rows:
        try:
            out = agent.system_one(r["state"], r.get("questions") or {})
        except Exception:  # noqa: BLE001
            continue
        ans, exp = out.get("answers", {}), r.get("expected", {})
        if "prompt_injection" in exp and "prompt_injection" in ans:
            p_ = float(ans["prompt_injection"]["noul"])
            buckets.setdefault(temp_bucket("noul", 2), []).append(
                (np.array([1.0 - p_, p_]), int(bool(exp["prompt_injection"]))))
        if "tool_risk" in exp and "tool_risk" in ans:
            keys = ["safe", "write", "privileged", "exfiltrate"]
            pv = np.array([float(ans["tool_risk"]["probabilities"][k]) for k in keys])
            buckets.setdefault(temp_bucket("choice", 4), []).append((pv, keys.index(exp["tool_risk"])))
        if "severity" in exp and "severity" in ans:
            pv = np.array([float(ans["severity"]["probabilities"][str(i)]) for i in range(3)])
            buckets.setdefault(temp_bucket("score", 3), []).append((pv, int(exp["severity"])))

    temps = {}
    for bucket_name, stacked in buckets.items():
        probs = np.stack([s[0] for s in stacked])
        tgts = np.array([s[1] for s in stacked])
        onehot = np.zeros_like(probs)
        onehot[np.arange(len(tgts)), tgts] = 1.0
        log_p = np.log(np.clip(probs, 1e-12, 1.0))
        temps[bucket_name] = {"temperature": float(fit_temperature(log_p, onehot)), "n": len(stacked)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(temps, indent=2, sort_keys=True) + "\n")
    print(json.dumps(temps, indent=2))


if __name__ == "__main__":
    main()
