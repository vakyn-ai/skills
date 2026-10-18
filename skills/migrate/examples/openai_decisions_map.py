"""Map an OpenAI Decisions API request (POST /v1/decisions) to a VAKYN /v1/systemone request,
and map the answer back to the OpenAI answer shape, so the calling code can stay as it is
while both run side by side.

Field names come from OpenAI's API reference (checked 2026-10-09). Read the person's code and
OpenAI's current reference before relying on this: the API is new and may change.

Usage:
    python3 openai_decisions_map.py openai-decisions.before.json > openai-decisions.request.json
    python3 openai_decisions_map.py openai-decisions.before.json --send   # VAKYN_BASE_URL, VAKYN_API_KEY
"""

import json
import os
import sys
import urllib.request


def _text(content):
    """Text parts only. VAKYN's API has no image field, so an image part stops the mapping."""
    if isinstance(content, str):
        return content
    parts = []
    for part in content:
        if part.get("type") == "input_text":
            parts.append(part["text"])
        else:
            raise ValueError(f"cannot map input part of type {part.get('type')!r}; keep this request on the old API")
    return "\n".join(parts)


def to_systemone(req, model="jev-latest"):
    """OpenAI Decisions request -> VAKYN request. Returns (body, names) where names keeps the
    original question names (None when unnamed) and choice values (which may be booleans)."""
    inp = req["input"]
    state = inp if isinstance(inp, str) else [_text(m["content"]) for m in inp]
    questions, meta = {}, []
    for i, q in enumerate(req["questions"]):
        qid = q.get("name") or f"q{i}"          # VAKYN questions are named; OpenAI names are optional
        if qid in questions:
            raise ValueError(f"duplicate question name {qid!r}")
        kind = q["type"]
        if kind == "predicate":
            questions[qid] = {"type": "noul", "instructions": q["instructions"]}
            meta.append((qid, q.get("name"), "predicate", None))
        elif kind == "choice":
            values = [c["value"] for c in q["choices"]]
            keys = [json.dumps(v) if isinstance(v, bool) else str(v) for v in values]
            questions[qid] = {"type": "choice", "instructions": q["instructions"],
                              "criteria": {k: c.get("description") or k for k, c in zip(keys, q["choices"])}}
            meta.append((qid, q.get("name"), "choice", dict(zip(keys, values))))
        elif kind == "score":
            # VAKYN reads the first level as the lowest. Keep the order; check the person's
            # levels run lowest first.
            labels = [lv["label"] + (f": {lv['description']}" if lv.get("description") else "") for lv in q["levels"]]
            questions[qid] = {"type": "score", "instructions": q["instructions"], "criteria": labels}
            meta.append((qid, q.get("name"), "score", [lv["label"] for lv in q["levels"]]))
        else:
            raise ValueError(f"unknown question type {kind!r}")
    # safety_identifier has no VAKYN field; it is dropped.
    return {"model": model, "state": state, "questions": questions}, meta


def to_openai_answers(resp, meta):
    """VAKYN response -> OpenAI-shaped {model, answers: [...]}, answers in question order."""
    out = []
    for qid, name, kind, extra in meta:
        a = resp["answers"][qid]
        if kind == "predicate":
            out.append({"type": "predicate", "name": name, "probability": a["noul"]})
        elif kind == "choice":
            out.append({"type": "choice", "name": name, "choice": extra[a["choice"]],
                        "confidence": a["confidence"],
                        "probabilities": [{"value": extra[k], "probability": p} for k, p in a["probabilities"].items()]})
        else:
            # `value` = level index here; check it against one real OpenAI response before relying on it.
            out.append({"type": "score", "name": name, "score": a["score"], "confidence": a["confidence"],
                        "probabilities": [{"value": int(i), "label": extra[int(i)], "probability": p}
                                          for i, p in a["probabilities"].items()]})
    return {"model": resp["model"], "answers": out}


def send(body):
    base = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com").rstrip("/")
    req = urllib.request.Request(f"{base}/v1/systemone", data=json.dumps(body).encode(), headers={
        "content-type": "application/json", "authorization": f"Bearer {os.environ['VAKYN_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    body, meta = to_systemone(json.load(open(sys.argv[1])))
    if "--send" in sys.argv:
        print(json.dumps(to_openai_answers(send(body), meta), indent=2))
    else:
        print(json.dumps(body, indent=2))
