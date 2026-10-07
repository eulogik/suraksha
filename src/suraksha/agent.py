"""SurakshaAgent: Jev-compatible System-1 guard over frozen laya encoder.

Frozen risk taxonomy (v1). Do not extend without freezing new hashes
(see AGENTS.md Data gates).
"""
from __future__ import annotations

import json
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

# Heuristic Devanagari detection: English checkpoint cannot read it (laya Router precedent).
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
        # drop unknown fields except the known set
        out[qid] = {k: v for k, v in q.items() if k in ("type", "instructions", "criteria", "labels")}
    return out


class SurakshaAgent:
    """Lazy-loading guard agent. `device="mps"` on Mac, falls back to CPU."""

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

    def _load(self, model: str):
        import laya

        kwargs: Dict[str, Any] = {"device": self.device}
        if model == "suraksha-multi":
            kwargs["subfolder"] = MULTI_SUBFOLDER
            repo = MULTI_MODEL
        else:
            repo = self.checkpoint_path or EN_MODEL
        if self.calibration_path:
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
        # multilingual context budget differs (AGENTS.md)
        if model == "suraksha-multi" and max_len == 512:
            max_len, head_max_len = 1024, 256
        agent = self._agent_for(model)
        out = agent.system_one(state, qs, max_len=max_len, head_max_len=head_max_len)
        out.setdefault("routing", {})["model"] = model
        return out
