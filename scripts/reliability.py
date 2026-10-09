"""reliability.py: reliability diagram PNG from heldout rows (assets/reliability.png).

Bins max-probability confidence vs accuracy per question type. Raw data for
the card; ECE numbers come from eval_checkpoint.py, never from the picture.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from suraksha.agent import SurakshaAgent  # noqa: E402


def collect(agent: SurakshaAgent, rows: list[dict], qid: str, keys: list[str], gold_key: str):
    conf, correct = [], []
    for r in rows:
        exp = r.get("expected", {})
        if gold_key not in exp:
            continue
        try:
            out = agent.system_one(r["state"], r.get("questions") or {})
        except Exception:  # noqa: BLE001
            continue
        ans = out.get("answers", {}).get(qid)
        if ans is None:
            continue
        if qid == "prompt_injection":
            p = float(ans["noul"])
            pv = np.array([1.0 - p, p])
            t = int(bool(exp[gold_key]))
        elif qid == "tool_risk":
            pv = np.array([float(ans["probabilities"][k]) for k in keys])
            t = keys.index(exp[gold_key])
        else:
            pv = np.array([float(ans["probabilities"][str(i)]) for i in range(3)])
            t = int(exp[gold_key])
        conf.append(float(pv.max()))
        correct.append(1.0 if int(pv.argmax()) == t else 0.0)
    return np.array(conf), np.array(correct)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--test-file", default="data/frozen/guard_test.jsonl")
    p.add_argument("--out", default="assets/reliability.png")
    p.add_argument("--device", default="mps")
    p.add_argument("--limit", type=int, default=1000)
    a = p.parse_args()
    rows = [json.loads(l) for l in open(a.test_file, encoding="utf-8")][:a.limit]
    agent = SurakshaAgent(device=a.device, checkpoint_path=a.checkpoint)
    groups = [
        ("prompt_injection", ["false", "true"], "prompt_injection"),
        ("tool_risk", ["safe", "write", "privileged", "exfiltrate"], "tool_risk"),
        ("severity", ["0", "1", "2"], "severity"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (qid, keys, gold) in zip(axes, groups):
        conf, correct = collect(agent, rows, qid, keys, gold)
        edges = np.linspace(0, 1, 11)
        xs, ys = [], []
        for i in range(10):
            m = (conf > edges[i]) & (conf <= edges[i + 1])
            if m.sum() == 0:
                continue
            xs.append(float(conf[m].mean()))
            ys.append(float(correct[m].mean()))
        ax.plot([0, 1], [0, 1], "k--", lw=1)
        ax.plot(xs, ys, "o-")
        ax.set_title(f"{qid} (n={len(conf)})")
        ax.set_xlabel("confidence")
        ax.set_ylabel("accuracy")
    fig.suptitle(f"reliability: {a.checkpoint or 'stock-laya-zero-shot'}")
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=100)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
