"""verify_onnx_parity: 37-case torch vs ONNX argmax agreement (gate: 37/37).

37 cases: prompt + tool rows across en/roman/devanagari/codeswitch slices,
plus choice/score/noul coverage. Compares the torch served wrapper against
the ONNX artifact per row. Exit 1 unless 37/37.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

import numpy as np
import torch
from baseline_laya import bucket  # noqa: E402
from suraksha.agent import SurakshaAgent  # noqa: E402
from suraksha.engine import collate_examples, encode_examples  # noqa: E402
from suraksha.guard_data import guard_examples_from_frozen  # noqa: E402

N_CASES = 37


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--torch", required=True)
    p.add_argument("--onnx", required=True)
    p.add_argument("--test-file", default="data/frozen/guard_test.jsonl")
    a = p.parse_args()

    import onnxruntime as ort

    agent = SurakshaAgent(device="cpu", checkpoint_path=a.torch)
    bundle = agent._trained_for_en()
    if bundle is None:
        raise SystemExit(f"no trained payload at {a.torch}")
    model, base, _meta = bundle
    model.eval()

    examples = guard_examples_from_frozen(a.test_file, source="guard_test")
    by_slice: dict[str, list] = {}
    for ex in examples:
        by_slice.setdefault(bucket(ex.state), []).append(ex)
    picked = []
    order = ["en", "roman", "devanagari", "codeswitch"]
    i = 0
    while len(picked) < N_CASES:
        for sl in order:
            pool = by_slice.get(sl, [])
            if pool:
                picked.append(pool[i % len(pool)])
                if len(picked) == N_CASES:
                    break
        i += 1
        if i > N_CASES + 1:
            break

    sess = ort.InferenceSession(a.onnx, providers=["CPUExecutionProvider"])
    in_names = [inp.name for inp in sess.get_inputs()]
    agree = total = 0
    with torch.no_grad():
        for ex in picked:
            items = encode_examples([ex], base.tok, max_bytes=model.max_bytes)
            b = collate_examples(items, base.tok.pad_token_id)
            ref = model({k: v for k, v in b.items()})["logits"].float().cpu().numpy()
            feed = {}
            for n in in_names:
                v = b[n]
                t = v.cpu().numpy() if torch.is_tensor(v) else v
                if n in ("marker_pos", "marker_mask") and t.shape[1] < 4:
                    pad = np.zeros((t.shape[0], 4 - t.shape[1]), dtype=t.dtype)
                    t = np.concatenate([t, pad], axis=1)
                feed[n] = t
            got = sess.run(None, feed)[0]
            w = ref.shape[1]
            total += 1
            if int(ref[0, :w].argmax()) == int(got[0, :w].argmax()):
                agree += 1
    print(f"PARITY {agree}/{total}")
    if agree != N_CASES or total != N_CASES:
        raise SystemExit(f"parity fail: {agree}/{total}, need 37/37")


if __name__ == "__main__":
    main()
