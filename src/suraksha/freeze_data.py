"""freeze_data: normalize + dedupe + hash-freeze + license gate.

Emits SHA256SUMS + LICENSES.json. Fails on unknown license (AGENTS.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ALLOW = {"Apache-2.0", "MIT", "BSD", "CC0", "CC-BY-4.0", "Apache-2.0-Ours", "Ours-Apache-2.0"}
DENY_SUBSTR = ("NC", "SA", "GPL", "NonCommercial", "Non-Commercial")

# source filename hint -> license (explicit allowlist; extend deliberately)
LICENSE_HINTS = {
    "en_inject": "Apache-2.0-Ours",
    "guard_hinglish": "Ours-Apache-2.0",
    "guard_train": "Ours-Apache-2.0",
    "guard_test": "Ours-Apache-2.0",
    "jailbreak": "MIT",
    "pii": "Ours-Apache-2.0",
    "tool": "Ours-Apache-2.0",
    "banking77": "CC-BY-4.0",
}


def license_for(path: Path) -> str:
    name = path.name.lower()
    for hint, lic in LICENSE_HINTS.items():
        if hint in name:
            return lic
    return "UNKNOWN"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    inp, out = Path(a.inp), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    licenses: dict[str, str] = {}
    total = kept = 0
    for f in sorted(inp.rglob("*.jsonl")):
        lic = license_for(f)
        if lic == "UNKNOWN" or any(d in lic for d in DENY_SUBSTR):
            raise SystemExit(f"LICENSE FAIL: {f} -> {lic}; add explicit allowlist entry or remove file")
        if lic not in ALLOW:
            raise SystemExit(f"LICENSE FAIL: {f} -> {lic} not in allowlist {sorted(ALLOW)}")
        licenses[f.name] = lic
        dest = out / f.name
        with open(f, encoding="utf-8") as fh, open(dest, "w", encoding="utf-8") as oh:
            for line in fh:
                total += 1
                norm = line.strip()
                h = hashlib.sha256(norm.encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                oh.write(norm + "\n")
                kept += 1
    sums = []
    for f in sorted(out.glob("*.jsonl")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        sums.append(f"{h}  {f.name}")
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    (out / "LICENSES.json").write_text(json.dumps(licenses, indent=2, sort_keys=True) + "\n")
    print(f"freeze: {kept}/{total} kept, {len(sums)} files -> {out}/SHA256SUMS + LICENSES.json")


if __name__ == "__main__":
    main()
