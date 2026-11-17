"""Grade a JSONL file of chat-model or agent outputs against the support-reply rubric.

Usage:
    python3 judge.py replies.sample.jsonl [--out grades.jsonl] [--concurrency 4]

Each input line: {"id": "...", "input": "the customer's message", "output": "the reply to grade"}.
Each output line: the per-criterion results, the overall verdict, the request id.
One output per request, every criterion in that request. The verdict is computed in code (rubric.py).
Needs: Python 3 only; VAKYN_API_KEY in the environment (VAKYN_BASE_URL if not VAKYN Cloud).
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from rubric import CRITERIA, answers_from_response, build_state, criterion_results, overall, request_body

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def ask(item, criteria=CRITERIA, timeout=60):
    """One request for one output. Returns (answers dict, request id)."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps(request_body(item, criteria)).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    for wait in (2, 5, 10, 20, None):  # a busy shared server can stay full for a while
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                answers = json.load(r)["answers"]
                return answers_from_response(answers, criteria), r.headers.get("x-vakyn-request-id")
        except urllib.error.HTTPError as e:
            if wait is None or not (e.code == 429 or e.code >= 500):
                raise
            time.sleep(float(e.headers.get("retry-after") or wait))


def grade(item, criteria=CRITERIA):
    answers, request_id = ask(item, criteria)
    results = criterion_results(answers, criteria)
    return {"id": item["id"], **overall(results, criteria), "criteria": results, "request_id": request_id}


def grade_all(items, concurrency=4, criteria=CRITERIA):
    """Grade every item, at most `concurrency` requests at a time, results in input order."""
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(pool.map(lambda item: grade(item, criteria), items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default="grades.jsonl")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()

    items = [json.loads(line) for line in open(a.file) if line.strip()]
    start = time.perf_counter()
    grades = grade_all(items, a.concurrency)
    took = time.perf_counter() - start
    with open(a.out, "w") as f:
        for g in grades:
            f.write(json.dumps(g) + "\n")

    for g in grades:
        detail = ", ".join(f"{n} {r['verdict']}" for n, r in g["criteria"].items() if r["verdict"] != "pass")
        print(f"{g['id']:<6} {g['verdict']:<7} weighted {g['weighted']:.2f}  {detail or 'all criteria pass'}")
    n = len(grades)
    counts = {v: sum(g["verdict"] == v for g in grades) for v in ("pass", "fail", "review")}
    print(f"\n{n} outputs: {counts['pass']} pass, {counts['fail']} fail, {counts['review']} to a person "
          f"(pass rate {counts['pass'] / n:.0%}). {took:.1f} s wall time at concurrency {a.concurrency}. "
          f"Grades in {a.out}.")


if __name__ == "__main__":
    main()
