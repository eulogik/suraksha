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

BANKING77_LABELS: tuple[str, ...] = (
    "activate_my_card", "age_limit", "apple_pay_or_google_pay", "atm_support",
    "automatic_top_up", "balance_not_updated_after_bank_transfer",
    "balance_not_updated_after_cheque_or_cash_deposit", "beneficiary_not_allowed",
    "cancel_transfer", "card_about_to_expire", "card_acceptance", "card_arrival",
    "card_delivery_estimate", "card_linking", "card_not_working",
    "card_payment_fee_charged", "card_payment_not_recognised",
    "card_payment_wrong_exchange_rate", "card_swallowed", "cash_withdrawal_charge",
    "cash_withdrawal_not_recognised", "change_pin", "compromised_card",
    "contactless_not_working", "country_support", "declined_card_payment",
    "declined_cash_withdrawal", "declined_transfer",
    "direct_debit_payment_not_recognised", "disposable_card_limits",
    "edit_personal_details", "exchange_charge", "exchange_rate", "exchange_via_app",
    "extra_charge_on_statement", "failed_transfer", "fiat_currency_support",
    "get_disposable_virtual_card", "get_physical_card", "getting_spare_card",
    "getting_virtual_card", "lost_or_stolen_card", "lost_or_stolen_phone",
    "order_physical_card", "passcode_forgotten", "pending_card_payment",
    "pending_cash_withdrawal", "pending_top_up", "pending_transfer", "pin_blocked",
    "receiving_money", "Refund_not_showing_up", "request_refund",
    "reverted_card_payment?", "supported_cards_and_currencies", "terminate_account",
    "top_up_by_bank_transfer_charge", "top_up_by_card_charge",
    "top_up_by_cash_or_cheque", "top_up_failed", "top_up_limits", "top_up_reverted",
    "topping_up_by_card", "transaction_charged_twice", "transfer_fee_charged",
    "transfer_into_account", "transfer_not_received_by_recipient",
    "transfer_timing", "unable_to_verify_identity", "verify_my_identity",
    "verify_source_of_funds", "verify_top_up", "virtual_card_not_working",
    "visa_or_mastercard", "why_verify_identity", "wrong_amount_of_cash_received",
    "wrong_exchange_rate_for_cash_withdrawal",
)


def banking_criteria() -> dict[str, str]:
    return {label: label for label in BANKING77_LABELS}

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
    rehearsal_csv: str | Path | None = None,
    rehearsal_limit: int | None = 2500,
) -> list[DecisionExample]:
    """Guard training mix from frozen train file (test file stays eval-only).

    rehearsal_csv adds Banking77 train rows as 77-way choice examples so the
    guard run keeps banking skill (CC-BY-4.0, attribute in card).
    """
    path = Path(frozen_dir) / train_file
    examples = guard_examples_from_frozen(path, source="guard_train")
    if rehearsal_csv is not None:
        rh = banking_rehearsal_examples(rehearsal_csv)
        if rehearsal_limit is not None:
            rh = sorted(rh, key=lambda e: e.id)[:rehearsal_limit]
        examples.extend(rh)
    rng = random.Random(seed)
    rng.shuffle(examples)
    return examples[:limit] if limit else examples


def banking_rehearsal_examples(csv_path: str | Path) -> list[DecisionExample]:
    """Banking77 train rows as 77-way intent choice examples (rehearsal)."""
    import csv as _csv

    crit = banking_criteria()
    examples: list[DecisionExample] = []
    with open(csv_path, encoding="utf-8") as f:
        for i, row in enumerate(_csv.DictReader(f)):
            examples.append(DecisionExample(
                id=f"banking-rh-{i:06d}", source="banking77_rehearsal", qtype="choice",
                state=row["text"], instructions="Classify the banking intent.",
                answer=row["category"], criteria=crit,
            ))
    return examples


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
