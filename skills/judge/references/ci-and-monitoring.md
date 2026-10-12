# CI and monitoring

The same rubric code ([rubric.py](../examples/rubric.py) and the `grade` function in
[judge.py](../examples/judge.py)) runs in three places: a pytest gate, a promptfoo eval, and a job
that grades production traces. Keep one copy of the criteria and import it everywhere.

## pytest gate

[test_replies.py](../examples/test_replies.py), over saved cases in
[ci-cases.sample.jsonl](../examples/ci-cases.sample.jsonl) (`{"id", "input", "output"}` per line):

- `produce(case)` calls the bot; the sample returns the saved reply so the file runs as is.
- One test per case, parametrized: fails when a must-pass criterion clearly fails. A reply that
  asks for a card number blocks the merge, whatever the average.
- `test_pass_rate`: fails when the share of `pass` verdicts drops below `MIN_PASS_RATE`. Replies in
  `review` are printed and never counted as a pass.
- All cases are graded once per session, concurrently with a cap.

```sh
pip install typesafe-sdk pytest
TYPESAFE_BASE_URL=http://127.0.0.1:8080 pytest -q test_replies.py   # TYPESAFE_API_KEY from the CI secret store
```

Run on the sample with a VAKYN 4B: 7 passed; pass rate 83% (5 of 6), one reply to a person (`c04`,
a credit for a billing mistake that `state.rules` does not cover; `follows_rules` 0.78). The fix
for that is a rule in the state, not a lower bar.

In CI, the VAKYN server is a service container or a shared internal host; the key comes from the
CI secret store. Keep the cases file in the repo and add every escaped bad output to it.

## promptfoo

promptfoo runs Python assertions: `type: python` with `value: file://vakyn_assert.py`, calling
`get_assert(output, context)`; `context["vars"]` holds the test's variables. The function may
return a bool, a number, or a grading result with `pass`, `score`, `reason`, `componentResults`
and `named_scores`. [vakyn_assert.py](../examples/vakyn_assert.py) returns the full result: one
component per criterion, the weighted score, the request id in the reason.

[promptfooconfig.yaml](../examples/promptfooconfig.yaml) uses the `echo` provider to grade saved
replies; point `providers` at the bot to grade live outputs.

```sh
PROMPTFOO_PYTHON=.venv/bin/python npx promptfoo@latest eval -c promptfooconfig.yaml
```

`PROMPTFOO_PYTHON` points at a Python that has `typesafe-sdk`. Run on the sample: 1 passed, 2
failed (the reply asking for card details; "We are looking into it").

## Langfuse: scores on every trace

[langfuse_scores.py](../examples/langfuse_scores.py) lists recent traces with
`langfuse.api.trace.list(from_timestamp=..., name=..., limit=..., page=...)`, grades each one,
and writes scores with `langfuse.create_score(...)`:

- one `NUMERIC` score per criterion (`vakyn.next_step`, value 0 to 1), the VAKYN request id in
  the comment;
- one `CATEGORICAL` score `vakyn.verdict` (`pass`, `fail`, `review`);
- `score_id` built from the trace id, so a rerun updates the scores instead of adding new ones;
- `langfuse.flush()` before exit.

Adapt `to_item(trace)` to how the app logs input and output. Run it on a schedule over a time
window (`--hours 1`), or call `grade` right after the reply is sent. `--dry-run` grades without
writing. Checked against a stub Langfuse client on the 8 [sample replies](../examples/replies.sample.jsonl):
48 scores written, one trace without a reply skipped.

## Every trace, not a 5% sample

Chat-model judges are often run on a few percent of traffic because each grade is a paid call.
A VAKYN grade runs on the person's own server: the five-criterion rubric request took 51 to 58 ms
per request (VAKYN 4B Q8_0, one RTX 5090, one short reply, 10 sequential requests on a shared
server). Grade every trace when the server has room for it:

- a rare failure (a reply asking for a card number) shows up the day it starts, not weeks later;
- per-criterion rates can be tracked per day, per prompt version, per customer segment;
- the `review` share is a cost: every unsure grade goes to a person. Watch it next to the pass rate.

Size the job from the measured time on the person's own machine and the trace volume; put the
grader's requests behind the app's own traffic (a lower concurrency cap) if they share a server.
