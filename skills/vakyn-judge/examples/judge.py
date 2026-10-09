"""Grade a JSONL file of chat-model or agent outputs against the support-reply rubric.

Usage:
    python3 judge.py replies.sample.jsonl [--out grades.jsonl] [--concurrency 4]

Each input line: {"id": "...", "input": "the customer's message", "output": "the reply to grade"}.
Each output line: the per-criterion results, the overall verdict, the request id.
One output per request, every criterion in that request. The verdict is computed in code (rubric.py).
Needs: pip install typesafe-sdk; TYPESAFE_BASE_URL and TYPESAFE_API_KEY in the environment.
"""

import argparse
import asyncio
import json
import time

from typesafe_sdk import AsyncTypeSafeClient, Noul, Score, TypeSafeRateLimitError

from rubric import CRITERIA, answers_from_response, build_state, criterion_results, overall


def sdk_questions(criteria=CRITERIA):
    qs = {}
    for name, c in criteria.items():
        if c["type"] == "noul":
            qs[name] = Noul(instructions=c["instructions"], criteria=c.get("criteria"))
        else:
            qs[name] = Score(instructions=c["instructions"], criteria=c["criteria"])
    return qs


async def ask(client, item, criteria=CRITERIA):
    """One request for one output. Returns (answers dict, request id)."""
    for wait in (2, 5, 10, 20, None):  # the SDK retries 429 twice; a busy shared server can stay full longer
        try:
            r = await client.system_one(state=build_state(item), questions=sdk_questions(criteria))
            return answers_from_response(r, criteria), r.request_id
        except TypeSafeRateLimitError:
            if wait is None:
                raise
            await asyncio.sleep(wait)


async def grade(client, item, criteria=CRITERIA):
    answers, request_id = await ask(client, item, criteria)
    results = criterion_results(answers, criteria)
    return {"id": item["id"], **overall(results, criteria), "criteria": results, "request_id": request_id}


async def grade_all(items, concurrency=4):
    client = AsyncTypeSafeClient(timeout=60.0)
    gate = asyncio.Semaphore(concurrency)

    async def one(item):
        async with gate:
            return await grade(client, item)

    return await asyncio.gather(*(one(i) for i in items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default="grades.jsonl")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()

    items = [json.loads(line) for line in open(a.file) if line.strip()]
    start = time.perf_counter()
    grades = asyncio.run(grade_all(items, a.concurrency))
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
