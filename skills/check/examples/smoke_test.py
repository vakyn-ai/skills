"""Smoke test: VAKYN and your current chat model on the same ~30 records, side by side.

Usage:
    python3 smoke_test.py records.jsonl --request smoke-test.request.json [--n 30]
        [--chat-answers chat.jsonl | --ask-chat-model] [--threshold 0.8]
        [--price-in 0.15 --price-out 0.60] [--out smoke-results.jsonl]

records.jsonl: one record per line, {"id": "...", "text": "..."} or {"id": "...", "state": {...}},
plus "label" when a person has said what is right.
The request file holds the question (only its first question is compared); each record's
state replaces the example state.

VAKYN side: pip install typesafe-sdk; TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
Chat-model side, one of:
  --chat-answers FILE   picks the chat model already made ({"id": ..., "chat_pick": ...}); nothing is sent
  --ask-chat-model      sends the records to an OpenAI-compatible chat API (CHAT_BASE_URL,
                        CHAT_API_KEY, CHAT_MODEL). Only after the data owner agreed: this leaves
                        the machine and may cost money.
  neither               VAKYN only.
Every answer is written to --out. Nothing is rerun.
"""

import argparse
import collections
import json
import os
import re
import statistics
import time
import urllib.request

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(value):
    if isinstance(value, str):
        return PHONE.sub("[phone]", EMAIL.sub("[email]", value))
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def pick_sample(records, n):
    """Round-robin over labels so every class shows up; first n when there are no labels."""
    groups = collections.defaultdict(list)
    for r in records:
        groups[r.get("label")].append(r)
    if len(groups) == 1:
        return records[:n]
    out, queues = [], [list(g) for g in groups.values()]
    while len(out) < n and any(queues):
        for q in queues:
            if q and len(out) < n:
                out.append(q.pop(0))
    return out


def sdk_question(q):
    if q["type"] == "choice":
        return Choice(instructions=q["instructions"], criteria=q["criteria"])
    if q["type"] == "score":
        return Score(instructions=q["instructions"], criteria=q["criteria"])
    return Noul(instructions=q["instructions"], criteria=q.get("criteria"))


def vakyn_answer(client, state, qid, q):
    t0 = time.perf_counter()
    res = client.system_one(state=state, questions={qid: sdk_question(q)})
    ms = (time.perf_counter() - t0) * 1000
    a = res.model_dump()["answers"][qid]
    if q["type"] == "noul":
        pick, conf = ("true" if a["noul"] >= 0.5 else "false"), abs(2 * a["noul"] - 1)
        probs = {"true": a["noul"], "false": round(1 - a["noul"], 2)}
    elif q["type"] == "score":
        top = max(a["probabilities"], key=a["probabilities"].get)
        pick, conf, probs = q["criteria"][int(top)], a["confidence"], a["probabilities"]
    else:
        pick, conf, probs = a["choice"], a["confidence"], a["probabilities"]
    return {"vakyn_pick": pick, "vakyn_confidence": conf, "vakyn_probabilities": probs,
            "request_id": res.request_id, "vakyn_ms": round(ms)}


def chat_answer(state, q):
    """Same question, same options, same evidence. Reply must be one option name."""
    if q["type"] == "choice":
        options = "\n".join(f"- {k}: {v}" for k, v in q["criteria"].items())
    elif q["type"] == "score":
        options = "\n".join(f"- {v}" for v in q["criteria"])
    else:
        options = "- true\n- false"
    prompt = (f"{q['instructions']}\n\nAnswer with exactly one of these, and nothing else:\n{options}\n\n"
              f"state:\n{json.dumps(state, ensure_ascii=False)}")
    body = {"model": os.environ["CHAT_MODEL"], "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        os.environ["CHAT_BASE_URL"].rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {os.environ['CHAT_API_KEY']}"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read())
    ms = (time.perf_counter() - t0) * 1000
    text = res["choices"][0]["message"]["content"].strip().strip("`\"' .").lower()
    usage = res.get("usage", {})
    return {"chat_pick": text, "chat_ms": round(ms),
            "chat_tokens_in": usage.get("prompt_tokens", 0), "chat_tokens_out": usage.get("completion_tokens", 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("records")
    ap.add_argument("--request", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--chat-answers")
    ap.add_argument("--ask-chat-model", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.8, help="below this VAKYN counts as unsure")
    ap.add_argument("--price-in", type=float, help="chat model price per million input tokens")
    ap.add_argument("--price-out", type=float, help="chat model price per million output tokens")
    ap.add_argument("--no-redact", action="store_true")
    ap.add_argument("--out", default="smoke-results.jsonl")
    a = ap.parse_args()

    template = json.load(open(a.request))
    qid, q = next(iter(template["questions"].items()))
    records = [json.loads(line) for line in open(a.records) if line.strip()]
    sample = pick_sample(records, a.n)
    chat_given = {}
    if a.chat_answers:
        chat_given = {r["id"]: r["chat_pick"] for r in map(json.loads, open(a.chat_answers)) if r.get("id")}

    client = TypeSafeClient(timeout=30.0)
    results = []
    with open(a.out, "w") as out:
        for r in sample:
            state = r.get("state") or {"message": r["text"]}
            if not a.no_redact:
                state = redact(state)
            row = {"id": r.get("id"), "label": r.get("label"), **vakyn_answer(client, state, qid, q)}
            if r.get("id") in chat_given:
                row["chat_pick"] = chat_given[r["id"]]
            elif a.ask_chat_model:
                row.update(chat_answer(state, q))
            if "chat_pick" in row:
                row["agree"] = row["vakyn_pick"] == row["chat_pick"]
            out.write(json.dumps(row) + "\n")  # keep every answer, good or bad
            results.append(row)
            print(f"{row['id']:<6} VAKYN {row['vakyn_pick']:<16} {row['vakyn_confidence']:.2f}"
                  f"  chat {row.get('chat_pick', '-'):<16} label {row['label'] or '-'}")

    n = len(results)
    print(f"\n{n} records (stopped here; run the full batch only after reviewing this).")
    both = [r for r in results if "chat_pick" in r]
    if both:
        ag = sum(r["agree"] for r in both)
        print(f"Agreement with the chat model: {ag}/{len(both)} ({ag / len(both):.0%}). Agreement is not accuracy.")
    labeled = [r for r in results if r["label"] is not None]
    if labeled:
        v = sum(r["vakyn_pick"] == r["label"] for r in labeled)
        line = f"Against person labels ({len(labeled)}): VAKYN right {v}"
        if both:
            c = sum(r.get("chat_pick") == r["label"] for r in labeled if "chat_pick" in r)
            line += f", chat model right {c}"
        print(line)
    unsure = [r for r in results if r["vakyn_confidence"] < a.threshold]
    print(f"VAKYN unsure (confidence < {a.threshold}): {len(unsure)}/{n}")
    for r in unsure:
        print(f"  {r['id']}: {r['vakyn_pick']} {r['vakyn_confidence']:.2f}  {r['vakyn_probabilities']}")
    dis = [r for r in both if not r["agree"]]
    if dis:
        print("Disagreements, side by side:")
        for r in dis:
            print(f"  {r['id']}: VAKYN {r['vakyn_pick']} ({r['vakyn_confidence']:.2f})  chat {r['chat_pick']}"
                  f"  label {r['label'] or '-'}")
    vms = [r["vakyn_ms"] for r in results]
    print(f"VAKYN time per call: median {statistics.median(vms):.0f} ms, max {max(vms)} ms (this machine, one at a time)")
    cms = [r["chat_ms"] for r in results if "chat_ms" in r]
    if cms:
        print(f"Chat model time per call: median {statistics.median(cms):.0f} ms, max {max(cms)} ms")
        tin = sum(r["chat_tokens_in"] for r in results if "chat_ms" in r)
        tout = sum(r["chat_tokens_out"] for r in results if "chat_ms" in r)
        if a.price_in is not None and a.price_out is not None:
            cost = (tin * a.price_in + tout * a.price_out) / 1e6
            print(f"Chat model cost: ${cost:.4f} for {len(cms)} calls ({tin} in, {tout} out tokens)")
        else:
            print(f"Chat model tokens: {tin} in, {tout} out (pass --price-in/--price-out for cost)")
    print(f"Every answer is in {a.out}.")


if __name__ == "__main__":
    main()
