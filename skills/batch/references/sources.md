# Sources: files, tables and logs

Whatever the source, the script does the same things: read only the columns it sends, one row
per request, save each answer with the row id, skip rows already answered. Only reading and
writing change.

| Source | Read with | Answers go to | Template |
|---|---|---|---|
| CSV, JSONL | `csv` / `json` (standard library) | new file next to the input, plus a checkpoint | [batch_csv.py](../examples/batch_csv.py) |
| Parquet, or CSV too big for memory | DuckDB or `pyarrow` | new Parquet or CSV file | [below](#parquet-and-large-files-duckdb) |
| SQLite | `sqlite3` (standard library) | a new table | [batch_sql.py](../examples/batch_sql.py) |
| Postgres | `psycopg` | a new table (its own schema is best) | [below](#postgres-psycopg) |
| Log dump | parse to JSONL first | as CSV/JSONL | [below](#log-dumps) |

## Tables: never change the source rows

- Answers go to a **new table** keyed by the row id (`ticket_answers`), joined to the source when
  read. The source table is only read; the script's database role needs no write rights on it.
- Adding answer columns to the source table, or updating its rows, is a change to the person's
  data and schema: **ask first**, and even then write to the new table and copy over in one
  reviewed `UPDATE` at the end.
- Read in batches with keyset paging (`WHERE id > last_id ORDER BY id LIMIT 200`), not `OFFSET`,
  and select only the columns that are sent.
- Write with an upsert on the id (`ON CONFLICT (id) DO UPDATE`), committed per batch: the commit is
  the checkpoint, and a rerun never duplicates.
- "Still to do" is a join: source rows with no answer row, or with an answer row that has an error.

## SQLite

Run [batch_sql.py](../examples/batch_sql.py): `python3 batch_sql.py tickets.db` (pilot), then
`--full`. Tested on the sample: 120 rows, pilot then `--limit 50` then the rest, 120 answer rows,
no duplicates, source unchanged.

## Postgres (psycopg)

Same script, with these pieces swapped in (`pip install "psycopg[binary]"`, connection string in
`DATABASE_URL`, never in code). Placeholders are `%s`; the pilot spreads over the table by a hash
of the id.

```python
import os
import psycopg
from psycopg.rows import dict_row

db = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
db.execute("CREATE SCHEMA IF NOT EXISTS vakyn")
db.execute("""
CREATE TABLE IF NOT EXISTS vakyn.ticket_answers (
    ticket_id text PRIMARY KEY,
    team text, team_confidence real, refund text, refund_p real,
    urgency text, urgency_score real, urgency_confidence real,
    unsure boolean, unsure_why text, request_id text,
    error text NOT NULL DEFAULT '', answered_at timestamptz NOT NULL DEFAULT now()
)""")
db.commit()

TODO = """SELECT t.ticket_id, t.subject, t.body, t.plan FROM support.tickets t
          LEFT JOIN vakyn.ticket_answers a ON a.ticket_id = t.ticket_id AND a.error = ''
          WHERE a.ticket_id IS NULL AND t.ticket_id > %s ORDER BY t.ticket_id LIMIT %s"""
PILOT = """SELECT ticket_id, subject, body, plan FROM support.tickets
           ORDER BY md5(ticket_id::text) LIMIT %s"""
COLUMNS = ["team", "team_confidence", "refund", "refund_p", "urgency", "urgency_score",
           "urgency_confidence", "unsure", "unsure_why", "request_id", "error"]
UPSERT = (f"INSERT INTO vakyn.ticket_answers (ticket_id, {', '.join(COLUMNS)}) "
          f"VALUES ({', '.join(['%s'] * (len(COLUMNS) + 1))}) ON CONFLICT (ticket_id) DO UPDATE SET "
          + ", ".join(f"{c} = excluded.{c}" for c in COLUMNS) + ", answered_at = now()")


def fetch_todo(last_id, size):
    return db.execute(TODO, (last_id, size)).fetchall()


def save(results):  # [(ticket_id, answer_columns), ...] for one batch
    with db.cursor() as cur:
        cur.executemany(UPSERT, [(rid, *(r.get(c) for c in COLUMNS[:-1]), r.get("error", ""))
                                 for rid, r in results])
    db.commit()
```

Review rows: `SELECT t.*, a.* FROM vakyn.ticket_answers a JOIN support.tickets t USING (ticket_id)
WHERE a.unsure AND a.error = ''`, exported with `\copy (...) TO 'review.csv' CSV HEADER`.
Tested against Postgres 16 with the sample: pilot, `--limit`, resume, rerun with no duplicates.

## Parquet and large files (DuckDB)

DuckDB reads Parquet and CSV without loading the file into Python first (`pip install duckdb`).
Read only the sent columns, keep [batch_csv.py](../examples/batch_csv.py)'s checkpoint, and join
the answers back at the end:

```python
import duckdb

def read_rows(path):  # replaces read_rows in batch_csv.py
    rel = duckdb.sql(f"SELECT ticket_id, subject, body, plan FROM '{path}' ORDER BY ticket_id")
    return [dict(zip(rel.columns, row)) for row in rel.fetchall()]

# After the run: every source column plus the answers, as Parquet. Unanswered rows keep empty answers.
duckdb.sql("""
COPY (
    SELECT t.*, a.* EXCLUDE (id)
    FROM 'tickets.parquet' t
    LEFT JOIN read_json_auto('tickets.vakyn.csv.progress.jsonl') a ON a.id = t.ticket_id
    QUALIFY row_number() OVER (PARTITION BY t.ticket_id ORDER BY a.error = '' DESC) = 1
) TO 'tickets.vakyn.parquet' (FORMAT parquet)
""")
```

The `QUALIFY` keeps one answer per row when the checkpoint holds an error line and a later
success for the same id. For files with tens of millions of rows, read in id ranges
(`WHERE ticket_id > ? ORDER BY ticket_id LIMIT 10000`) instead of all at once.
Tested with DuckDB on the sample saved as Parquet.

## Log dumps

- Turn the dump into one record per line first (JSONL): one log event per record, with
  multi-line entries (stack traces) joined to their first line. Keep the raw line in a column.
- Id: the event's own id when there is one; otherwise a hash of the raw text plus its timestamp,
  so a rerun on the same dump finds the same ids.
- Send the message and the fields the question needs (service, level); leave out hosts, IPs, user
  ids and tokens. Logs often hold secrets: replace anything that looks like a key or a password
  in code before sending, and say so in the plan.
- Then run it like a JSONL file with [batch_csv.py](../examples/batch_csv.py).
