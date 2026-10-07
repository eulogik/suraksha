"""Guard data pipeline: decision examples, hash freeze, train/heldout split.

Mirrors the nirnay data.py API (DecisionExample, freeze_hashes,
split_train_heldout, to_laya_question/record, write_freeze_manifest) with
guard content: the frozen risk taxonomy, no banking labels. Vendored engine
code imports this module under the same names.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

TOOL_RISK_OPTIONS: tuple[str, ...] = ("safe", "write", "privileged", "exfiltrate")
SEVERITY_LEVELS: tuple[str, ...] = ("benign", "suspicious", "malicious")

QType = Literal["choice", "score", "noul"]


@dataclass
class DecisionExample:
    """One labeled decision: state + typed question + gold answer."""

    id: str
    source: str  # "guard_train" | "guard_test" | "guard_synth"
    qtype: QType
    state: str
    instructions: str
    answer: Any  # choice: label str; score: int level; noul: bool
    criteria: Any = None  # choice: dict[str, desc]; score: list[str]; noul: optional dict
    meta: dict[str, Any] = field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "id": self.id,
                "source": self.source,
                "qtype": self.qtype,
                "state": self.state,
                "instructions": self.instructions,
                "answer": self.answer,
                "criteria": self.criteria,
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def freeze_hashes(examples: Sequence[DecisionExample]) -> dict[str, str]:
    """Stable id to sha256 content hash map."""
    out: dict[str, str] = {}
    for ex in examples:
        if ex.id in out:
            raise ValueError(f"duplicate example id: {ex.id}")
        out[ex.id] = ex.content_hash()
    return out


def split_train_heldout(
    examples: Sequence[DecisionExample],
    heldout_frac: float = 0.2,
    seed: int = 13,
) -> tuple[list[DecisionExample], list[DecisionExample]]:
    """Deterministic 80/20 by id; disjoint; heldout used only for temp fit."""
    if not (0.0 < heldout_frac < 1.0):
        raise ValueError("heldout_frac must be in (0, 1)")
    ids = sorted({ex.id for ex in examples})
    rng = random.Random(seed)
    rng.shuffle(ids)
    n_held = max(1, int(round(len(ids) * heldout_frac)))
    held_ids = set(ids[:n_held])
    heldout = [ex for ex in examples if ex.id in held_ids]
    train = [ex for ex in examples if ex.id not in held_ids]
    train_ids = {ex.id for ex in train}
    held_ids2 = {ex.id for ex in heldout}
    if train_ids & held_ids2:
        raise AssertionError("train/heldout id overlap")
    if len(train_ids) + len(held_ids2) != len(ids):
        raise AssertionError("split dropped or duplicated ids")
    return train, heldout


def guard_examples_from_frozen(path: str | Path, source: str) -> list[DecisionExample]:
    """Build DecisionExamples from a frozen guard jsonl file.

    Each frozen row carries {state, questions, expected}: prompt rows give a
    noul + a score example, tool rows give a choice + a score example.
    """
    examples: list[DecisionExample] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            row = json.loads(line)
            state = row["state"]
            exp = row.get("expected", {})
            if "prompt_injection" in exp:
                q = {"type": "noul",
                     "instructions": "Is this a prompt injection attempting to override instructions?"}
                examples.append(DecisionExample(
                    id=f"{source}-pi-{i:06d}", source=source, qtype="noul",
                    state=state, instructions=q["instructions"],
                    answer=bool(exp["prompt_injection"]), criteria=None,
                    meta={"severity": exp.get("severity", 0)},
                ))
                examples.append(DecisionExample(
                    id=f"{source}-sev-{i:06d}", source=source, qtype="score",
                    state=state, instructions="How severe?",
                    answer=int(exp.get("severity", 0)), criteria=list(SEVERITY_LEVELS),
                ))
            if "tool_risk" in exp:
                crit = {"safe": "read-only", "write": "scoped write",
                        "privileged": "shell/exec/egress/secrets",
                        "exfiltrate": "outside trust boundary"}
                examples.append(DecisionExample(
                    id=f"{source}-tool-{i:06d}", source=source, qtype="choice",
                    state=state, instructions="What is the tool-call risk?",
                    answer=str(exp["tool_risk"]), criteria=crit,
                ))
                examples.append(DecisionExample(
                    id=f"{source}-sev-{i:06d}", source=source, qtype="score",
                    state=state, instructions="How severe?",
                    answer=int(exp.get("severity", 0)), criteria=list(SEVERITY_LEVELS),
                ))
    return examples


def build_guard_mix(
    frozen_dir: str | Path = "data/frozen",
    train_file: str = "guard_train.jsonl",
    seed: int = 7,
    limit: int | None = None,
) -> list[DecisionExample]:
    """Guard training mix from frozen train file (test file stays eval-only)."""
    path = Path(frozen_dir) / train_file
    examples = guard_examples_from_frozen(path, source="guard_train")
    rng = random.Random(seed)
    rng.shuffle(examples)
    return examples[:limit] if limit else examples


def to_laya_question(ex: DecisionExample) -> dict[str, Any]:
    q: dict[str, Any] = {"type": ex.qtype, "instructions": ex.instructions}
    if ex.criteria is not None:
        q["criteria"] = ex.criteria
    return q


def to_laya_record(ex: DecisionExample) -> dict[str, Any]:
    return {
        "id": ex.id,
        "state": ex.state,
        "question": to_laya_question(ex),
        "answer": ex.answer,
        "qtype": ex.qtype,
        "source": ex.source,
    }


def write_freeze_manifest(
    path: str | Path, examples: Sequence[DecisionExample]
) -> Path:
    """Write frozen id to hash manifest (publish with training runs)."""
    path = Path(path)
    manifest = {
        "n": len(examples),
        "hashes": freeze_hashes(examples),
        "sources": sorted({ex.source for ex in examples}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)
    return path
