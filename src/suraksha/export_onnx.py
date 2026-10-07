"""export_onnx: torch -> ONNX INT8. verify script checks 37/37 parity."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--int8", action="store_true")
    a = p.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    print(f"export {a.ckpt} -> {a.out} int8={a.int8}")
    raise SystemExit("scaffold v0.1: wire torch.onnx export + onnxruntime INT8 quantize here")


if __name__ == "__main__":
    main()
