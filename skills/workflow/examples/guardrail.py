"""Guardrail in front of an agent's API calls: allow, hold for a person, or block.

pip install typesafe-sdk. Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
Same questions and rule as the "Guardrails for agents" page in the VAKYN docs.

    python guardrail.py            # checks the two sample calls in this folder
"""

import json
import sys
from pathlib import Path

from typesafe_sdk import TypeSafeClient

# Example value from the docs. For calls that are hard to undo, start at 0.8 and
# set yours on labeled checks with the check skill.
SURE = 0.70
QUESTIONS = json.loads((Path(__file__).parent / "guardrail-clear.request.json").read_text())["questions"]
LOG = Path("guardrail.log.jsonl")

client = TypeSafeClient(timeout=30.0)


def sureness(answers: dict) -> dict:
    """How sure each answer is, from 0 to 1. A noul near 0.5 is unsure."""
    return {
        name: max(a["noul"], 1 - a["noul"]) if a["type"] == "noul" else a["confidence"]
        for name, a in answers.items()
    }


def check_call(agent: dict, call: dict, context: dict) -> dict:
    """Decide before the call goes out. Anything unsure, or VAKYN down, waits for a person."""
    state = {"agent": agent, "call": call, "context": context}
    try:
        result = client.system_one(state=state, questions=QUESTIONS)
    except Exception as e:  # server down or refused: never let the call through unchecked
        decision = {"do": "hold", "why": f"guardrail unavailable: {type(e).__name__}"}
        _log(state, None, None, decision)
        return decision

    answers = {name: a.model_dump() if hasattr(a, "model_dump") else dict(a) for name, a in result.answers.items()}
    sure = sureness(answers)
    weakest = min(sure, key=sure.get)
    if sure[weakest] < SURE:
        decision = {"do": "hold", "why": f"{weakest} is only {sure[weakest]:.2f} sure"}
    elif answers["action"]["choice"] == "allow":
        decision = {"do": "allow", "why": "every answer sure"}
    elif answers["action"]["choice"] == "block":
        decision = {"do": "block", "why": "every answer sure"}
    else:  # ask_human
        decision = {"do": "hold", "why": "VAKYN asks for a person"}
    _log(state, result.request_id, answers, decision)
    return decision


def _log(state, request_id, answers, decision):
    """Every check is a record of what the agent tried to do and why it was allowed or held."""
    with LOG.open("a") as f:
        f.write(json.dumps({"request_id": request_id, "call": state["call"], "answers": answers,
                            "sure_at": SURE, "decision": decision}) + "\n")


if __name__ == "__main__":
    here = Path(__file__).parent
    for name in ("clear", "borderline"):
        s = json.loads((here / f"guardrail-{name}.request.json").read_text())["state"]
        d = check_call(s["agent"], s["call"], s["context"])
        print(f"{name:10} {d['do']:5}  {d['why']}")
    sys.exit(0)
