# Replay: re-decide stored answers when the decision code changes

VAKYN says what a case is; code says what follows ("refund requests go to the refunds desk",
"below 0.8, a person looks"). When only the code side changes (a rule, a threshold, the order of
the rules), the answers are still good. Store every answer once, with its probabilities, and re-run
the new code over the stored answers. No model calls, no cost, and the whole history is replayed in
seconds.

## Replay or drift check

| | Replay | [Drift check](drift.md) |
|---|---|---|
| What changed | the decision code, a threshold, a rule, the policy file | the model file, the server, a question's text or options, the state builder |
| What runs | the new code over stored answers | VAKYN again, on a stored reference batch |
| Model calls | none | one request per record |
| It shows | which cases now get a different outcome, and which rule made the difference | which answers moved, by how much |
| Valid while | the questions and the state builder are the same as when the answers were stored | always; it is how a new reference batch is made |

A change to a question makes its stored answers stale: they answer the old question. The script
checks the question hashes and skips those cases; re-ask them with a drift check. A new question
the code needs has no stored answer at all; record it from now on, or ask it on the stored inputs
(a model call, so a drift-style batch).

## What to store

One line per decision, the [audit record](go-live.md#audit-record): case id, step, model name,
request id, the input (or its hash and where it is kept), a hash per question, **every answer with
its probabilities** (a pick alone cannot be re-thresholded), the policy version and its hash, the
outcome and the reason. The same line serves the audit, the replay and the
[tuning](tuning.md) of the next version. Sample: [answers.sample.jsonl](../examples/answers.sample.jsonl)
(100 support tickets, real answers from a VAKYN-4B).

## Steps

1. **Put thresholds and rules in a versioned file**, not in literals:
   [routing-policy.v1.json](../examples/routing-policy.v1.json). The decision code reads it.
   A change is a new file or a new version in git, reviewed like code.
2. **Store an audit record per decision** in the app, from the first day. Template:
   `python3 replay.py record --request drift.request.json --records tickets.jsonl --policy routing-policy.v1.json`.
3. **Edit the rule or the code**, then replay: `python3 replay.py replay --answers answers.jsonl
   --policy routing-policy.v2.json --request drift.request.json`. Replaying with the policy the
   answers were decided under must show 0 changes; if not, the code changed too, or the log is
   incomplete.
4. **Report**: how many cases changed outcome, from which outcome to which, and per case the old
   outcome with its reason next to the new one with its reason.
5. **A changed outcome is not a better one.** Check the changed cases against labels on a dev set
   and a reserved set before the new version goes live: [tuning](tuning.md).

Script for their project: [replay.py](../examples/replay.py) (`replay` needs only the standard
library; `record` needs the SDK).

## Example (sample file)

The tickets were answered once with two questions (`team`, a `choice`; `wants_refund`, a `noul`;
[drift.request.json](../examples/drift.request.json)) and decided under `routing-v1`: refunds desk
only for tickets VAKYN put in `billing` with confidence at or above 0.8; below 0.8, a person.
`routing-v2` makes two edits: refund requests go to the refunds desk whatever the team, and the
team cut-off drops to 0.7.

```text
Stored: 100 cases, step route_ticket, decided under routing-v1 (9a3a3f4846ec): 100
Models in the stored answers: VAKYN-4B
Replaying with: routing-v2 (07d0974eccfd). No model calls.

Outcome changed: 7/100 cases (7%)
     triage -> refunds   4
     triage -> access    2
   shipping -> refunds   1

Changed cases (stored outcome and reason -> new outcome and reason):
  t021  triage (team access 0.79 < 0.8)
        -> access (team access 0.79 >= 0.7)
  t060  triage (team billing 0.37 < 0.8)
        -> refunds (wants_refund 1.00 >= 0.8, from any team)
  t068  triage (team access 0.78 < 0.8)
        -> access (team access 0.78 >= 0.7)
  t081  shipping (team shipping 1.00 >= 0.8)
        -> refunds (wants_refund 1.00 >= 0.8, from any team)
  ...
```

How to read it: two edits, two kinds of change. The refund rule moves five refund requests that
VAKYN was unsure how to route ("The order never arrived so I want my money back", t060) to the
refunds desk. The lower cut-off sends two tickets straight to `access`; one of them, t068 ("After
the update I can sign in but every page is blank"), is a product bug. Whether the version is better
is for the labels to say: [tuning](tuning.md#example-sample-files) shows `routing-v2` is not
promoted and a version with only the refund edit is.

Recording the 100 tickets took 4 minutes 28 seconds (one request at a time, CPU-only server,
shared with other jobs). Replaying 20,000 stored decisions took 0.16 seconds on the same machine
(AMD Ryzen 9 9950X3D), with no server. A replay sends no requests, so on VAKYN Cloud it spends
nothing; recording the answers in the first place is what costs balance.

## Mistakes to avoid

- **Storing only the pick or the outcome.** A new threshold needs the probabilities.
- **Replaying across a question change.** Stale answers give confident nonsense; check the hashes.
- **Thresholds as literals in code.** Nobody can tell which version decided a case.
- **Promoting because outcomes changed.** Changed is not better; labels decide.
