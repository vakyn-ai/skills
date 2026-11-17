"""Judgments as reusable data: score each listing once, store the raw probabilities, rank many ways.

Standard library only, nothing to install. Needs VAKYN_API_KEY; VAKYN_BASE_URL is optional
(default https://api.vakyn.com).
"""

import json
import os
import pathlib
import urllib.request

QUESTIONS = {
    "quiet": {"type": "score", "instructions": "How quiet does the listing say the flat is?", "criteria": [
        "Says it is noisy: busy street, bars, works nearby",
        "Says nothing about noise",
        "Some hint of calm: a side street or upper floor",
        "Says it is quiet: courtyard side, quiet street, no traffic"]},
    "light": {"type": "score", "instructions": "How much daylight does the listing say the flat gets?", "criteria": [
        "Says it is dark: ground floor facing a wall, small windows",
        "Says nothing about light",
        "Some daylight: windows mentioned, no direction or size",
        "Very bright: big windows, south or west facing, top floor"]},
    "condition": {"type": "score", "instructions": "What state is the flat in, from the listing?", "criteria": [
        "Needs work: damage, old fittings, renovation needed",
        "Not described",
        "Mixed: some parts new, some old but kept up",
        "New or fully renovated"]},
    "pets_allowed": {"type": "noul", "instructions": "Does the listing say pets are allowed?"},
}
STORE = pathlib.Path("judgments.jsonl")
BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state: dict, questions: dict, timeout: float = 30.0) -> tuple[dict, str]:
    """POST /v1/systemone; returns the answers by question name and the request id."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"], r.headers.get("x-vakyn-request-id", "")


def judge(listing_id: str, text: str) -> dict:
    """Ask once per listing (and again only when its text changes). Keep every probability."""
    answers, request_id = decide({"listing": text}, QUESTIONS)
    row = {"id": listing_id, "request_id": request_id, "pets_allowed": answers["pets_allowed"]["noul"]}
    for k in ("quiet", "light", "condition"):
        s = answers[k]
        row[k] = {"score": s["score"], "probabilities": s["probabilities"], "confidence": s["confidence"]}
    return row


def rank(rows: list[dict], weights: dict[str, float], need_pets: bool = False) -> list[tuple[str, float]]:
    """Runs on stored answers only: moving a slider or a filter never calls the server."""
    keep = [r for r in rows if not need_pets or r["pets_allowed"] >= 0.8]
    total = sum(weights.values()) or 1.0
    scored = [(r["id"], round(sum(w * r[k]["score"] / 3 for k, w in weights.items()) / total, 2)) for r in keep]
    return sorted(scored, key=lambda x: -x[1])


def features(row: dict) -> list[float]:
    """Optional: the same answers as inputs for a classical model (logistic regression, trees)."""
    return [row[k]["probabilities"][str(level)] for k in ("quiet", "light", "condition") for level in range(4)] + [
        row["pets_allowed"]]


LISTINGS = {
    "flat_17": "Bright two-room flat on the 4th floor, facing a quiet inner courtyard. Big south windows in both "
               "rooms. Kitchen redone in 2023, bathroom original but clean. Tram stop 2 minutes away. Small pets welcome.",
    "flat_22": "Ground-floor studio above a busy bar street, lively area at night. Window onto the street. "
               "Freshly painted, new floors and new bathroom. No pets.",
    "flat_31": "Three rooms on the 2nd floor of an older building on a side street. Needs some updating: original "
               "kitchen, worn floors. Cats are fine.",
}
if not STORE.exists():  # judge once
    STORE.write_text("".join(json.dumps(judge(i, t)) + "\n" for i, t in LISTINGS.items()))
rows = [json.loads(line) for line in STORE.read_text().splitlines()]
print("quiet first:      ", rank(rows, {"quiet": 3, "light": 1, "condition": 1}))
print("condition first:  ", rank(rows, {"quiet": 1, "light": 1, "condition": 3}))
print("pets, light first:", rank(rows, {"quiet": 1, "light": 3, "condition": 1}, need_pets=True))
print("features flat_17: ", [round(x, 2) for x in features(rows[0])])
