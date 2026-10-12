"""Replay: re-decide stored answers with changed decision code, thresholds or rules. No model calls.

Usage:
    # In the app (here as a script): ask, decide, and store one audit record per case.
    python3 replay.py record --request drift.request.json --records tickets.jsonl \
        --policy routing-policy.v1.json --out answers.jsonl
    # After editing decide(), the thresholds or the rules: re-decide every stored case and diff.
    python3 replay.py replay --answers answers.jsonl --policy routing-policy.v2.json \
        [--request drift.request.json] [--show 30]

record needs the SDK (pip install typesafe-sdk; TYPESAFE_BASE_URL and TYPESAFE_API_KEY).
replay needs nothing but the stored file: it never calls the server, so it runs in seconds on
thousands of cases and costs nothing.

Each stored line is the audit record of one decision (references/go-live.md#audit-record):
case id, step, model name, request id, the input (or its hash and where it is kept), a hash per
question, every answer with its probabilities, the policy version and hash, the outcome and the
reason. replay compares the stored outcome with what the new code decides from the same answers.

Replay is valid only while the questions are the same: answers to an old question say nothing about
a new one. Give --request to check the stored question hashes against the current ones; changed
questions need a drift check (re-ask the model), not a replay.
"""

import argparse
import collections
import datetime
import hashlib
import json
import sys

STEP = "route_ticket"


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def load_policy(path):
    policy = json.load(open(path))
    return policy, digest(policy)


def decide(answers, policy):
    """The decision code: VAKYN said what the ticket is; this says what happens. Returns (outcome, reason)."""
    team = answers["team"]
    pick, conf = team["choice"], team["confidence"]
    refund = answers["wants_refund"]["noul"]
    min_conf, yes_at = policy["team_min_confidence"], policy["refund_yes_at"]
    any_team = policy["refund_from"] == "any_team"
    if refund >= yes_at and (any_team or (pick in policy["refund_from"] and conf >= min_conf)):
        where = "from any team" if any_team else f"team {pick} {conf:.2f} >= {min_conf}"
        return "refunds", f"wants_refund {refund:.2f} >= {yes_at}, {where}"
    if pick == "other":
        return "triage", f"team other {conf:.2f}"
    if conf < min_conf:
        return "triage", f"team {pick} {conf:.2f} < {min_conf}"
    return pick, f"team {pick} {conf:.2f} >= {min_conf}"


def build_state(record):
    return record.get("state") or {"message": record["text"]}


def record(a):
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

    template = json.load(open(a.request))
    policy, policy_hash = load_policy(a.policy)
    kinds = {"choice": Choice, "score": Score, "noul": Noul}
    questions = {k: kinds[q["type"]](instructions=q["instructions"], criteria=q.get("criteria"))
                 for k, q in template["questions"].items()}
    client = TypeSafeClient(timeout=60.0)
    with open(a.out, "w") as out:
        for line in open(a.records):
            if not line.strip():
                continue
            rec = json.loads(line)
            state = build_state(rec)
            res = client.system_one(state=state, questions=questions, model=template.get("model"))
            answers = {}
            for name, ans in res.model_dump()["answers"].items():
                ans.pop("stats", None)
                ans.pop("type", None)
                answers[name] = ans
            outcome, reason = decide(answers, policy)
            row = {
                "case_id": rec["id"], "step": STEP,
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "request_id": res.request_id, "model": res.model,
                # Keep the input itself only where your data policy allows; otherwise its hash and where it lives.
                "input": state, "input_hash": digest(state), "input_ref": f"{a.records}#{rec['id']}",
                "questions": {k: digest(q) for k, q in template["questions"].items()},
                "answers": answers,
                "policy_version": policy["version"], "policy_hash": policy_hash,
                "outcome": outcome, "reason": reason,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Stored audit records in {a.out}.")


def replay(a):
    rows = [json.loads(line) for line in open(a.answers) if line.strip()]
    policy, policy_hash = load_policy(a.policy)
    stale = set()
    if a.request:
        now = {k: digest(q) for k, q in json.load(open(a.request))["questions"].items()}
        for r in rows:
            if any(now.get(k) != h for k, h in r["questions"].items()):
                stale.add(r["case_id"])
    versions = collections.Counter(f"{r['policy_version']} ({r['policy_hash']})" for r in rows)
    print(f"Stored: {len(rows)} cases, step {rows[0]['step']}, decided under " + ", ".join(
        f"{v}: {n}" for v, n in versions.items()))
    print(f"Models in the stored answers: {', '.join(sorted({r['model'] for r in rows}))}")
    print(f"Replaying with: {policy['version']} ({policy_hash}). No model calls.")
    if stale:
        print(f"Skipped {len(stale)} cases: a question changed since they were answered. Re-ask those (drift check).")

    changed, moves = [], collections.Counter()
    for r in rows:
        if r["case_id"] in stale:
            continue
        outcome, reason = decide(r["answers"], policy)
        if outcome != r["outcome"]:
            changed.append((r, outcome, reason))
            moves[(r["outcome"], outcome)] += 1
    n = len(rows) - len(stale)
    print(f"\nOutcome changed: {len(changed)}/{n} cases ({len(changed) / n:.0%})")
    for (old, new), k in moves.most_common():
        print(f"  {old:>9} -> {new:<9} {k}")
    if changed:
        print("\nChanged cases (stored outcome and reason -> new outcome and reason):")
        for r, outcome, reason in changed[: a.show]:
            text = json.dumps(r.get("input", {}), ensure_ascii=False)[:60]
            print(f"  {r['case_id']}  {r['outcome']} ({r['reason']})\n"
                  f"        -> {outcome} ({reason})\n        {text}")
        if len(changed) > a.show:
            print(f"  ... {len(changed) - a.show} more (--show)")
    print("\nA changed outcome is not a better one. Check them against labels: promote.py.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["record", "replay"])
    ap.add_argument("--request", help="record: the questions as the app sends them; replay: check question hashes")
    ap.add_argument("--records", help="record: one case per line, {\"id\", \"text\"} or {\"id\", \"state\"}")
    ap.add_argument("--policy", required=True, help="the versioned thresholds and rules file")
    ap.add_argument("--out", default="answers.jsonl")
    ap.add_argument("--answers", default="answers.jsonl", help="replay: the stored audit records")
    ap.add_argument("--show", type=int, default=30)
    a = ap.parse_args()
    if a.mode == "record":
        if not (a.request and a.records):
            ap.error("record needs --request and --records")
        record(a)
    else:
        replay(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
