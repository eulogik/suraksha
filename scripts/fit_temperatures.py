"""fit_temperatures: per-(type, n_options) temperature fit (wraps laya.fit_temperatures)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--preds", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    try:
        from laya import fit_temperatures as _fit  # noqa: F401
        print("laya.fit_temperatures available; wiring per-(type,n_options) fit here")
    except ImportError as e:
        raise SystemExit(f"laya not installed: {e}")
    Path(a.out).write_text(json.dumps({"note": "scaffold: temperatures go here"}, indent=2) + "\n")
    print(f"wrote {a.out} (scaffold)")


if __name__ == "__main__":
    main()
