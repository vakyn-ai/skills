"""AFTER: the same triage on VAKYN Cloud, as a direct HTTP call. Standard library only, nothing to install.

    export VAKYN_API_KEY=...                       # a vk_ key from vakyn.com/console/keys; never in code
    export VAKYN_BASE_URL=https://api.vakyn.com    # optional; root, no /v1; or your own open-server's URL
    export VAKYN_MODEL=...                         # optional; own open-server: the name from /v1/models

Run: python3 sdk_after.py

The SDK client, its question classes and its typed results are gone: the questions are plain
JSON and the answers are read by question name. What the SDK did for us is written out here: a
timeout, and a few retries on 408/429/5xx and connection errors that wait as long as the
server's retry-after says.
Rollback: keep the old call (sdk_before.py) behind one setting until the move is done.
"""

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")
MODEL = os.environ.get("VAKYN_MODEL")  # left out on VAKYN Cloud: vakyn-max answers
TIMEOUT = 30  # seconds per attempt; the old SDK used 10, raise it on a CPU-only server of your own

QUESTIONS = {
    "team": {
        "type": "choice",
        "instructions": "Which desk should answer state.message?",
        "criteria": {
            "repairs": "Broken parts, flat tires, brakes, gears",
            "bookings": "Reserving, changing or cancelling a rental",
            "billing": "Charges, deposits, refunds",
            "other": "None of these fits",
        },
    },
    "refund": {"type": "noul", "instructions": "Does state.message ask for money back?"},
    "urgency": {
        "type": "score",
        "instructions": "How soon does state.message need a reply?",
        "criteria": ["This week", "Today", "Within the hour"],
    },
}


def decide(state, questions, retries=3):
    """POST /v1/systemone; returns (response body, request id). Retries 408, 429 and 5xx."""
    body = {"state": state, "questions": questions, **({"model": MODEL} if MODEL else {})}
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            f"{BASE_URL}/v1/systemone",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.load(r), r.headers.get("x-vakyn-request-id")
        except urllib.error.HTTPError as e:
            if attempt == retries or not (e.code in (408, 429) or e.code >= 500):
                raise RuntimeError(f"VAKYN {e.code}: {e.read()[:300].decode(errors='replace')}") from e
            time.sleep(float(e.headers.get("retry-after") or 2 ** attempt))
        except (urllib.error.URLError, TimeoutError):  # no connection, or no answer in time
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def triage(message: str) -> dict:
    result, request_id = decide({"message": message}, QUESTIONS)
    answers = result["answers"]
    return {
        "team": answers["team"]["choice"],
        "team_confidence": answers["team"]["confidence"],
        "refund": answers["refund"]["noul"],
        "urgency": answers["urgency"]["score"],
        "request_id": request_id,
        "model": result["model"],  # log it: it names the model that answered
    }


if __name__ == "__main__":
    print(triage("The chain on the e-bike I rented this morning snapped two km from your shop. "
                 "I'm stuck on the river path, can someone come out?"))
