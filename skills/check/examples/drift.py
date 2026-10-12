"""Drift check: re-run a stored reference batch and report what changed.

Usage:
    # once, on the setup you trust: store the answers
    python3 drift.py save  --request drift.request.json --records records.jsonl --out reference.jsonl
    # after a change (model file, server version, question text, state builder): compare
    python3 drift.py check --request drift.request.json --records records.jsonl --reference reference.jsonl
        [--tolerance 0.05] [--max-pick-changes 0.02] [--max-mean-change 0.02] [--max-crossing 0.02]
        [--threshold 0.8] [--noul-band 0.2,0.8] [--concurrency 1] [--out current.jsonl]

records.jsonl: one record per line, {"id": "...", "text": "..."} or {"id": "...", "state": {...}}.
build_state() below turns a record into the state; edit it to match your app's state builder.
Every question in the request file is asked in one request per record, as the app does.

Each stored line holds the record id, question name, a hash of the question text, the answer
(pick, confidence, probabilities or noul), the request id, the model name from the response, and
the served model file as /v1/models describes it.

check exits 1 when a limit is broken, so it can fail a CI job. Changes no bigger than --tolerance
(on every probability) with the same pick are treated as run-to-run noise. Keep --concurrency at
1 or 2: under heavier concurrent load the numbers can move slightly between runs.

Needs: pip install typesafe-sdk; TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import json
import sys

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient


def build_state(record):
    """Your app's state builder. Change this when the app's changes; that is a drift check too."""
    return record.get("state") or {"message": record["text"]}


def question_hash(q):
    return hashlib.sha256(json.dumps(q, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def sdk_question(q):
    if q["type"] == "choice":
        return Choice(instructions=q["instructions"], criteria=q["criteria"])
    if q["type"] == "score":
        return Score(instructions=q["instructions"], criteria=q["criteria"])
    return Noul(instructions=q["instructions"], criteria=q.get("criteria"))


def served_model_file(client, name):
    """What /v1/models says about the served model (for open-server: file format and quantization)."""
    try:
        models = {m.name: m.description for m in client.models.list().models}
    except Exception as e:  # keep going; the model name from each answer is still stored
        return f"unknown ({type(e).__name__})"
    desc = models.get(name, "")
    if desc.startswith("Alias for "):
        desc = models.get(desc.removeprefix("Alias for ").rstrip("."), desc)
    return desc


def ask(client, template, record):
    questions = {k: sdk_question(q) for k, q in template["questions"].items()}
    res = client.system_one(state=build_state(record), questions=questions, model=template.get("model"))
    answers = res.model_dump()["answers"]
    rows = []
    for name, q in template["questions"].items():
        a = answers[name]
        row = {"id": record["id"], "question": name, "question_hash": question_hash(q), "type": q["type"],
               "request_id": res.request_id, "model": res.model}
        if q["type"] == "noul":
            row.update(noul=a["noul"], pick=a["noul"] >= 0.5, confidence=round(abs(2 * a["noul"] - 1), 2),
                       probabilities={"true": a["noul"], "false": round(1 - a["noul"], 2)})
        elif q["type"] == "score":
            top = max(a["probabilities"], key=a["probabilities"].get)
            row.update(pick=q["criteria"][int(top)], score=a["score"], confidence=a["confidence"],
                       probabilities=a["probabilities"])
        else:
            row.update(pick=a["choice"], confidence=a["confidence"], probabilities=a["probabilities"])
        rows.append(row)
    return rows


def run(a):
    template = json.load(open(a.request))
    records = [json.loads(line) for line in open(a.records) if line.strip()]
    if a.limit:
        records = records[: a.limit]
    if a.concurrency > 2:
        print(f"Note: concurrency {a.concurrency}. Above 2 in flight, numbers can move slightly between runs; "
              "use 1 or 2 for reference batches.", file=sys.stderr)
    client = TypeSafeClient(timeout=60.0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        results = list(pool.map(lambda r: ask(client, template, r), records))
    rows = [row for rs in results for row in rs]
    model_file = a.model_file or served_model_file(client, rows[0]["model"]) if rows else ""
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    for row in rows:
        row.update(model_file=model_file, server_version=a.server_version, saved_at=stamp)
    return rows


def write(rows, path):
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def largest_move(old, new):
    keys = set(old["probabilities"]) | set(new["probabilities"])
    return round(max(abs(old["probabilities"].get(k, 0.0) - new["probabilities"].get(k, 0.0)) for k in keys), 2)


def show(pick):
    return json.dumps(pick) if isinstance(pick, bool) else str(pick)


def acted(row, a):
    """'yes' / 'no' / the pick when the app acts on it alone, 'unsure' when it goes to the unsure path."""
    if row["type"] == "noul":
        lo, hi = a.noul_band
        return "yes" if row["noul"] >= hi else "no" if row["noul"] <= lo else "unsure"
    return row["pick"] if row["confidence"] >= a.threshold else "unsure"


def compare(ref, cur, a):
    failed = False
    meta = lambda rows, k: sorted({str(r.get(k)) for r in rows})
    print("Setup        reference -> now")
    for k in ("model", "model_file", "server_version"):
        old, new = meta(ref, k), meta(cur, k)
        print(f"  {k:<14} {', '.join(old)} -> {', '.join(new)}{'   CHANGED' if old != new else ''}")
    ref_by = {(r["id"], r["question"]): r for r in ref}
    cur_by = {(r["id"], r["question"]): r for r in cur}
    questions = sorted({q for _, q in ref_by} | {q for _, q in cur_by})
    for q in questions:
        old_rows = [r for k, r in ref_by.items() if k[1] == q]
        new_rows = [r for k, r in cur_by.items() if k[1] == q]
        print(f"\n=== question: {q} ===")
        if not old_rows or not new_rows:
            print("  only in the " + ("new run" if new_rows else "reference") + "; nothing to compare")
            continue
        oh, nh = meta(old_rows, "question_hash"), meta(new_rows, "question_hash")
        print(f"  question text: {'CHANGED' if oh != nh else 'same'} ({', '.join(oh)} -> {', '.join(nh)})")
        pairs = [(ref_by[k], cur_by[k]) for k in ref_by if k[1] == q and k in cur_by]
        missing = len(old_rows) - len(pairs)
        n = len(pairs)
        moves = [(largest_move(o, c), o, c) for o, c in pairs]
        mean_move = sum(m for m, _, _ in moves) / n
        flips = [(m, o, c) for m, o, c in moves if o["pick"] != c["pick"] and m > a.tolerance]
        near = [(m, o, c) for m, o, c in moves if o["pick"] != c["pick"] and m <= a.tolerance]
        real = [(m, o, c) for m, o, c in moves if m > a.tolerance]
        crossing = [(m, o, c) for m, o, c in real if acted(o, a) != acted(c, a)]
        print(f"  compared {n} records" + (f" ({missing} missing from the new run)" if missing else ""))
        print(f"  picks changed:              {len(flips)}/{n} ({len(flips) / n:.1%})  [limit {a.max_pick_changes:.1%}]")
        print(f"  mean absolute change:       {mean_move:.3f}  (largest probability move per record) "
              f"[limit {a.max_mean_change:.3f}]")
        print(f"  moved more than {a.tolerance:.2f}:       {len(real)}/{n}; at or below it counts as noise")
        print(f"  crossed the threshold:      {len(crossing)}/{n} ({len(crossing) / n:.1%})  [limit {a.max_crossing:.1%}]")
        if near:
            print(f"  near ties that flipped within noise: {len(near)} (re-check these by hand)")
        counts_old = collections.Counter(show(o["pick"]) for o, _ in pairs)
        counts_new = collections.Counter(show(c["pick"]) for _, c in pairs)
        options = sorted(set(counts_old) | set(counts_new))
        shift = sum(abs(counts_old[k] - counts_new[k]) for k in options) / (2 * n)
        print(f"  picks per option (reference -> now), shift {shift:.1%}:")
        for k in options:
            print(f"    {k:<12} {counts_old[k]:>4} -> {counts_new[k]:<4}")
        if real:
            print("  changed records, biggest first:")
            for m, o, c in sorted(real, key=lambda x: -x[0])[: a.show]:
                print(f"    {o['id']:<8} {show(o['pick']):<10} {o['confidence']:.2f} -> {show(c['pick']):<10} "
                      f"{c['confidence']:.2f}  move {m:.2f}  {acted(o, a)} -> {acted(c, a)}")
        bad = []
        if len(flips) / n > a.max_pick_changes:
            bad.append("picks changed")
        if mean_move > a.max_mean_change:
            bad.append("mean change")
        if len(crossing) / n > a.max_crossing:
            bad.append("threshold crossings")
        print(f"  result: {'FAIL (' + ', '.join(bad) + ')' if bad else 'pass'}")
        failed |= bool(bad)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["save", "check"])
    ap.add_argument("--request", required=True, help="request file with the questions as the app sends them")
    ap.add_argument("--records", required=True)
    ap.add_argument("--reference", default="reference.jsonl", help="check: the stored reference batch")
    ap.add_argument("--out", help="where to write this run's answers (save: the reference batch)")
    ap.add_argument("--limit", type=int, help="only the first N records")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--model-file", help="model file and quantization, when /v1/models does not say")
    ap.add_argument("--server-version", default="", help="server version or image tag, for the record")
    ap.add_argument("--tolerance", type=float, default=0.05, help="moves at or below this are noise")
    ap.add_argument("--threshold", type=float, default=0.8, help="choice/score: the app acts at or above this")
    ap.add_argument("--noul-band", default="0.2,0.8", help="noul: acts on no at or below lo, on yes at or above hi")
    ap.add_argument("--max-pick-changes", type=float, default=0.02, help="share of picks allowed to change")
    ap.add_argument("--max-mean-change", type=float, default=0.02, help="mean largest probability move allowed")
    ap.add_argument("--max-crossing", type=float, default=0.02, help="share allowed to cross the threshold")
    ap.add_argument("--show", type=int, default=20, help="how many changed records to list per question")
    a = ap.parse_args()
    a.noul_band = tuple(float(x) for x in a.noul_band.split(","))

    rows = run(a)
    if a.mode == "save":
        out = a.out or "reference.jsonl"
        write(rows, out)
        print(f"Saved {len(rows)} answers ({len({r['id'] for r in rows})} records) to {out}. "
              f"Model {rows[0]['model']}, {rows[0]['model_file']}.")
        return 0
    if a.out:
        write(rows, a.out)
    ref = [json.loads(line) for line in open(a.reference) if line.strip()]
    failed = compare(ref, rows, a)
    print("\nDRIFT CHECK FAILED: a limit is broken. Review the changed records before shipping." if failed
          else "\nDrift check passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
