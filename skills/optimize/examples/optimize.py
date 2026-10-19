"""Tune the wording of one VAKYN question from labeled cases: measure, keep only what scores better.

Usage:
    # 1. check the inputs, split, print the call estimate, score the current wording on dev
    python3 optimize.py start --request intent.v1.request.json --cases cases.jsonl \
        [--model vakyn-fast] [--rounds 5] [--max-calls 2000] [--confirm-above 300] [--yes] \
        [--threshold 0.5] [--metric accuracy|ap] [--reserved-share 0.3] [--run optimize-run]
    # 2. each round: write a candidate as a new file, then score it on dev (kept only if better)
    python3 optimize.py try --candidate intent.v2.request.json \
        --rule "BIL -> ACC: a refund for a charge is BIL even when the person also mentions the app" [--run ...]
    # 3. once, at the end: score the start and the best wording on the reserved set, decide, write the report
    python3 optimize.py finish [--log promotions.jsonl] [--run ...]

The request file holds the model and exactly one question (noul, choice or score); each case's
state replaces its example state. cases.jsonl, one case per line:
    {"id": "c001", "text": "...", "label": "BIL"}          choice: the option key
    {"id": "c002", "state": {...}, "label": true}         noul: true or false
    {"id": "c003", "text": "...", "label": 2}             score: the level index, 0 = first level
build_state() below turns a case into the state; edit it to match your app's state builder.

Cases go to the dev set or the reserved set by a hash of the case id (the same split as check's
promote.py), so the split never changes between runs. Rounds only ever send dev cases. The reserved
set is sent once, by finish, and only its counts are printed. Answers are stored in the run folder
(answers.jsonl) by wording hash, model and case id: nothing is asked twice, and a run can be replayed
from stored answers with no key.

Promotion follows check: better on dev and not worse on reserved. The question name and the option
keys must stay the same; try refuses a candidate that changes them.

Needs TYPESAFE_BASE_URL (default https://api.vakyn.com, or your own server) and TYPESAFE_API_KEY in
the environment, unless every answer is already stored. Standard library only.
"""

import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

MIN_CASES = 50
MIN_PER_CLASS = 5
OVERFIT_GAP = 0.10  # dev gained this much more than reserved: the wording fits the dev cases


class Stop(Exception):
    """A clear reason to stop (bad key, rate limit, call budget); printed without a traceback."""


def build_state(case):
    """Your app's state builder. The same one the live flow uses, so the wording is tuned on real input."""
    return case.get("state") or {"message": case["text"]}


def reserved(case_id, share):
    return int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) % 1000 < share * 1000


def load_request(path):
    req = json.loads(pathlib.Path(path).read_text())
    if len(req.get("questions", {})) != 1:
        raise Stop(f"{path}: put exactly one question in the request; tune one question at a time")
    (name, q), = req["questions"].items()
    return req, name, q


def wording_hash(q):
    return hashlib.sha256(json.dumps(q, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def wording_size(q):
    return len(json.dumps({"instructions": q.get("instructions"), "criteria": q.get("criteria")}, ensure_ascii=False))


def keys_of(q):
    c = q.get("criteria")
    if q["type"] == "choice":
        return sorted(c)
    if q["type"] == "score":
        return len(c)  # levels are read by index: the count must stay
    return None


# ---------- calls ----------

class Client:
    def __init__(self, run_dir, model, max_calls, concurrency=8, timeout=60):
        self.base = os.environ.get("TYPESAFE_BASE_URL", "https://api.vakyn.com").rstrip("/")
        self.key = os.environ.get("TYPESAFE_API_KEY", "")
        self.model, self.max_calls, self.concurrency, self.timeout = model, max_calls, concurrency, timeout
        self.store_path = run_dir / "answers.jsonl"
        self.store, self.lock = {}, threading.Lock()
        if self.store_path.exists():
            for line in self.store_path.open():
                r = json.loads(line)
                self.store[(r["wording"], r["model"], r["case_id"])] = r["answer"]
        self.calls = 0

    def missing(self, q, cases):
        h = wording_hash(q)
        return [c for c in cases if (h, self.model, c["id"]) not in self.store]

    def post(self, body):
        data = json.dumps(body).encode()
        for attempt in range(6):
            req = urllib.request.Request(f"{self.base}/v1/systemone", data=data, headers={
                "content-type": "application/json", "authorization": f"Bearer {self.key}"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    raise Stop("401 from VAKYN: the key in TYPESAFE_API_KEY is missing, wrong or revoked.")
                if e.code == 402:
                    raise Stop("402 from VAKYN: the balance is empty. Add balance in the console, then rerun.")
                if e.code in (429, 503) and attempt < 5:
                    time.sleep(float(e.headers.get("retry-after") or 2 ** attempt))
                    continue
                if e.code == 429:
                    raise Stop("429 from VAKYN after 5 retries: lower --concurrency, then rerun (stored answers are kept).")
                raise Stop(f"HTTP {e.code} from VAKYN: {e.read()[:300]!r}")
            except (urllib.error.URLError, OSError) as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise Stop(f"cannot reach {self.base}: {e}")

    def answers(self, req, name, q, cases):
        """Answers for every case, from the store or from VAKYN. Never asks a stored case again."""
        h = wording_hash(q)
        todo = self.missing(q, cases)
        if todo:
            if not self.key:
                raise Stop(f"{len(todo)} answers are not stored and TYPESAFE_API_KEY is not set: no scores. "
                           "Set the key in the environment and rerun.")
            if self.calls + len(todo) > self.max_calls:
                raise Stop(f"this step needs {len(todo)} calls and {self.calls} are used of --max-calls "
                           f"{self.max_calls}: stopping. Raise the limit only after the person agrees.")

            def one(case):
                body = {"model": self.model, "state": build_state(case), "questions": {name: q}}
                a = self.post(body)["answers"][name]
                with self.lock:
                    self.calls += 1
                    self.store[(h, self.model, case["id"])] = a
                    with self.store_path.open("a") as f:
                        f.write(json.dumps({"wording": h, "model": self.model, "case_id": case["id"], "answer": a}) + "\n")

            with concurrent.futures.ThreadPoolExecutor(self.concurrency) as pool:
                for fut in [pool.submit(one, c) for c in todo]:
                    fut.result()
        return {c["id"]: self.store[(h, self.model, c["id"])] for c in cases}


# ---------- scoring ----------

def average_precision(pairs):
    """pairs: (probability of true, label). Area under the precision-recall curve, step-wise."""
    pairs = sorted(pairs, key=lambda p: -p[0])
    positives = sum(1 for _, y in pairs if y)
    if not positives:
        return float("nan")
    hits, total = 0, 0.0
    for i, (_, y) in enumerate(pairs, 1):
        if y:
            hits += 1
            total += hits / i
    return total / positives


def truth(label):
    """noul labels: true / false, as JSON booleans or strings."""
    return label if isinstance(label, bool) else str(label).strip().lower() in ("true", "yes", "1")


def score(qtype, cases, answers, threshold):
    n = len(cases)
    if qtype == "choice":
        right = sum(answers[c["id"]]["choice"] == c["label"] for c in cases)
        return {"n": n, "right": right, "accuracy": right / n}
    if qtype == "noul":
        right = sum((answers[c["id"]]["noul"] >= threshold) == truth(c["label"]) for c in cases)
        ap = average_precision([(answers[c["id"]]["noul"], truth(c["label"])) for c in cases])
        return {"n": n, "right": right, "accuracy": right / n, "ap": ap}
    diffs = [answers[c["id"]]["score"] - int(c["label"]) for c in cases]
    exact = sum(d == 0 for d in diffs)
    return {"n": n, "right": exact, "exact": exact / n, "within_one": sum(abs(d) <= 1 for d in diffs) / n,
            "mae": sum(abs(d) for d in diffs) / n}


def key_of(qtype, s, metric):
    """Bigger is better."""
    if qtype == "score":
        return (s["exact"], -s["mae"])
    if qtype == "noul" and metric == "ap":
        return (s["ap"], s["accuracy"])
    return (s["accuracy"],) + ((s["ap"],) if qtype == "noul" else ())


def show(qtype, s):
    if qtype == "choice":
        return f"accuracy {s['accuracy']:.3f} ({s['right']} of {s['n']})"
    if qtype == "noul":
        return f"accuracy {s['accuracy']:.3f} ({s['right']} of {s['n']}), average precision {s['ap']:.3f}"
    return (f"exact {s['exact']:.3f} ({s['right']} of {s['n']}), within one level {s['within_one']:.3f}, "
            f"mean absolute error {s['mae']:.2f}")


def miss_groups(qtype, cases, answers, threshold):
    """Misses grouped by kind: choice (right -> picked), noul (false positive / negative), score (high / low)."""
    groups = collections.defaultdict(list)
    for c in cases:
        a = answers[c["id"]]
        if qtype == "choice":
            if a["choice"] != c["label"]:
                groups[f"{c['label']} -> {a['choice']}"].append((c, a.get("confidence")))
        elif qtype == "noul":
            said = a["noul"] >= threshold
            if said != truth(c["label"]):
                groups["false positive (said true, label false)" if said else
                       "false negative (said false, label true)"].append((c, a["noul"]))
        else:
            d = a["score"] - int(c["label"])
            if d:
                groups["too high" if d > 0 else "too low"].append((c, a["score"]))
    return sorted(groups.items(), key=lambda kv: -len(kv[1]))


def print_misses(qtype, cases, answers, threshold, top=5, per_group=3):
    groups = miss_groups(qtype, cases, answers, threshold)
    if not groups:
        print("No misses on dev.")
        return
    print(f"Misses on dev, grouped by kind (write one rule per group, biggest first):")
    for name, items in groups[:top]:
        print(f"  {name}: {len(items)}")
        for c, v in items[:per_group]:
            text = json.dumps(build_state(c), ensure_ascii=False)
            print(f"    {c['id']} ({v}): {text[:140]}")


# ---------- run state ----------

def run_paths(run):
    d = pathlib.Path(run)
    return d, d / "run.json"


def save_run(path, run):
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n")


def load_run(run):
    d, path = run_paths(run)
    if not path.exists():
        raise Stop(f"no run in {d}: run `optimize.py start` first")
    return d, path, json.loads(path.read_text())


def load_cases(path):
    cases = [json.loads(line) for line in open(path) if line.strip()]
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise Stop(f"{path}: case ids must be unique (the split hashes them)")
    return [c for c in cases if c.get("label") is not None]


def check_inputs(qtype, q, cases):
    """Warnings about the labeled cases; printed, never fatal."""
    warnings = []
    if len(cases) < MIN_CASES:
        warnings.append(f"only {len(cases)} labeled cases; label at least {MIN_CASES - len(cases)} more "
                        f"(to {MIN_CASES}). With this few, a gain of one or two cases is noise.")
    counts = collections.Counter(str(truth(c["label"])).lower() if qtype == "noul" else c["label"] for c in cases)
    if qtype == "choice":
        expected = list(q["criteria"])
    elif qtype == "noul":
        expected = ["true", "false"]
    else:
        expected = list(range(len(q["criteria"])))
    for k in expected:
        if counts.get(k, 0) < MIN_PER_CLASS:
            warnings.append(f"{k!r} has {counts.get(k, 0)} labeled cases (fewer than {MIN_PER_CLASS}): the result "
                            f"says little about it; label {MIN_PER_CLASS - counts.get(k, 0)} more if it matters.")
    seen = {str(truth(c["label"])).lower() if qtype == "noul" else str(c["label"]) for c in cases}
    unknown = sorted(seen - {str(k) for k in expected})
    if unknown:
        raise Stop(f"labels that are not options of the question: {unknown}")
    return warnings


# ---------- commands ----------

def cmd_start(a):
    d, path = run_paths(a.run)
    if path.exists() and not a.restart:
        raise Stop(f"{path} exists: continue with `try` / `finish`, or pass --restart to begin again")
    d.mkdir(parents=True, exist_ok=True)
    req, name, q = load_request(a.request)
    model = a.model or req.get("model")
    cases = load_cases(a.cases)
    dev = [c for c in cases if not reserved(c["id"], a.reserved_share)]
    res = [c for c in cases if reserved(c["id"], a.reserved_share)]

    print(f"Question {name!r} ({q['type']}), model {model}, wording {wording_hash(q)}.")
    print(f"{len(cases)} labeled cases: {len(dev)} dev, {len(res)} reserved (split by a hash of the case id).")
    for w in check_inputs(q["type"], q, cases):
        print(f"Warning: {w}")

    estimate = len(dev) * (1 + a.rounds) + len(res) * 2
    print(f"Estimate: up to {estimate} calls to VAKYN ({len(dev)} dev x (1 + {a.rounds} rounds) + "
          f"{len(res)} reserved x 2, at the end). On VAKYN Cloud each call spends balance.")
    if estimate > a.confirm_above and not a.yes:
        print(f"That is more than {a.confirm_above} calls: ask the person, then rerun with --yes.")
        return 3

    client = Client(d, model, a.max_calls, a.concurrency)
    answers = client.answers(req, name, q, dev)
    s = score(q["type"], dev, answers, a.threshold)
    run = {"request": str(a.request), "cases": str(a.cases), "question": name, "type": q["type"], "model": model,
           "threshold": a.threshold, "metric": a.metric, "reserved_share": a.reserved_share, "rounds": a.rounds,
           "max_calls": a.max_calls, "calls": client.calls, "estimate": estimate, "keys": keys_of(q),
           "start": {"file": str(a.request), "wording": wording_hash(q), "dev": s},
           "best": {"file": str(a.request), "wording": wording_hash(q), "dev": s, "rules": []},
           "tried": [], "no_gain": 0, "reserved_done": False}
    save_run(path, run)
    print(f"\nCurrent wording on dev: {show(q['type'], s)}")
    print_misses(q["type"], dev, answers, a.threshold)
    print(f"\nCalls used: {client.calls}. Next: write a candidate as a new file and run `optimize.py try`.")
    return 0


def cmd_try(a):
    d, path, run = load_run(a.run)
    if run["reserved_done"]:
        raise Stop("the reserved set was already scored: this run is closed. Start a new run for new rounds.")
    if pathlib.Path(a.candidate).resolve() in {pathlib.Path(run["start"]["file"]).resolve(),
                                               pathlib.Path(run["best"]["file"]).resolve()}:
        raise Stop("write the candidate as a new versioned file; never overwrite the wording in use")
    _, name, base_q = load_request(run["best"]["file"])
    req, cname, q = load_request(a.candidate)
    if cname != run["question"]:
        raise Stop(f"the candidate renames the question {run['question']!r} to {cname!r}: the code reads that name")
    if q["type"] != run["type"]:
        raise Stop(f"the candidate changes the question type ({run['type']} -> {q['type']})")
    if keys_of(q) != run["keys"]:
        raise Stop(f"the candidate changes the option keys ({run['keys']} -> {keys_of(q)}): the code reads them. "
                   "Only instructions and descriptions may change; ask the person before any key change.")
    tried = len(run["tried"]) + 1
    if tried > run["rounds"]:
        raise Stop(f"round limit reached ({run['rounds']}): run `optimize.py finish`")

    cases = load_cases(run["cases"])
    dev = [c for c in cases if not reserved(c["id"], run["reserved_share"])]
    client = Client(d, run["model"], run["max_calls"] - run["calls"], a.concurrency)
    answers = client.answers(req, name, q, dev)
    run["calls"] += client.calls
    s = score(q["type"], dev, answers, run["threshold"])
    best = run["best"]
    cand_key, best_key = key_of(q["type"], s, run["metric"]), key_of(q["type"], best["dev"], run["metric"])
    shorter = wording_size(q) < wording_size(base_q)
    keep = cand_key > best_key or (cand_key == best_key and shorter)

    print(f"Round {tried}: {a.candidate} ({wording_hash(q)})")
    print(f"  best so far  {show(q['type'], best['dev'])}   [{best['file']}]")
    print(f"  candidate    {show(q['type'], s)}")
    if keep:
        why = "better on dev" if cand_key > best_key else "same score on dev, shorter wording"
        print(f"Keep the candidate: {why}.")
        run["best"] = {"file": str(a.candidate), "wording": wording_hash(q), "dev": s,
                       "rules": best["rules"] + list(a.rule or [])}
        run["no_gain"] = 0 if cand_key > best_key else run["no_gain"] + 1
    else:
        print(f"Discard the candidate: not better on dev. Keep {best['file']}.")
        run["no_gain"] += 1
    run["tried"].append({"file": str(a.candidate), "wording": wording_hash(q), "dev": s, "kept": keep,
                         "rules": list(a.rule or [])})
    save_run(path, run)

    _, _, best_q = load_request(run["best"]["file"])
    best_answers = client.answers(req, name, best_q, dev)
    print()
    print_misses(q["type"], dev, best_answers, run["threshold"])
    print(f"\nCalls used: {run['calls']} of {run['max_calls']}.")
    if run["no_gain"] >= 2:
        print("Two rounds with no gain: stop here and run `optimize.py finish`.")
    elif tried >= run["rounds"]:
        print("Round limit reached: run `optimize.py finish`.")
    return 0


def cmd_finish(a):
    d, path, run = load_run(a.run)
    if run["reserved_done"]:
        raise Stop("the reserved set was already scored for this run; looking again turns it into a second dev set")
    cases = load_cases(run["cases"])
    res = [c for c in cases if reserved(c["id"], run["reserved_share"])]
    req, name, q0 = load_request(run["start"]["file"])
    _, _, q1 = load_request(run["best"]["file"])
    client = Client(d, run["model"], run["max_calls"] - run["calls"], a.concurrency)
    s0 = score(run["type"], res, client.answers(req, name, q0, res), run["threshold"])
    s1 = score(run["type"], res, client.answers(req, name, q1, res), run["threshold"])
    run["calls"] += client.calls
    run["reserved_done"] = True
    t, m = run["type"], run["metric"]
    d0, d1 = run["start"]["dev"], run["best"]["dev"]

    same = run["best"]["wording"] == run["start"]["wording"]
    dev_ok = not same and key_of(t, d1, m) > key_of(t, d0, m)
    res_ok = key_of(t, s1, m) >= key_of(t, s0, m)
    promote = dev_ok and res_ok
    print(f"Reserved set ({len(res)} cases; counts only)")
    print(f"  start  {show(t, s0)}   [{run['start']['file']}]")
    print(f"  best   {show(t, s1)}   [{run['best']['file']}]")
    print(f"\nBetter on dev: {'yes' if dev_ok else 'no'}. Not worse on reserved: {'yes' if res_ok else 'no'}.")
    print(f"Verdict: {'PROMOTE ' + run['best']['file'] if promote else 'KEEP ' + run['start']['file']}")
    if dev_ok and not res_ok:
        print("Better on dev but worse on reserved: the new wording fits the dev cases, not the flow. Do not promote.")
    main_metric = "exact" if t == "score" else ("ap" if m == "ap" else "accuracy")
    gap = (d1[main_metric] - d0[main_metric]) - (s1[main_metric] - s0[main_metric])
    if promote and gap > OVERFIT_GAP:
        print(f"Dev gained {gap:.2f} more than reserved ({len(res)} reserved cases: one case is {1 / len(res):.2f}). "
              "Check that every rule is general, not about single dev cases; if not, try fewer, more general rules. "
              "More reserved cases will tell.")
    run.update({"reserved": {"start": s0, "best": s1}, "verdict": "promote" if promote else "keep"})
    save_run(path, run)

    report = d / "report.md"
    report.write_text(render_report(run))
    print(f"\nReport: {report}. Calls used in this run: {run['calls']}.")
    if a.log:
        with open(a.log, "a") as f:
            f.write(json.dumps({
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "current": f"{run['start']['file']} ({run['start']['wording']})",
                "candidate": f"{run['best']['file']} ({run['best']['wording']})",
                "dev": {"current": d0, "candidate": d1}, "reserved": {"current": s0, "candidate": s1},
                "verdict": run["verdict"], "live": run["best"]["file"] if promote else run["start"]["file"],
                "model": run["model"], "calls": run["calls"]}) + "\n")
        print(f"Promotion log: one line appended to {a.log}.")
    return 0 if promote else 1


def render_report(run):
    t = run["type"]
    rows = {"choice": [("accuracy", "{:.3f}")], "noul": [("accuracy", "{:.3f}"), ("ap", "{:.3f}")],
            "score": [("exact", "{:.3f}"), ("within_one", "{:.3f}"), ("mae", "{:.2f}")]}[t]
    out = [f"# Wording tuned: {run['question']} ({t}) on {run['model']}", "",
           f"Start: `{run['start']['file']}` ({run['start']['wording']}). "
           f"Best: `{run['best']['file']}` ({run['best']['wording']}). Verdict: **{run['verdict']}**.", "",
           "| Metric | Dev, start | Dev, best | Reserved, start | Reserved, best |", "|---|---|---|---|---|"]
    d0, d1, r0, r1 = run["start"]["dev"], run["best"]["dev"], run["reserved"]["start"], run["reserved"]["best"]
    for k, f in rows:
        out.append(f"| {k} | {f.format(d0[k])} | {f.format(d1[k])} | {f.format(r0[k])} | {f.format(r1[k])} |")
    out.append(f"| right / cases | {d0['right']} / {d0['n']} | {d1['right']} / {d1['n']} | "
               f"{r0['right']} / {r0['n']} | {r1['right']} / {r1['n']} |")
    out += ["", "## Rules added (each with the misses it was written for)", ""]
    out += [f"- {r}" for r in run["best"]["rules"]] or ["- none kept"]
    out += ["", "## Rounds", ""]
    for i, tr in enumerate(run["tried"], 1):
        main = tr["dev"].get("accuracy", tr["dev"].get("exact"))
        out.append(f"{i}. `{tr['file']}`: dev {main:.3f}, {'kept' if tr['kept'] else 'discarded'}")
    out += ["", f"Model calls used: {run['calls']} (estimate was {run['estimate']}).", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--request", required=True)
    s.add_argument("--cases", required=True)
    s.add_argument("--model", help="tune for this model (wording is tuned per model); default: the request's")
    s.add_argument("--rounds", type=int, default=5)
    s.add_argument("--max-calls", type=int, default=2000, help="hard stop on calls for the whole run")
    s.add_argument("--confirm-above", type=int, default=300, help="above this estimate, stop until --yes")
    s.add_argument("--yes", action="store_true", help="the person agreed to the estimate")
    s.add_argument("--threshold", type=float, default=0.5, help="noul: the threshold the app uses")
    s.add_argument("--metric", choices=["accuracy", "ap"], default="accuracy",
                   help="noul: ap (average precision) when ranking or filtering matters")
    s.add_argument("--reserved-share", type=float, default=0.3)
    s.add_argument("--restart", action="store_true")
    t = sub.add_parser("try")
    t.add_argument("--candidate", required=True)
    t.add_argument("--rule", action="append", help="'<group of misses>: <rule>'; repeat once per rule added")
    f = sub.add_parser("finish")
    f.add_argument("--log", help="promotion log (JSON lines), as check's promote.py writes it")
    for p in (s, t, f):
        p.add_argument("--run", default="optimize-run", help="folder for run.json, answers.jsonl and report.md")
        p.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args(argv)
    try:
        return {"start": cmd_start, "try": cmd_try, "finish": cmd_finish}[a.cmd](a)
    except Stop as e:
        print(f"Stopped: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
