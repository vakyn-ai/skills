"""Run a SQLite table through VAKYN. Answers go to a NEW table; the source table is only read.

Usage:
    python3 batch_sql.py tickets.db --create-from tickets.sample.csv   # demo: load the sample once
    python3 batch_sql.py tickets.db                  # pilot: 30 rows spread over the table
    python3 batch_sql.py tickets.db --full           # every row without an answer yet
    python3 batch_sql.py tickets.db --full --limit 50

Needs: pip install typesafe-sdk; TYPESAFE_BASE_URL and TYPESAFE_API_KEY in the environment.
The questions, state builder and unsure rules are imported from batch_csv.py (keep them in one
module so the file run and the table run ask the same thing).

Resume: a row is done when ticket_answers has a row for its id with an empty error. Answers are
upserted by id, so a rerun never duplicates and never touches the source table.
Postgres and DuckDB versions of the SQL: see the skill's references/sources.md.
"""

import argparse
import asyncio
import csv
import sqlite3
import sys
import time

from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError

from batch_csv import (CONCURRENCY, MAX_CONCURRENCY, PILOT_ROWS, RETRY, TIMEOUT_S, QUESTIONS, Progress,
                       build_state, to_columns)

SOURCE, ID = "tickets", "ticket_id"
RESULTS = "ticket_answers"
READ_BATCH = 200  # rows read from the table at a time; memory stays flat on any table size

CREATE_RESULTS = f"""
CREATE TABLE IF NOT EXISTS {RESULTS} (
    {ID} TEXT PRIMARY KEY,
    team TEXT, team_confidence REAL,
    refund TEXT, refund_p REAL,
    urgency TEXT, urgency_score REAL, urgency_confidence REAL,
    unsure INTEGER, unsure_why TEXT,
    request_id TEXT, error TEXT NOT NULL DEFAULT '',
    answered_at TEXT NOT NULL DEFAULT (datetime('now'))
)"""
COLUMNS = ["team", "team_confidence", "refund", "refund_p", "urgency", "urgency_score",
           "urgency_confidence", "unsure", "unsure_why", "request_id", "error"]
UPSERT = (f"INSERT INTO {RESULTS} ({ID}, {', '.join(COLUMNS)}) VALUES ({', '.join('?' * (len(COLUMNS) + 1))}) "
          f"ON CONFLICT({ID}) DO UPDATE SET " + ", ".join(f"{c} = excluded.{c}" for c in COLUMNS)
          + ", answered_at = datetime('now')")
# Rows still to do, in id order, read with keyset paging (id > last seen) instead of OFFSET.
TODO = (f"SELECT t.* FROM {SOURCE} t LEFT JOIN {RESULTS} a ON a.{ID} = t.{ID} AND a.error = '' "
        f"WHERE a.{ID} IS NULL AND t.{ID} > ? ORDER BY t.{ID} LIMIT ?")
# Pilot: every k-th row, so the sample covers the whole table, not only the oldest rows.
PILOT = (f"SELECT * FROM (SELECT t.*, ROW_NUMBER() OVER (ORDER BY t.{ID}) AS rn FROM {SOURCE} t) "
         f"WHERE (rn - 1) % ? = 0 ORDER BY {ID} LIMIT ?")


async def answer(client, gate, row):
    async with gate:
        try:
            res = await client.system_one(state=build_state(row), questions=QUESTIONS)
            return row[ID], to_columns(res)
        except (TypeSafeError, ValueError) as e:  # kept with its error; a rerun tries it again
            return row[ID], {"error": f"{type(e).__name__}: {str(e)[:200]}"}


def save(db, results):
    db.executemany(UPSERT, [(rid, *(r.get(c) for c in COLUMNS[:-1]), r.get("error", ""))
                            for rid, r in results])
    db.commit()  # one commit per batch: the checkpoint


async def run(db, args, total, done):
    gate = asyncio.Semaphore(args.concurrency)
    progress = Progress(total, done, warmup=args.concurrency) if args.full else None
    sent, last_id = 0, ""
    async with AsyncTypeSafeClient(timeout=TIMEOUT_S, retry=RETRY) as client:
        while True:
            if args.full:
                size = READ_BATCH if args.limit is None else min(READ_BATCH, args.limit - sent)
                rows = db.execute(TODO, (last_id, size)).fetchall() if size > 0 else []
            else:
                step = max(total // PILOT_ROWS, 1)
                rows = [] if sent else db.execute(PILOT, (step, PILOT_ROWS)).fetchall()
            if not rows:
                return sent
            last_id = rows[-1][ID]
            results = []
            for coro in asyncio.as_completed([answer(client, gate, dict(r)) for r in rows]):
                rid, r = await coro
                results.append((rid, r))
                if progress:
                    progress.tick(not r.get("error"))
            save(db, results)
            sent += len(rows)


def report(db, out_review):
    print(f"\nRows in {SOURCE}: {db.execute(f'SELECT count(*) FROM {SOURCE}').fetchone()[0]}")
    ok, err = db.execute(f"SELECT sum(error = ''), sum(error != '') FROM {RESULTS}").fetchone()
    print(f"Answered: {ok or 0}  errors: {err or 0}")
    for col in ("team", "refund", "urgency"):
        counts = db.execute(f"SELECT {col}, count(*) FROM {RESULTS} WHERE error = '' GROUP BY 1 ORDER BY 2 DESC")
        print(f"  {col}: " + ", ".join(f"{k} {n}" for k, n in counts))
    unsure = db.execute(f"SELECT sum(unsure) FROM {RESULTS} WHERE error = ''").fetchone()[0] or 0
    if ok:
        print(f"  unsure: {unsure}/{ok} ({unsure / ok:.0%})")
    cur = db.execute(f"SELECT t.{ID}, t.subject, t.body, a.team, a.team_confidence, a.refund_p, a.urgency, "
                     f"a.urgency_confidence, a.unsure_why FROM {RESULTS} a JOIN {SOURCE} t USING ({ID}) "
                     f"WHERE a.unsure = 1 AND a.error = '' ORDER BY t.{ID}")
    with open(out_review, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur)
    print(f"Answers: table {RESULTS}. Review file: {out_review}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--create-from", help="demo only: load this CSV into the source table first")
    args = ap.parse_args()
    if args.concurrency > MAX_CONCURRENCY:
        sys.exit("concurrency above the server's default queue (32); lower it or raise --max-queue")

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    if args.create_from:
        with open(args.create_from, newline="") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0])
        db.execute(f"CREATE TABLE IF NOT EXISTS {SOURCE} ({', '.join(c + ' TEXT' for c in cols)}, "
                   f"PRIMARY KEY ({ID}))")
        db.executemany(f"INSERT OR IGNORE INTO {SOURCE} VALUES ({', '.join('?' * len(cols))})",
                       [tuple(r[c] for c in cols) for r in rows])
        db.commit()
    db.execute(CREATE_RESULTS)
    total = db.execute(f"SELECT count(*) FROM {SOURCE}").fetchone()[0]
    done = db.execute(f"SELECT count(*) FROM {RESULTS} WHERE error = ''").fetchone()[0]
    print(f"{'Full run' if args.full else 'Pilot'} over {SOURCE} ({total} rows, {done} done). "
          f"Answers go to {RESULTS}; {SOURCE} is only read.")

    t0 = time.monotonic()
    try:
        sent = asyncio.run(run(db, args, total, done))
    except KeyboardInterrupt:
        sent = None
        print("\nStopped. Batches already saved stay saved; rerun the same command to resume.")
    seconds = time.monotonic() - t0
    if sent:
        print(f"This run: {sent} rows in {seconds:.1f} s ({sent / seconds:.1f} rows/s, whole run)")
    if not args.full:
        print("Pilot done. Check the answers (SELECT * FROM ticket_answers), then rerun with --full.")
    report(db, f"{RESULTS}.review.csv")


if __name__ == "__main__":
    main()
