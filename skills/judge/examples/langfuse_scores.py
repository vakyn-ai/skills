"""Grade every recent support-bot trace in Langfuse with VAKYN and write the grades back as scores.

    pip install typesafe-sdk langfuse
    python3 langfuse_scores.py --hours 1 [--name support-reply] [--dry-run]

Run it on a schedule (every hour, say) over every trace in the window, not a sample. Each trace gets
one score per criterion (NUMERIC, 0 to 1) and one overall verdict (CATEGORICAL: pass, fail, review).
Score ids are derived from the trace id, so a rerun updates the same scores instead of adding new ones.
Needs TYPESAFE_BASE_URL, TYPESAFE_API_KEY, and LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST.
"""

import argparse
import asyncio
import datetime as dt

from typesafe_sdk import AsyncTypeSafeClient

from judge import grade


def to_item(trace):
    """Adapt to how your app logs a trace: here input is {"message": ...} and output is the reply text."""
    message = trace.input.get("message") if isinstance(trace.input, dict) else trace.input
    reply = trace.output if isinstance(trace.output, str) else (trace.output or {}).get("reply")
    if not message or not reply:
        return None
    return {"id": trace.id, "input": message, "output": reply}


def fetch_traces(langfuse, since, name, page_size=100):
    page = 1
    while True:
        batch = langfuse.api.trace.list(from_timestamp=since, name=name, limit=page_size, page=page)
        yield from batch.data
        if len(batch.data) < page_size:
            return
        page += 1


def write_scores(langfuse, g):
    for criterion, res in g["criteria"].items():
        langfuse.create_score(
            trace_id=g["id"], score_id=f"{g['id']}-vakyn-{criterion}", name=f"vakyn.{criterion}",
            value=res["value"], data_type="NUMERIC", comment=f"{res['verdict']} (VAKYN {g['request_id']})")
    langfuse.create_score(
        trace_id=g["id"], score_id=f"{g['id']}-vakyn-verdict", name="vakyn.verdict", value=g["verdict"],
        data_type="CATEGORICAL", comment=f"weighted {g['weighted']}; failed {g['failed']}; unsure {g['unsure']}")


async def grade_items(items, concurrency):
    client = AsyncTypeSafeClient(timeout=60.0)
    gate = asyncio.Semaphore(concurrency)

    async def one(item):
        async with gate:
            return await grade(client, item)

    return await asyncio.gather(*(one(i) for i in items))


def main(langfuse=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--name", default="support-reply", help="trace name your app uses for a reply")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="grade and print, write nothing to Langfuse")
    a = ap.parse_args()

    if langfuse is None:
        from langfuse import get_client
        langfuse = get_client()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=a.hours)
    traces = list(fetch_traces(langfuse, since, a.name))
    items = [i for i in (to_item(t) for t in traces) if i]
    grades = asyncio.run(grade_items(items, a.concurrency))
    for g in grades:
        print(f"{g['id']}: {g['verdict']} (weighted {g['weighted']})")
        if not a.dry_run:
            write_scores(langfuse, g)
    langfuse.flush()
    print(f"{len(traces)} traces, {len(items)} graded, {len(traces) - len(items)} skipped (no message or reply).")


if __name__ == "__main__":
    main()
