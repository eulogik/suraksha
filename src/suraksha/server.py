"""suraksha-serve: POST /v1/systemone (Jev-compatible)."""
from __future__ import annotations

import argparse
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from .agent import SurakshaAgent, normalize_criteria, validate_questions

app = FastAPI(title="suraksha-serve")
_agent: Optional[SurakshaAgent] = None


def get_agent() -> SurakshaAgent:
    global _agent
    if _agent is None:
        import os

        _agent = SurakshaAgent(
            device=os.environ.get("SURAKSHA_DEVICE", "mps"),
            checkpoint_path=os.environ.get("SURAKSHA_CKPT"),
            calibration_path=os.environ.get("SURAKSHA_CALIBRATION"),
        )
    return _agent


class SystemOneRequest(BaseModel):
    state: Any
    questions: Optional[Dict[str, Dict[str, Any]]] = None
    max_len: Optional[int] = None
    head_max_len: Optional[int] = None


@app.post("/v1/systemone")
def systemone(req: SystemOneRequest):
    try:
        qs = normalize_criteria(req.questions or {})
        if qs:
            validate_questions(qs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    kwargs: Dict[str, Any] = {}
    if req.max_len is not None:
        kwargs["max_len"] = req.max_len
    if req.head_max_len is not None:
        kwargs["head_max_len"] = req.head_max_len
    try:
        # None questions -> agent default taxonomy
        return get_agent().system_one(req.state, req.questions, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/health")
def health():
    return {"ok": True}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    a = p.parse_args()
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
