"""suraksha scan: OpenTrustBench static card + learned Suraksha screen.

Static side shells out to the installed `opentrustbench` CLI (no reimpl).
Learned side scores text-like files with SurakshaAgent when SURAKSHA_CKPT
is set; without a checkpoint it reports static-only honestly.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {".py", ".js", ".ts", ".json", ".md", ".txt", ".yml", ".yaml", ".sh"}


def static_scan(target: str) -> dict:
    binary = shutil.which("opentrustbench")
    if binary is None:
        return {"available": False, "note": "opentrustbench CLI not installed"}
    proc = subprocess.run([binary, "scan", target], capture_output=True, text=True, timeout=300)
    return {"available": True, "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-500:]}


def learned_screen(target: str, ckpt: str | None, limit: int = 50) -> dict:
    if ckpt is None:
        return {"ran": False, "note": "SURAKSHA_CKPT not set; static-only"}
    import sys
    sys.path.insert(0, "src")
    from suraksha.agent import SURAKSHA_QUESTIONS, SurakshaAgent

    agent = SurakshaAgent(device=os.environ.get("SURAKSHA_DEVICE", "mps"), checkpoint_path=ckpt)
    files = [p for p in Path(target).rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES][:limit]
    worst = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            continue
        try:
            out = agent.system_one(text, {"prompt_injection": SURAKSHA_QUESTIONS["prompt_injection"],
                                          "severity": SURAKSHA_QUESTIONS["severity"]})
        except Exception:
            continue
        pi = out["answers"]["prompt_injection"]["noul"]
        worst.append({"file": str(p), "p_injection": pi,
                      "severity": out["answers"]["severity"]["score"]})
    worst.sort(key=lambda r: r["p_injection"], reverse=True)
    return {"ran": True, "n_files": len(files), "top": worst[:10]}


def main() -> None:
    p = argparse.ArgumentParser(prog="suraksha scan")
    p.add_argument("target", nargs="?", default=".")
    p.add_argument("--fail-on", default="high")
    p.add_argument("--ckpt", default=os.environ.get("SURAKSHA_CKPT"))
    a = p.parse_args()
    static = static_scan(a.target)
    learned = learned_screen(a.target, a.ckpt) if a.ckpt else {"ran": False, "note": "static-only"}
    print(json.dumps({"target": a.target, "static": static, "learned": learned,
                      "fail_on": a.fail_on}, indent=2))
    if static.get("available") and static.get("returncode", 0) != 0:
        raise SystemExit(static["returncode"])


if __name__ == "__main__":
    main()
