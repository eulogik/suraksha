"""Day-1 baseline: stock laya zero shot on guard rows, per slice + latency.

Writes eval/baseline_laya.json. No training. Proves the gap before G0.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from suraksha.agent import SURAKSHA_QUESTIONS, _has_devanagari  # noqa: E402
from suraksha.data_synth_guard import synth  # noqa: E402

HINGLISH_ROMAN_BITS = ["karo", "bhejo", "kripya", "ko ", "hai", "please confirm karo"]


def bucket(state: str) -> str:
    if _has_devanagari(state):
        return "devanagari"
    low = state.lower()
    if any(b in low for b in HINGLISH_ROMAN_BITS):
        return "roman" if "{" not in state else "codeswitch"
    if any(k in low for k in ["ignore previous", "exfiltrate", "translate then follow", "base64"]):
        return "en"
    if state.strip().startswith("{"):
        return "en"
    return "en"


def pred_noul(ans: dict) -> bool:
    return float(ans.get("noul", 0.0)) > 0.5


def pred_choice(ans: dict) -> str:
    probs = ans.get("probabilities") or {}
    if probs:
        return max(probs, key=lambda k: probs[k])
    return str(ans.get("answer", ans.get("choice", "")))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=250, help="synth n (each n gives 2 rows)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--limit", type=int, default=0, help="cap rows, 0 = all")
    p.add_argument("--out", default="eval/baseline_laya.json")
    a = p.parse_args()

    rows = synth(a.n, a.seed)
    if a.limit:
        rows = rows[:a.limit]

    from suraksha.agent import SurakshaAgent

    agent = SurakshaAgent(device="mps")
    per_slice: dict[str, dict[str, int]] = {}
    pi_correct = pi_total = tool_correct = tool_total = 0
    lat: list[float] = []
    routed_multi = routed_en = 0

    for r in rows:
        state = r["state"]
        sl = bucket(state)
        d = per_slice.setdefault(sl, {"n": 0, "pi_ok": 0, "pi_n": 0, "tool_ok": 0, "tool_n": 0})
        d["n"] += 1
        t0 = time.perf_counter()
        try:
            out = agent.system_one(state, SURAKSHA_QUESTIONS)
        except Exception as e:  # noqa: BLE001 - baseline must not die on one row
            print(f"row failed ({sl}): {e}")
            continue
        dt = (time.perf_counter() - t0) * 1000
        lat.append(dt)
        if out.get("routing", {}).get("model") == "suraksha-multi":
            routed_multi += 1
        else:
            routed_en += 1
        labels = r.get("labels", {})
        ans = out.get("answers", {})
        if "prompt_injection" in labels and "prompt_injection" in ans:
            ok = pred_noul(ans["prompt_injection"]) == bool(labels["prompt_injection"])
            d["pi_n"] += 1
            pi_total += 1
            if ok:
                d["pi_ok"] += 1
                pi_correct += 1
        if "tool_risk" in labels and "tool_risk" in ans:
            ok = pred_choice(ans["tool_risk"]) == labels["tool_risk"]
            d["tool_n"] += 1
            tool_total += 1
            if ok:
                d["tool_ok"] += 1
                tool_correct += 1

    lat_sorted = sorted(lat)
    payload = {
        "model": "stock-laya-zero-shot-via-SurakshaAgent",
        "n_rows": len(rows),
        "seed": a.seed,
        "prompt_injection_acc": (pi_correct / pi_total) if pi_total else None,
        "tool_risk_acc": (tool_correct / tool_total) if tool_total else None,
        "per_slice": {
            k: {
                "n": v["n"],
                "pi_acc": (v["pi_ok"] / v["pi_n"]) if v["pi_n"] else None,
                "tool_acc": (v["tool_ok"] / v["tool_n"]) if v["tool_n"] else None,
            }
            for k, v in per_slice.items()
        },
        "latency_ms": {
            "n": len(lat_sorted),
            "p50": lat_sorted[len(lat_sorted) // 2] if lat_sorted else None,
            "p95": lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else None,
        },
        "routing": {"suraksha-en": routed_en, "suraksha-multi": routed_multi},
        "note": "zero shot, third party base, never mix with fine tuned numbers",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
