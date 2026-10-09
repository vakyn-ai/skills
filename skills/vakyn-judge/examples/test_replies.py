"""CI gate: grade the support bot's replies on saved cases with VAKYN.

    pip install typesafe-sdk pytest
    TYPESAFE_BASE_URL=... TYPESAFE_API_KEY=... pytest -q test_replies.py

Two levels:
- each case fails on its own when a must-pass criterion clearly fails (a reply asking for a card
  number must block the merge, whatever the average);
- the run fails when the share of passing replies drops below MIN_PASS_RATE.
Replies that VAKYN is unsure about are counted and printed, never counted as a pass.
"""

import asyncio
import json
import pathlib

import pytest
from typesafe_sdk import AsyncTypeSafeClient

from judge import grade

CASES = [json.loads(line) for line in open(pathlib.Path(__file__).parent / "ci-cases.sample.jsonl") if line.strip()]
MIN_PASS_RATE = 0.8  # a named setting: set it from your own history, raise it as the bot improves


def produce(case):
    """Call your bot here. The sample file stores the reply it gave, so the example runs as is."""
    return case["output"]


@pytest.fixture(scope="session")
def grades():
    async def run():
        client = AsyncTypeSafeClient(timeout=60.0)
        gate = asyncio.Semaphore(4)

        async def one(case):
            async with gate:
                return await grade(client, {**case, "output": produce(case)})

        return {g["id"]: g for g in await asyncio.gather(*(one(c) for c in CASES))}

    return asyncio.run(run())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_no_must_pass_failure(case, grades):
    g = grades[case["id"]]
    assert not g["failed"], f"{case['id']} fails {g['failed']} (request {g['request_id']}): {case['output'][:80]}"


def test_pass_rate(grades):
    passed = sum(g["verdict"] == "pass" for g in grades.values())
    review = [g["id"] for g in grades.values() if g["verdict"] == "review"]
    rate = passed / len(grades)
    print(f"pass rate {rate:.0%} ({passed}/{len(grades)}); to a person: {review or 'none'}")
    assert rate >= MIN_PASS_RATE, f"pass rate {rate:.0%} is below {MIN_PASS_RATE:.0%}"
