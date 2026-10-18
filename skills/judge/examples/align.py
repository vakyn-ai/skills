"""Measure how well VAKYN's grades match your experts, per criterion, without tuning on what you report.

Usage:
    python3 align.py                         # offline: stored answers in vakyn-answers.sample.jsonl
    python3 align.py --draft first           # the first draft of the rubric
    python3 align.py --compare first aligned # both drafts, held-out part only
    python3 align.py --live                  # grade every item with VAKYN (spends balance on VAKYN Cloud), store the answers
    python3 align.py --target 0.9            # the agreement you need per criterion

Expert labels, one line per graded output (expert-labels.sample.jsonl):
    {"id": "r02", "input": "...", "output": "...",
     "pass": {"answers_request": false, "next_step": false, ...},
     "reasons": {"next_step": "No owner, no time, nothing the customer can do."}}

The labels are split once, at random with a fixed seed: about 70% to read disagreements and rewrite
criteria on ("tune"), 30% held out to report on ("check"). Disagreements are only ever shown from the
tune part. --live needs typesafe-sdk, TYPESAFE_BASE_URL and TYPESAFE_API_KEY; offline needs nothing.
"""

import argparse
import asyncio
import json
import pathlib
import random

from rubric import NOUL_NO, NOUL_YES, criteria_for

HERE = pathlib.Path(__file__).parent
LABELS = HERE / "expert-labels.sample.jsonl"
ANSWERS = HERE / "vakyn-answers.sample.jsonl"


def load_jsonl(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def split(items, holdout, seed):
    ids = sorted(i["id"] for i in items)
    random.Random(seed).shuffle(ids)
    k = round(len(ids) * holdout)
    return set(ids[k:]), set(ids[:k])  # tune, check


def vakyn_pass(answer, c):
    """VAKYN's pass/fail for one criterion, and whether it sits in the unsure band."""
    if c["type"] == "noul":
        p = answer["noul"] if c["pass_when"] else 1 - answer["noul"]
        return p >= 0.5, NOUL_NO < p < NOUL_YES
    return answer["score"] >= c["pass_at"], False


def measure(items, answers, criteria):
    """Per criterion: agreement, false pass (VAKYN pass, expert fail), false fail, unsure, with counts."""
    rows = {}
    for name, c in criteria.items():
        n = agree = false_pass = false_fail = unsure = 0
        misses = []
        for it in items:
            a = answers.get(it["id"])
            if a is None:
                continue
            got, in_band = vakyn_pass(a[name], c)
            want = it["pass"][name]
            n += 1
            unsure += in_band
            if got == want:
                agree += 1
            else:
                false_pass += got and not want
                false_fail += want and not got
                misses.append((it, got, a[name]))
        rows[name] = {"n": n, "agree": agree, "false_pass": false_pass, "false_fail": false_fail,
                      "unsure": unsure, "misses": misses}
    return rows


def print_table(rows, title, target):
    print(f"\n{title}")
    print(f"{'criterion':<17}{'n':>4}{'agree':>7}{'rate':>7}{'false pass':>12}{'false fail':>12}{'unsure':>8}  target")
    for name, r in rows.items():
        rate = r["agree"] / r["n"] if r["n"] else 0.0
        ok = "meets" if rate >= target else "below"
        print(f"{name:<17}{r['n']:>4}{r['agree']:>7}{rate:>7.0%}{r['false_pass']:>12}{r['false_fail']:>12}{r['unsure']:>8}  {ok}")


def print_disagreements(rows):
    print("\nDisagreements on the tune part (rewrite the criterion text from these, then re-check on held-out):")
    for name, r in rows.items():
        for it, got, a in r["misses"]:
            shown = f"noul {a['noul']:.2f}" if "noul" in a else f"score {a['score']:.2f}"
            print(f"- {name} {it['id']}: VAKYN {'pass' if got else 'fail'} ({shown}), expert "
                  f"{'pass' if it['pass'][name] else 'fail'}: {it.get('reasons', {}).get(name, '(the expert gave no reason)')}")
            print(f"    output: {it['output'][:110]}")


async def grade_live(items, draft, concurrency=2):
    from typesafe_sdk import AsyncTypeSafeClient

    from judge import ask  # one output per request, every criterion in it, 429 retry

    criteria = criteria_for(draft)
    client = AsyncTypeSafeClient(timeout=60.0)
    gate = asyncio.Semaphore(concurrency)

    async def one(it):
        async with gate:
            answers, request_id = await ask(client, it, criteria)
        return {"id": it["id"], "draft": draft, "request_id": request_id, "answers": answers}

    return await asyncio.gather(*(one(it) for it in items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", default="aligned", choices=["first", "aligned"])
    ap.add_argument("--compare", nargs=2, metavar="DRAFT")
    ap.add_argument("--target", type=float, default=0.9, help="agreement you need per criterion")
    ap.add_argument("--holdout", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--live", action="store_true", help="grade with VAKYN and rewrite the stored answers")
    a = ap.parse_args()

    items = load_jsonl(LABELS)
    if a.live:
        lines = []
        for draft in ("first", "aligned"):
            lines += asyncio.run(grade_live(items, draft))
        ANSWERS.write_text("".join(json.dumps(x) + "\n" for x in lines))
        print(f"Stored {len(lines)} answers in {ANSWERS.name}")

    stored = load_jsonl(ANSWERS)
    tune_ids, check_ids = split(items, a.holdout, a.seed)
    tune = [i for i in items if i["id"] in tune_ids]
    check = [i for i in items if i["id"] in check_ids]
    by_draft = {}
    for x in stored:
        by_draft.setdefault(x["draft"], {})[x["id"]] = x["answers"]
    print(f"{len(items)} labeled outputs: {len(tune)} to tune on, {len(check)} held out.")
    if len(check) < 50:
        print("Small sample: treat these rates as a first look (see the check thresholds page for sizes).")

    if a.compare:
        for d in a.compare:
            print_table(measure(check, by_draft[d], criteria_for(d)), f"Held out, draft '{d}'", a.target)
        return
    criteria = criteria_for(a.draft)
    rows = measure(tune, by_draft[a.draft], criteria)
    print_table(rows, f"Tune part, draft '{a.draft}'", a.target)
    print_disagreements(rows)
    print_table(measure(check, by_draft[a.draft], criteria), f"Held out, draft '{a.draft}' (report this one)", a.target)


if __name__ == "__main__":
    main()
