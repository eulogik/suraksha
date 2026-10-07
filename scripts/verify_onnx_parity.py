"""verify_onnx_parity: torch vs ONNX must be 37/37."""
from __future__ import annotations

import argparse


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--torch", required=True)
    p.add_argument("--onnx", required=True)
    a = p.parse_args()
    print(f"parity check torch={a.torch} onnx={a.onnx}")
    raise SystemExit("scaffold v0.1: run 37-case parity suite here; exit nonzero unless 37/37")


if __name__ == "__main__":
    main()
