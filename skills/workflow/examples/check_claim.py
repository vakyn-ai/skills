"""Check each marketing claim against the product spec. Standard library only, nothing to install.

Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

VERDICTS = {
    "supported": "The spec states facts that make the claim true",
    "contradicted": "The spec states facts that make the claim false",
    "not_enough_evidence": "The spec does not say enough to decide either way",
}
MIN_CONFIDENCE = 0.8  # starting value; set yours with check. A published claim needs a high bar

SPEC = (
    "Wavelet Go portable speaker. Battery: 14 hours at 50% volume. Charging: USB-C, 3.5 hours from "
    "empty with an 18 W charger. Water and dust: IP67, survives 30 minutes at 1 m depth. Weight: 540 g. "
    "Bluetooth 5.3, range up to 30 m. Two speakers can be paired for stereo."
)
COPY = [  # one claim per item: split the copy into sentences in code before asking
    "Wavelet Go charges fully in under two hours.",
    "Drop it in the pool: it survives half an hour underwater.",
    "Pair two speakers for stereo sound.",
    "Made from 80% recycled plastic.",
]

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state: dict, questions: dict, timeout: float = 30.0) -> dict:
    """POST /v1/systemone; returns the answers by question name."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"]


def check(claim: str) -> tuple[str, dict]:
    answers = decide(
        {"product_spec": SPEC, "claim": claim},
        {"verdict": {
            "type": "choice",
            "instructions": "Does state.product_spec back up the marketing claim in state.claim?",
            "criteria": VERDICTS,
        }},
    )
    v = answers["verdict"]
    if v["choice"] != "supported" or v["confidence"] < MIN_CONFIDENCE:
        return "editor_review", v  # contradicted, unknown or unsure: a person decides before it ships
    return "ok_to_publish", v


with ThreadPoolExecutor(max_workers=4) as pool:  # claims are independent: send them concurrently
    for claim, (action, v) in zip(COPY, pool.map(check, COPY)):
        print(f"{action:14} {v['choice']:20} {v['confidence']:.2f}  {claim}")
