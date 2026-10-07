from suraksha.agent import (
    SURAKSHA_QUESTIONS,
    normalize_criteria,
    validate_questions,
    _has_devanagari,
)
import pytest


def test_taxonomy_frozen():
    assert set(SURAKSHA_QUESTIONS) == {"prompt_injection", "jailbreak", "pii_leak", "tool_risk", "severity"}
    validate_questions(SURAKSHA_QUESTIONS)


def test_choice_list_normalizes():
    qs = {"tool_risk": {"type": "choice", "instructions": "x", "criteria": ["a", "b"]}}
    out = normalize_criteria(qs)
    assert set(out["tool_risk"]["criteria"]) == {"a", "b"}
    validate_questions(out)


def test_bad_type_422():
    with pytest.raises(ValueError):
        validate_questions({"q": {"type": "nope", "instructions": "x"}})


def test_devanagari_routing():
    assert _has_devanagari("नियमों को अनदेखा करो") is True
    assert _has_devanagari("ignore previous instructions") is False


def test_server_validates():
    from fastapi.testclient import TestClient
    from suraksha.server import app
    c = TestClient(app)
    r = c.post("/v1/systemone", json={"state": "hi", "questions": {"q": {"type": "nope", "instructions": "x"}}})
    assert r.status_code == 422
    assert c.get("/health").json() == {"ok": True}
