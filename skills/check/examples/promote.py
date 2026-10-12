"""Promote a new decision version only if it is better: dev set to tune on, reserved set to confirm.

Usage:
    python3 promote.py --answers answers.jsonl --labels labels.jsonl \
        --current routing-policy.v1.json --candidate routing-policy.v2.json \
        [--reserved-share 0.3] [--log promotions.jsonl]

answers.jsonl: stored audit records (replay.py record). labels.jsonl: what a person says the right
outcome is, {"case_id": "t001", "outcome": "refunds"}. Both versions are decided from the same
stored answers with replay.decide(), so this makes no model calls.

Each case goes to the dev set or the reserved set by a hash of its id, so the split never changes
between runs. Tune on the dev set: its cases are listed. The reserved set is only counted, never
listed: read nothing case by case from it, or it becomes a second dev set.

A version is better when it decides fewer cases wrongly (an automatic outcome that differs from the
label), or as many and sends fewer to a person. Promote when the candidate is better on the dev set
and not worse on the reserved set. Then, on the wrongly decided dev cases of the version that will be
live, it prints each question's mean confidence: the lowest is the question to rewrite first.
Exits 0 to promote, 1 to keep the current version. Standard library only (plus replay.py).
"""

import argparse
import datetime
import hashlib
import json
import sys

from replay import decide, load_policy

PERSON = "triage"  # the outcome that sends a case to a person


def reserved(case_id, share):
    return int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) % 1000 < share * 1000


def score(rows, labels, policy):
    wrong, person, right, per_case = 0, 0, 0, {}
    for r in rows:
        outcome, reason = decide(r["answers"], policy)
        label = labels[r["case_id"]]
        if outcome == label:
            right += 1
        elif outcome == PERSON:
            person += 1
        else:
            wrong += 1
        per_case[r["case_id"]] = (outcome, reason)
    return {"wrong": wrong, "person": person, "right": right, "n": len(rows)}, per_case


def better(a, b):
    """a is better than b."""
    return (a["wrong"], a["person"]) < (b["wrong"], b["person"])


def not_worse(a, b):
    return (a["wrong"], a["person"]) <= (b["wrong"], b["person"])


def line(name, s):
    return f"  {name:<12} wrong {s['wrong']:>3}   to a person {s['person']:>3}   right {s['right']:>3} of {s['n']}"


def confidence(name, answer):
    if "noul" in answer:
        return abs(2 * answer["noul"] - 1)
    return answer["confidence"]


def weakest_question(rows, labels, per_case):
    wrong = [r for r in rows if per_case[r["case_id"]][0] not in (labels[r["case_id"]], PERSON)]
    if not wrong:
        print("\nNo wrongly decided dev cases: nothing to diagnose.")
        return
    print(f"\nMean confidence per question on the {len(wrong)} wrongly decided dev cases (lowest: rewrite it first):")
    names = sorted(wrong[0]["answers"])
    means = {q: sum(confidence(q, r["answers"][q]) for r in wrong) / len(wrong) for q in names}
    rest = [r for r in rows if r not in wrong]
    for q in sorted(names, key=means.get):
        other = sum(confidence(q, r["answers"][q]) for r in rest) / len(rest) if rest else float("nan")
        print(f"  {q:<14} {means[q]:.2f}   (on the other dev cases: {other:.2f})")
    for r in wrong:
        outcome, reason = per_case[r["case_id"]]
        print(f"  {r['case_id']}: decided {outcome} ({reason}), label {labels[r['case_id']]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--current", required=True, help="policy file of the version in use")
    ap.add_argument("--candidate", required=True, help="policy file of the proposed version")
    ap.add_argument("--reserved-share", type=float, default=0.3)
    ap.add_argument("--log", help="append the result here, to keep the evidence behind each promotion")
    a = ap.parse_args()

    labels = {r["case_id"]: r["outcome"] for r in map(json.loads, open(a.labels)) if r.get("outcome")}
    rows = [r for r in map(json.loads, open(a.answers)) if r["case_id"] in labels]
    dev = [r for r in rows if not reserved(r["case_id"], a.reserved_share)]
    res = [r for r in rows if reserved(r["case_id"], a.reserved_share)]
    cur, cur_hash = load_policy(a.current)
    cand, cand_hash = load_policy(a.candidate)
    print(f"{len(rows)} labeled cases: {len(dev)} dev, {len(res)} reserved (split by a hash of the case id).")

    dev_cur, dev_cur_cases = score(dev, labels, cur)
    dev_cand, dev_cand_cases = score(dev, labels, cand)
    print(f"\nDev set ({len(dev)} cases)")
    print(line(cur["version"], dev_cur))
    print(line(cand["version"], dev_cand))
    moved = [r for r in dev if dev_cur_cases[r["case_id"]][0] != dev_cand_cases[r["case_id"]][0]]
    for r in moved:
        cid = r["case_id"]
        print(f"    {cid}: {dev_cur_cases[cid][0]} -> {dev_cand_cases[cid][0]}  (label {labels[cid]})")

    res_cur, _ = score(res, labels, cur)
    res_cand, _ = score(res, labels, cand)
    print(f"\nReserved set ({len(res)} cases; counts only)")
    print(line(cur["version"], res_cur))
    print(line(cand["version"], res_cand))

    dev_ok, res_ok = better(dev_cand, dev_cur), not_worse(res_cand, res_cur)
    promote = dev_ok and res_ok
    print(f"\nBetter on dev: {'yes' if dev_ok else 'no'}. Not worse on reserved: {'yes' if res_ok else 'no'}.")
    print(f"Verdict: {'PROMOTE ' + cand['version'] if promote else 'KEEP ' + cur['version']}")
    if dev_ok and not res_ok:
        print("Better on dev but worse on reserved: the change fits the dev cases, not the flow. Do not promote.")

    live = cand if promote else cur
    weakest_question(dev, labels, dev_cand_cases if promote else dev_cur_cases)
    if a.log:
        with open(a.log, "a") as f:
            f.write(json.dumps({
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "current": f"{cur['version']} ({cur_hash})", "candidate": f"{cand['version']} ({cand_hash})",
                "dev": {"current": dev_cur, "candidate": dev_cand},
                "reserved": {"current": res_cur, "candidate": res_cand},
                "verdict": "promote" if promote else "keep", "live": live["version"]}) + "\n")
    return 0 if promote else 1


if __name__ == "__main__":
    sys.exit(main())
