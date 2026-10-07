"""SurakshaAgent: Jev-compatible System-1 guard.

Zero-shot path: stock laya encoder (en + multilingual routing).
Trained path: local guard checkpoint (engine.NirnayTrainModel payload)
on top of the en base, with per-bucket temperatures.

Frozen risk taxonomy (v1). Do not extend without freezing new hashes
(see AGENTS.md Data gates).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional

TOOL_RISK_OPTIONS = ["safe", "write", "privileged", "exfiltrate"]
SEVERITY_LEVELS = ["benign", "suspicious", "malicious"]

SURAKSHA_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "prompt_injection": {
        "type": "noul",
        "instructions": "Is this a prompt injection attempting to override instructions?",
    },
    "jailbreak": {
        "type": "noul",
        "instructions": "Is this a jailbreak attempting to bypass refusal (DAN, roleplay, encoding tricks)?",
    },
    "pii_leak": {
        "type": "noul",
        "instructions": "Does this contain PII, secrets, or API keys (Aadhaar, PAN, phone, keys) in state or tool args?",
    },
    "tool_risk": {
        "type": "choice",
        "instructions": "What is the tool-call risk?",
        "criteria": {
            "safe": "use when read-only, scoped, reversible",
            "write": "use when writes state but scoped",
            "privileged": "use when shell, exec, network egress, secrets access",
            "exfiltrate": "use when sends data outside trust boundary",
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe?",
        "criteria": SEVERITY_LEVELS,
    },
}

EN_MODEL = "convaiinnovations/laya"
MULTI_MODEL = "convaiinnovations/laya"  # subfolder="multilingual"
MULTI_SUBFOLDER = "multilingual"


def _has_devanagari(s: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in s)


def validate_questions(questions: Dict[str, Dict[str, Any]]) -> None:
    """422-style validation: unknown qtype, bad criteria shape, malformed question."""
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions must be a non-empty dict")
    for qid, q in questions.items():
        if not isinstance(q, dict):
            raise ValueError(f"question {qid!r}: must be a dict")
        qtype = q.get("type")
        if qtype not in ("noul", "choice", "score"):
            raise ValueError(f"question {qid!r}: unknown type {qtype!r}")
        if "instructions" not in q:
            raise ValueError(f"question {qid!r}: missing instructions")
        crit = q.get("criteria")
        if qtype == "choice":
            if isinstance(crit, list):  # server normalizes; raw agent requires dict
                raise ValueError(f"question {qid!r}: choice criteria as list must go via server normalize")
            if not isinstance(crit, dict) or not crit:
                raise ValueError(f"question {qid!r}: choice criteria must be a non-empty dict")
        elif qtype == "score":
            if not isinstance(crit, list) or not crit:
                raise ValueError(f"question {qid!r}: score criteria must be a non-empty list")


def normalize_criteria(questions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Accept criteria as list or dict (Jev-compat); ignore unknown fields."""
    out: Dict[str, Dict[str, Any]] = {}
    for qid, q in questions.items():
        q = dict(q)
        if q.get("type") == "choice" and isinstance(q.get("criteria"), list):
            items = q["criteria"]
            q["criteria"] = {str(v): f"option {v}" for v in items}
        out[qid] = {k: v for k, v in q.items() if k in ("type", "instructions", "criteria", "labels")}
    return out


class SurakshaAgent:
    """Lazy-loading guard agent. `device="mps"` on Mac, falls back to CPU.

    checkpoint_path: local .pt guard checkpoint (trained path, en only).
    Without it, all traffic runs zero-shot on stock laya.
    """

    def __init__(
        self,
        device: str = "mps",
        checkpoint_path: Optional[str] = None,
        calibration_path: Optional[str] = None,
    ) -> None:
        self.device = device
        self.checkpoint_path = checkpoint_path
        self.calibration_path = calibration_path
        self._en = None
        self._multi = None
        self._trained = None
        self._temps_override: Dict[str, float] = {}
        if calibration_path:
            from .temps import TEMP_MAX, TEMP_MIN, load_temps

            for key, value in load_temps(calibration_path).items():
                if not math.isfinite(float(value)) or not TEMP_MIN <= float(value) <= TEMP_MAX:
                    raise ValueError(f"temperature {key}={value} out of range")
                self._temps_override[str(key)] = float(value)

    def _load(self, model: str):
        import laya

        kwargs: Dict[str, Any] = {"device": self.device}
        if model == "suraksha-multi":
            kwargs["subfolder"] = MULTI_SUBFOLDER
            repo = MULTI_MODEL
        else:
            repo = EN_MODEL
        if self.calibration_path and self._trained is None:
            kwargs["calibration"] = self.calibration_path
        return laya.load(repo, **kwargs)

    def _pick_model(self, state: Any) -> str:
        s = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
        return "suraksha-multi" if _has_devanagari(s) else "suraksha-en"

    def _agent_for(self, model: str):
        if model == "suraksha-multi":
            if self._multi is None:
                self._multi = self._load(model)
            return self._multi
        if self._en is None:
            self._en = self._load(model)
        return self._en

    def _trained_for_en(self):
        """Load guard checkpoint onto the en base (None when no checkpoint)."""
        if self.checkpoint_path is None:
            return None
        if self._trained is None:
            import torch

            from .engine import NirnayTrainModel

            base = self._agent_for("suraksha-en")
            payload = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
            model, meta = NirnayTrainModel.from_checkpoint(
                base.model, payload, device=str(base.device)
            )
            model.eval()
            model.remove_hooks()
            self._trained = (model, base, meta)
        return self._trained

    @staticmethod
    def _to_internal(question: Dict[str, Any]) -> Dict[str, Any]:
        qtype = question["type"]
        criteria = question.get("criteria")
        if qtype == "choice" and isinstance(criteria, list):
            criteria = {str(i): None for i in range(len(criteria))}
        instructions = question["instructions"]
        if not isinstance(instructions, str):
            instructions = json.dumps(instructions)
        return {"t": qtype, "ins": instructions, "crit": criteria}

    def _temperature(self, base_agent, qtype: str, k: int) -> float:
        from laya.common import QTYPES

        from .temps import temp_bucket

        default = float(base_agent.temperature[QTYPES[qtype]])
        return float(self._temps_override.get(temp_bucket(qtype, k), default))

    def _trained_system_one(
        self,
        state: Any,
        questions: Dict[str, Dict[str, Any]],
        max_len: int,
        head_max_len: int,
    ) -> Dict[str, Any]:
        import numpy as np
        import torch
        from laya.common import QTYPES, build_sequence, confidence_from_probs, render_options

        from .engine import collate_examples

        model, base, _meta = self._trained_for_en() or (None, None, None)
        assert model is not None and base is not None
        items, qdefs = [], {}
        for qid, raw_q in questions.items():
            q = self._to_internal(raw_q)
            qdefs[qid] = q
            seq, markers = build_sequence(base.tok, state, q, max_len, head_max_len)
            if len(markers) != len(render_options(q)):
                raise ValueError(f"question {qid!r} options exceed head budget")
            items.append({"ids": seq, "markers": markers, "qtype": QTYPES[q["t"]]})
        batch = collate_examples(items, base.tok.pad_token_id)
        batch = {k: (v.to(base.device) if torch.is_tensor(v) else v) for k, v in batch.items()}
        model.eval()
        with torch.no_grad():
            out = model(batch)
        logits = out["logits"].detach().float().cpu().numpy()
        answers: Dict[str, Dict[str, Any]] = {}
        for row, qid in enumerate(questions):
            q = qdefs[qid]
            k = len(render_options(q))
            z = logits[row, :k] / self._temperature(base, q["t"], k)
            p = np.exp(z - z.max())
            p = p / p.sum()
            conf = round(confidence_from_probs(p, k), 4)
            if q["t"] == "choice":
                keys = list(q["crit"].keys())
                answers[qid] = {"type": "choice", "choice": keys[int(p.argmax())],
                                "probabilities": {key: round(float(v), 4) for key, v in zip(keys, p)},
                                "confidence": conf}
            elif q["t"] == "score":
                answers[qid] = {"type": "score",
                                "score": round(float((np.arange(k) * p).sum()), 4),
                                "probabilities": {str(i): round(float(v), 4) for i, v in enumerate(p)},
                                "confidence": conf}
            else:
                answers[qid] = {"type": "noul", "noul": round(float(p[1]), 4),
                                "confidence": round(max(float(p[1]), 1.0 - float(p[1])), 4)}
        return {"model": "suraksha-1", "answers": answers,
                "usage": {"input_tokens": int(batch["attention_mask"].sum().item()),
                          "output_tokens": 0, "truncated": False},
                "routing": {"model": "suraksha-en"}}

    def system_one(
        self,
        state: Any,
        questions: Optional[Dict[str, Dict[str, Any]]] = None,
        max_len: int = 512,
        head_max_len: int = 192,
    ) -> Dict[str, Any]:
        qs = normalize_criteria(questions or SURAKSHA_QUESTIONS)
        validate_questions(qs)
        model = self._pick_model(state)
        if model == "suraksha-multi" and max_len == 512:
            max_len, head_max_len = 1024, 256
        if model == "suraksha-en" and self.checkpoint_path is not None and Path(self.checkpoint_path).exists():
            try:
                return self._trained_system_one(state, qs, max_len, head_max_len)
            except Exception:
                pass  # fall through to stock base rather than failing the gate
        agent = self._agent_for(model)
        out = agent.system_one(state, qs, max_len=max_len, head_max_len=head_max_len)
        out.setdefault("routing", {})["model"] = model
        return out
