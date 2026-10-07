"""Space demo: textbox + JSON tool box -> guard probs + latency.

Preload pattern mirrors laya Router(preload=True): agent loads once at boot.
"""
import json
import os
import time

import gradio as gr

from suraksha.agent import SURAKSHA_QUESTIONS, SurakshaAgent

_agent = SurakshaAgent(
    device=os.environ.get("SURAKSHA_DEVICE", "cpu"),
    checkpoint_path=os.environ.get("SURAKSHA_CKPT"),
    calibration_path=os.environ.get("SURAKSHA_CALIBRATION"),
)


def score(prompt: str, tool_json: str):
    t0 = time.perf_counter()
    out = _agent.system_one(prompt or "", SURAKSHA_QUESTIONS)
    ms = (time.perf_counter() - t0) * 1000.0
    lines = [f"model={out.get('routing', {}).get('model')} latency={ms:.0f}ms"]
    for qid, ans in out.get("answers", {}).items():
        if ans["type"] == "noul":
            lines.append(f"{qid}: P(true)={ans['noul']} conf={ans['confidence']}")
        elif ans["type"] == "choice":
            lines.append(f"{qid}: {ans['choice']} {json.dumps(ans['probabilities'])}")
        else:
            lines.append(f"{qid}: score={ans['score']} {json.dumps(ans['probabilities'])}")
    tool_lines = []
    if tool_json.strip():
        try:
            tool_state = json.loads(tool_json)
        except json.JSONDecodeError as e:
            return "\n".join(lines), f"tool JSON invalid: {e}"
        t1 = time.perf_counter()
        tout = _agent.system_one(tool_state, SURAKSHA_QUESTIONS)
        tms = (time.perf_counter() - t1) * 1000.0
        tr = tout["answers"]["tool_risk"]
        tool_lines.append(f"tool_risk={tr['choice']} {json.dumps(tr['probabilities'])} ({tms:.0f}ms)")
    return "\n".join(lines), "\n".join(tool_lines) or "no tool call given"


demo = gr.Interface(
    fn=score,
    inputs=[gr.Textbox(label="prompt / state", lines=4),
            gr.Textbox(label="mcp tool call json {tool, args, permission_scope}", lines=4)],
    outputs=[gr.Textbox(label="guard probs"), gr.Textbox(label="tool risk")],
    title="SURAKSHA 450M guard demo",
    description="Calibrated P(prompt-injection, jailbreak, PII-leak, tool-risk) in one forward pass. CI-grade scores, not a pentest verdict.",
)

if __name__ == "__main__":
    demo.launch()
