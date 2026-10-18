"""Run a CSV or JSONL file through VAKYN: pilot first, then the full run, with resume.

Usage:
    python3 batch_csv.py tickets.csv                 # pilot: 30 rows spread over the file
    python3 batch_csv.py tickets.csv --full          # every row not done yet
    python3 batch_csv.py tickets.csv --full --limit 50   # stop after 50 new rows (resume later)

Needs: pip install typesafe-sdk; TYPESAFE_BASE_URL (https://api.vakyn.com, or your own server) and
TYPESAFE_API_KEY in the environment. On VAKYN Cloud every answered row spends balance: the pilot
prints the input tokens, so the full run's cost can be estimated before --full.

Writes, next to --out (default <input>.vakyn.csv):
    <out>.progress.jsonl   checkpoint: one line per finished row; a rerun skips rows done here
    <out>                  every input column plus the answer columns, in input order
    <out-stem>.review.csv  the unsure rows, with the columns that were sent, for a person to check
Rerunning never sends a done row again, and rebuilds the same output files.
"""

import argparse
import asyncio
import collections
import csv
import json
import os
import pathlib
import re
import statistics
import sys
import time

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, RetryPolicy, Score, TypeSafeError

# ---- What is sent. Only these columns go into the state; every other column stays here. ----
ID_COLUMN = "ticket_id"
SEND_COLUMNS = {"subject": "subject", "body": "message", "plan": "plan"}  # file column -> state key
REDACT = True  # replace emails and phone numbers in the sent text with [email] / [phone]

# ---- The questions. Independent, so they share ONE request per row. ----
TEAMS = {
    "billing": "Charges, invoices, refunds, plan prices, payment methods",
    "access": "Signing in, passwords, two-factor, invitations, user roles and owners",
    "bug": "Something in the product is broken, wrong or slow",
    "how_to": "How to use or set up a feature that works as intended",
    "other": "None of these: sales, partnerships, feedback, job applications, spam, too vague to tell",
}
URGENCY = {  # name -> level description, lowest first
    "low": "Low: a question, feedback or a small problem with an easy workaround",
    "medium": "Medium: something is broken or wrong, but the customer can still work",
    "high": "High: the customer cannot work, has lost data or money, or threatens legal action",
}
QUESTIONS = {
    "team": Choice(instructions="Which team should handle the support ticket in state.message?", criteria=TEAMS),
    "refund": Noul(instructions="Does the customer in state.message ask for money back?"),
    "urgency": Score(instructions="How urgent is the support ticket in state.message?",
                     criteria=list(URGENCY.values())),
}

# ---- Unsure rules: starting values from check's thresholds page; tune on labeled rows. ----
MIN_CONFIDENCE = {"team": 0.6, "urgency": 0.6}  # choice/score that only routes work
NOUL_YES, NOUL_NO = 0.8, 0.2                   # noul: act on yes at >= 0.8, on no at <= 0.2
ESCAPE = {"team": "other"}                     # an escape pick is unsure too

# ---- Load. ----
# VAKYN Cloud takes 60 requests per second per key; open-server queues --max-queue (default 32).
CONCURRENCY = 8      # requests in flight
MAX_CONCURRENCY = 32
TIMEOUT_S = 60.0     # per attempt; the SDK default is 10 s
# Retries 408, 429 and 5xx, waiting the retry-after the server sends; gives up after 6 tries or 10 min.
RETRY = RetryPolicy(max_retries=6, backoff_max=30.0, timeout=600.0, respect_retry_after=True)
PILOT_ROWS = 30

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
ANSWER_COLUMNS = ["team", "team_confidence", "refund", "refund_p", "urgency", "urgency_score",
                  "urgency_confidence", "unsure", "unsure_why", "request_id", "input_tokens", "error"]


def read_rows(path):
    if path.suffix == ".jsonl":
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_state(row):
    state = {}
    for column, key in SEND_COLUMNS.items():
        value = (row.get(column) or "").strip()
        if REDACT:
            value = PHONE.sub("[phone]", EMAIL.sub("[email]", value))
        state[key] = value
    return state


def to_columns(res):
    team, refund, urgency = res.choices["team"], res.nouls["refund"].noul, res.scores["urgency"]
    if team.choice not in TEAMS:
        raise ValueError(f"team pick {team.choice!r} is not an offered option")
    top_level = max(urgency.probabilities, key=urgency.probabilities.get)
    why = []
    if team.confidence < MIN_CONFIDENCE["team"] or team.choice == ESCAPE["team"]:
        why.append("team")
    if NOUL_NO < refund < NOUL_YES:
        why.append("refund")
    if urgency.confidence < MIN_CONFIDENCE["urgency"]:
        why.append("urgency")
    return {
        "team": team.choice, "team_confidence": team.confidence,
        "refund": "yes" if refund >= NOUL_YES else "no" if refund <= NOUL_NO else "unsure", "refund_p": refund,
        "urgency": list(URGENCY)[int(top_level)], "urgency_score": urgency.score,
        "urgency_confidence": urgency.confidence,
        "unsure": bool(why), "unsure_why": " ".join(why), "request_id": res.request_id,
        "input_tokens": res.usage.input_tokens, "error": "",
    }


class Progress:
    """done/total, %, rows/s, ETA, errors. The rate skips the first wave of requests (warm-up)
    and uses the last 30 s, so it shows the steady state."""

    def __init__(self, total, already, warmup):
        self.total, self.done, self.errors = total, already, 0
        self.warmup, self.seen = warmup, 0
        self.stamps = collections.deque()
        self.last_print = 0.0

    def tick(self, ok):
        now = time.monotonic()
        self.done += 1
        self.seen += 1
        self.errors += not ok
        if self.seen > self.warmup:
            self.stamps.append(now)
        while self.stamps and now - self.stamps[0] > 30:
            self.stamps.popleft()
        if now - self.last_print >= 2 or self.done == self.total:
            self.last_print = now
            print(self.line(), flush=True)

    def rate(self):
        if len(self.stamps) < 2:
            return None
        return (len(self.stamps) - 1) / max(self.stamps[-1] - self.stamps[0], 1e-6)

    def line(self):
        r = self.rate()
        left = self.total - self.done
        rate = f"{r:.1f} rows/s" if r else "warming up"
        eta = f"ETA {left / r / 60:.1f} min" if r else "ETA after warm-up"
        return f"{self.done}/{self.total} ({self.done / self.total:.0%})  {rate}  {eta}  errors {self.errors}"


async def run(rows, todo, progress_path, concurrency, progress=None, times=None):
    queue = asyncio.Queue()
    for row in todo:
        queue.put_nowait(row)
    write_lock = asyncio.Lock()

    async def worker(client, out):
        while True:
            try:
                row = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            t0 = time.perf_counter()
            try:
                res = await client.system_one(state=build_state(row), questions=QUESTIONS)
                result = to_columns(res)
            except (TypeSafeError, ValueError) as e:  # 400 too big, 401, 429/5xx after every retry, timeout
                result = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            if times is not None:
                times.append(time.perf_counter() - t0)
            async with write_lock:  # one line per finished row, flushed: the checkpoint
                out.write(json.dumps({"id": row[ID_COLUMN], **result}) + "\n")
                out.flush()
            if progress:
                progress.tick(not result["error"])

    async with AsyncTypeSafeClient(timeout=TIMEOUT_S, retry=RETRY) as client:
        with open(progress_path, "a") as out:
            await asyncio.gather(*(worker(client, out) for _ in range(concurrency)))


def load_done(progress_path):
    """Last result per id. Rows that ended in an error are not done: a rerun tries them again."""
    results = {}
    if progress_path.exists():
        with open(progress_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:  # a line cut off by a hard stop: that row runs again
                    continue
                results[r["id"]] = r
    return results


def write_outputs(rows, results, out_path, review_path):
    fields = list(rows[0]) + [c for c in ANSWER_COLUMNS if c not in rows[0]]
    review_fields = [ID_COLUMN, *SEND_COLUMNS] + ANSWER_COLUMNS
    with open(out_path, "w", newline="") as f, open(review_path, "w", newline="") as rf:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        rw = csv.DictWriter(rf, fieldnames=review_fields, extrasaction="ignore")
        w.writeheader()
        rw.writeheader()
        for row in rows:  # input order, so the same results always give the same files
            r = results.get(row[ID_COLUMN])
            if r is None:
                continue
            merged = {**row, **{c: r.get(c, "") for c in ANSWER_COLUMNS}}
            w.writerow(merged)
            if r.get("unsure"):
                rw.writerow(merged)


def summary(rows, results, seconds, sent):
    ok = [r for r in results.values() if not r.get("error")]
    errors = [r for r in results.values() if r.get("error")]
    print(f"\nRows: {len(rows)}  answered: {len(ok)}  errors: {len(errors)}  "
          f"not done: {len(rows) - len(results)}")
    for col in ("team", "refund", "urgency"):
        counts = collections.Counter(r[col] for r in ok)
        print(f"  {col}: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
    unsure = sum(bool(r["unsure"]) for r in ok)
    if ok:
        print(f"  unsure: {unsure}/{len(ok)} ({unsure / len(ok):.0%})")
    for r in errors[:5]:
        print(f"  error {r['id']}: {r['error']}")
    if sent:
        print(f"This run: {sent} rows sent in {seconds:.1f} s ({sent / seconds:.1f} rows/s, whole run)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--full", action="store_true", help="run every row (after the pilot was reviewed)")
    ap.add_argument("--limit", type=int, help="stop after this many new rows")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    a = ap.parse_args()
    if a.concurrency > MAX_CONCURRENCY:
        sys.exit(f"--concurrency {a.concurrency} is above {MAX_CONCURRENCY} (open-server's default --max-queue); "
                 "lower it, or raise --max-queue on your own server first")

    rows = read_rows(a.input)
    ids = [r[ID_COLUMN] for r in rows]
    if len(set(ids)) != len(ids):
        sys.exit(f"{ID_COLUMN} is not unique; resume needs one stable id per row")
    out_path = a.out or a.input.with_suffix(".vakyn.csv")
    progress_path = out_path.with_name(out_path.name + ".progress.jsonl")
    review_path = out_path.with_name(out_path.stem + ".review.csv")
    print(f"Server: {os.environ.get('TYPESAFE_BASE_URL', '(SDK default)')}")
    print(f"Sent per row: {', '.join(SEND_COLUMNS)}" + (" (emails and phone numbers replaced)" if REDACT else ""))
    print(f"Not sent: {', '.join(c for c in rows[0] if c not in SEND_COLUMNS)}")

    results = load_done(progress_path)
    done = {i for i, r in results.items() if not r.get("error")}
    if a.full:
        todo = [r for r in rows if r[ID_COLUMN] not in done]
    else:  # pilot: rows spread over the whole file, not only the first ones
        step = max(len(rows) // PILOT_ROWS, 1)
        todo = [r for r in rows[::step][:PILOT_ROWS] if r[ID_COLUMN] not in done]
    if a.limit is not None:
        todo = todo[:a.limit]
    print(f"{'Full run' if a.full else 'Pilot'}: {len(todo)} rows to send, {len(done)} already done "
          f"(checkpoint {progress_path.name}), {a.concurrency} at a time")

    times, t0 = [], time.monotonic()
    progress = Progress(len(done) + len(todo), len(done), warmup=a.concurrency) if a.full else None
    try:
        asyncio.run(run(rows, todo, progress_path, a.concurrency, progress, times))
    except KeyboardInterrupt:
        print("\nStopped. Finished rows are saved; rerun the same command to resume.")
    seconds = time.monotonic() - t0
    results = load_done(progress_path)
    write_outputs(rows, results, out_path, review_path)

    if not a.full:
        step = max(len(rows) // PILOT_ROWS, 1)
        print(f"\n{'id':<7}{'team':<9}{'conf':>5}  {'refund_p':>8}  {'urgency':<8}{'conf':>5}  unsure  subject")
        for row in rows[::step][:PILOT_ROWS]:
            r = results.get(row[ID_COLUMN], {})
            if r.get("error") or not r:
                print(f"{row[ID_COLUMN]:<7}ERROR {r.get('error', 'not run')}")
                continue
            print(f"{row[ID_COLUMN]:<7}{r['team']:<9}{r['team_confidence']:>5.2f}  {r['refund_p']:>8.2f}  "
                  f"{r['urgency']:<8}{r['urgency_confidence']:>5.2f}  {r['unsure_why'] or '-':<7} {row['subject'][:40]}")
        if times:
            rate = len(times) / seconds
            print(f"\nTime per row: median {statistics.median(times) * 1000:.0f} ms, "
                  f"max {max(times) * 1000:.0f} ms, at {a.concurrency} in flight; {rate:.1f} rows/s "
                  f"(includes warm-up). Full file at this rate: about {len(rows) / rate / 60:.1f} min.")
        tokens = [r["input_tokens"] for r in results.values() if r.get("input_tokens")]
        if tokens:
            per_row = statistics.mean(tokens)
            print(f"Input tokens per row: mean {per_row:.0f}; whole file about {per_row * len(rows):,.0f}. "
                  "On VAKYN Cloud, multiply by the price per billion input tokens from GET /v1/models.")
        print("Review the pilot rows above. Then run again with --full.")
    summary(rows, results, seconds, len(times))
    print(f"Output: {out_path}  Review file: {review_path}")


if __name__ == "__main__":
    main()
