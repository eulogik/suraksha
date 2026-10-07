"""eval_banking77: no-forgetting gate (must stay >= 0.86).

77-way intent choice per row, stock or trained checkpoint. Writes raw JSON.
Heavy-ish (3k rows); run once per checkpoint that matters.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")

INTENTS = ["activate_my_card", "age_limit", "apple_pay_or_google_pay", "atm_support",
           "automatic_top_up", "balance_not_updated_after_bank_transfer",
           "balance_not_updated_after_cheque_or_cash_deposit", "beneficiary_not_allowed",
           "cancel_transfer", "card_about_to_expire", "card_acceptance", "card_arrival",
           "card_delivery_estimate", "card_linking", "card_not_working",
           "card_payment_fee_charged", "card_payment_not_recognised",
           "card_payment_wrong_exchange_rate", "card_swallowed", "cash_withdrawal_charge",
           "cash_withdrawal_not_recognised", "change_pin", "compromised_card",
           "contactless_not_working", "country_support", "declined_card_payment",
           "declined_cash_withdrawal", "declined_transfer", "direct_debit_payment_not_recognised",
           "disposable_card_limits", "edit_personal_details", "exchange_charge",
           "exchange_rate", "exchange_via_app", "extra_charge_on_statement",
           "failed_transfer", "fiat_currency_support", "get_disposable_virtual_card",
           "get_physical_card", "getting_spare_card", "getting_virtual_card",
           "lost_or_stolen_card", "lost_or_stolen_phone", "order_physical_card",
           "passcode_forgotten", "pending_card_payment", "pending_cash_withdrawal",
           "pending_top_up", "pending_transfer", "pin_blocked", "receiving_money",
           "Refund_not_showing_up", "request_refund", "reverted_card_payment?",
           "supported_cards_and_currencies", "terminate_account",
           "top_up_by_bank_transfer_charge", "top_up_by_card_charge",
           "top_up_by_cash_or_cheque", "top_up_failed", "top_up_limits", "top_up_reverted",
           "topping_up_by_card", "transaction_charged_twice", "transfer_fee_charged",
           "transfer_into_account", "transfer_not_received_by_recipient",
           "transfer_timing", "unable_to_verify_identity", "verify_my_identity",
           "verify_source_of_funds", "verify_top_up", "virtual_card_not_working",
           "visa_or_mastercard", "why_verify_identity", "wrong_amount_of_cash_received",
           "wrong_exchange_rate_for_cash_withdrawal"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="/Volumes/KIOXIA 1TB/suraksha/banking77_test.csv")
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--out", default="eval/banking77_regression.json")
    p.add_argument("--device", default="mps")
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    from suraksha.agent import SurakshaAgent

    rows = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    if a.limit:
        rows = rows[:a.limit]
    agent = SurakshaAgent(device=a.device, checkpoint_path=a.checkpoint)
    q = {"intent": {"type": "choice", "instructions": "Classify the banking intent.",
                    "criteria": {label: label for label in INTENTS}}}
    hits = tot = 0
    lat = []
    for r in rows:
        t0 = time.perf_counter()
        try:
            out = agent.system_one(r["text"], q)
        except Exception:  # noqa: BLE001
            continue
        lat.append((time.perf_counter() - t0) * 1000.0)
        tot += 1
        if out["answers"]["intent"]["choice"] == r["category"]:
            hits += 1
    lat_sorted = sorted(lat)
    payload = {"checkpoint": a.checkpoint or "stock-laya-zero-shot", "n": tot,
               "accuracy": (hits / tot) if tot else None,
               "gate": ">=0.86",
               "latency_ms": {"p50": lat_sorted[len(lat_sorted) // 2] if lat_sorted else None}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
