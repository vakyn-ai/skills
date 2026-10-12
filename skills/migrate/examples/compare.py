"""Replay saved decision requests against two Jev-compatible servers and report how often they agree.

Use it before switching: A is where the requests go today, B is the person's own open-server.

Usage:
    python3 compare.py recorded.jsonl --a https://old.example --b http://127.0.0.1:8080 \
        [--a-model NAME] [--b-model jev-latest] [--a-key-env OLD_API_KEY] [--b-key-env VAKYN_API_KEY] \
        [--n 30] [--out compare-results.jsonl] [--dry]
    python3 compare.py recorded.jsonl --a recorded --b http://127.0.0.1:8080   # A = answers saved in the file

recorded.jsonl: one request per line, either a bare /v1/systemone body or
    {"id": "...", "request": {...}, "old_answers": {...}}   ("old_answers" only with --a recorded:
    the `answers` object the old service returned, taken from the person's logs).

Base URLs are server roots; the script adds /v1/systemone. Keys are read from the environment
variables named by --a-key-env and --b-key-env and never printed.
--dry sends nothing: it checks every line and prints what would be sent where.
Standard library only. Each request is sent once per side; nothing is rerun.
Agreement is not accuracy: two models can be wrong the same way. Labels decide who is right.
"""

import argparse
import collections
import concurrent.futures
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request


def load(path, n):
    rows = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if "request" not in row:
                row = {"id": f"line-{i}", "request": row}
            row.setdefault("id", f"line-{i}")
            rows.append(row)
    return rows[:n]


def check_row(row):
    req = row["request"]
    problems = [f"missing {k}" for k in ("state", "questions") if req.get(k) is None]
    for qid, q in (req.get("questions") or {}).items():
        if q.get("type") not in ("noul", "choice", "score"):
            problems.append(f"{qid}: type {q.get('type')!r} is not noul, choice or score")
    return problems


def send(base, key, body, timeout):
    """POST once; wait and retry only on 429/503 (server asked us to). Returns (status, json, seconds, request_id)."""
    data = json.dumps(body).encode()
    for attempt in range(4):
        req = urllib.request.Request(f"{base}/v1/systemone", data=data, headers={
            "content-type": "application/json", "authorization": f"Bearer {key}"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read()), time.perf_counter() - t0, r.headers.get("x-typesafe-request-id")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(float(e.headers.get("retry-after") or 2))
                continue
            return e.code, {"error": e.read()[:300].decode(errors="replace")}, time.perf_counter() - t0, None
        except (urllib.error.URLError, OSError) as e:
            return 0, {"error": str(e)}, time.perf_counter() - t0, None
    return 0, {"error": "gave up after retries"}, 0.0, None


def top_level(a):
    probs = a.get("probabilities") or {}
    return max(probs, key=probs.get) if probs else str(round(a["score"]))


def compare_answer(q, a, b):
    """Returns (agree, detail) for one question."""
    if q["type"] == "noul":
        return (a["noul"] >= 0.5) == (b["noul"] >= 0.5), {"a": a["noul"], "b": b["noul"]}
    if q["type"] == "choice":
        return a["choice"] == b["choice"], {"a": a["choice"], "a_conf": a.get("confidence"),
                                            "b": b["choice"], "b_conf": b.get("confidence")}
    return top_level(a) == top_level(b), {"a": a["score"], "b": b["score"],
                                          "a_level": top_level(a), "b_level": top_level(b)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--a", required=True, help="old base URL, or 'recorded' to use old_answers from the file")
    p.add_argument("--b", required=True, help="new base URL (the person's open-server)")
    p.add_argument("--a-model", help="model name for A (default: the model in each request)")
    p.add_argument("--b-model", default="jev-latest")
    p.add_argument("--a-key-env", default="OLD_API_KEY")
    p.add_argument("--b-key-env", default="VAKYN_API_KEY")
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--out", default="compare-results.jsonl")
    p.add_argument("--dry", action="store_true", help="check the file and print the plan; send nothing")
    args = p.parse_args()

    rows = load(args.file, args.n)
    bad = [(r["id"], pr) for r in rows for pr in check_row(r)]
    recorded = args.a == "recorded"
    if recorded:
        bad += [(r["id"], "no old_answers for --a recorded") for r in rows if "old_answers" not in r]
    sides = {"A": "answers saved in the file" if recorded else f"{args.a.rstrip('/')}/v1/systemone",
             "B": f"{args.b.rstrip('/')}/v1/systemone"}
    nq = sum(len(r["request"]["questions"]) for r in rows)
    print(f"{len(rows)} requests, {nq} questions")
    print(f"A: {sides['A']}" + ("" if recorded else f"  model={args.a_model or 'as in each request'}  key=${args.a_key_env}"))
    print(f"B: {sides['B']}  model={args.b_model}  key=${args.b_key_env}")
    for rid, pr in bad:
        print(f"  problem {rid}: {pr}")
    if args.dry or bad:
        print("dry run: nothing sent" if args.dry else "fix the problems above first; nothing sent")
        return 0 if args.dry and not bad else 1

    keys = {}
    for side, env in (("A", args.a_key_env), ("B", args.b_key_env)):
        if side == "A" and recorded:
            continue
        keys[side] = os.environ.get(env, "")
        if not keys[side]:
            print(f"set {env} (the key for side {side}); it is read from the environment and never printed")
            return 1

    def run(row):
        out = {"id": row["id"]}
        for side, base, model in (("A", args.a, args.a_model), ("B", args.b, args.b_model)):
            if side == "A" and recorded:
                out["A"] = {"status": 200, "answers": row["old_answers"], "seconds": None}
                continue
            body = dict(row["request"])
            if model:
                body["model"] = model
            status, res, secs, rid = send(base.rstrip("/"), keys[side], body, args.timeout)
            out[side] = {"status": status, "seconds": round(secs, 3), "request_id": rid,
                         "model": res.get("model"), "answers": res.get("answers"), "error": res.get("error")}
        return out

    with concurrent.futures.ThreadPoolExecutor(args.concurrency) as pool:
        results = list(pool.map(run, rows))

    per_q = collections.defaultdict(lambda: [0, 0])
    disagreements, failed = [], 0
    with open(args.out, "w") as f:
        for row, res in zip(rows, results):
            ok = res["A"]["status"] == 200 and res["B"]["status"] == 200
            res["compare"] = {}
            if not ok:
                failed += 1
            else:
                for qid, q in row["request"]["questions"].items():
                    agree, detail = compare_answer(q, res["A"]["answers"][qid], res["B"]["answers"][qid])
                    per_q[qid][0] += agree
                    per_q[qid][1] += 1
                    res["compare"][qid] = {"agree": agree, **detail}
                    if not agree:
                        disagreements.append((row["id"], qid, detail))
            f.write(json.dumps(res) + "\n")

    print(f"\nanswered by both: {len(rows) - failed}/{len(rows)}  (failed lines: {failed}; see {args.out})")
    for row, res in zip(rows, results):
        for side in ("A", "B"):
            if res[side]["status"] != 200:
                print(f"  {row['id']} {side}: HTTP {res[side]['status']} {str(res[side]['error'])[:120]}")
    print("\nagreement per question (noul: same side of 0.5; choice: same pick; score: same top level)")
    for qid, (agree, total) in per_q.items():
        print(f"  {qid:<20} {agree}/{total}  {100 * agree / total:.0f}%")
    for side in ("A", "B"):
        secs = [r[side]["seconds"] for r in results if r[side]["status"] == 200 and r[side]["seconds"] is not None]
        if secs:
            print(f"time per request {side}: median {statistics.median(secs):.2f} s, max {max(secs):.2f} s "
                  f"(this run, this machine, concurrency {args.concurrency})")
    print(f"\ndisagreements: {len(disagreements)}")
    for rid, qid, detail in disagreements:
        print(f"  {rid} {qid}: {json.dumps(detail)}")
    print("\nAgreement is not accuracy. Label the disagreements to see which side is right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
