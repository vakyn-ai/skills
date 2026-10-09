# Side-by-side log summary

A converted app (`vakyn-convert`) runs side by side first: VAKYN and the chat model both pick, the
app acts on the chat model's pick, and both picks go to a log. This page reads that log and says
whether to switch.

## Log format

JSON lines, one decision per line:

```json
{"ts": "2026-10-06T08:20:13Z", "request_id": "req_9f92…", "vakyn_pick": "refund_order",
 "vakyn_confidence": 0.99, "vakyn_probabilities": {"refund_order": 0.99, "search_orders": 0.01},
 "chat_pick": "refund_order", "agree": true, "mode": "side_by_side", "used": "chat"}
```

| Field | Meaning |
|---|---|
| `ts` | UTC time of the decision |
| `request_id` | VAKYN's `x-typesafe-request-id`; finds the record again |
| `vakyn_pick` | VAKYN's option (`"true"` / `"false"` for a `noul`) |
| `vakyn_confidence` | `confidence`; for a `noul`, `abs(2 * noul - 1)` |
| `vakyn_probabilities` | the full distribution |
| `chat_pick` | the chat model's option |
| `agree` | `vakyn_pick == chat_pick` (recompute it; don't trust it blindly) |
| `mode` | `side_by_side` (both pick) or `vakyn` (switched on) |
| `used` | whose pick the app acted on: `chat` or `vakyn` |
| `label` | optional: what a person says is right, added during review |

Sample: [side-by-side.sample.jsonl](../examples/side-by-side.sample.jsonl) (40 tool picks).

## Steps

1. **Read the whole log** with a short script in their project. Template:
   [log_summary.py](../examples/log_summary.py) (standard library only). Keep only
   `mode: side_by_side` lines.
2. **Agreement**: overall `k/n` and %, then per option (by the chat model's pick), with what VAKYN
   picked instead.
3. **Confusion pairs**: chat → VAKYN counts. Two options that swap often usually overlap; fix
   their descriptions before anything else ([options](../../vakyn-questions/references/options-and-levels.md)).
4. **By confidence**: for each threshold, how many VAKYN would answer and the agreement on those;
   the rest is the unsure share that would go to the chat model.
5. **Disagreements to label**: list them, most confident VAKYN first. Those are the costly ones: if
   VAKYN is confident and wrong, a threshold will not catch it. Ask the person to label these
   (and a random handful of agreements) and add a `label` field.
6. **Recommend**, with the evidence for it and what would change it.

## Reading the numbers (sample log)

Running the template on the sample gives 31/40 agreement (78%). At confidence ≥ 0.7, VAKYN
answers 26 of 40 and agrees on 25 of them (96%); the 14 below go to the chat model. Most
disagreements sit below 0.6. The one confident disagreement ("Can I get my money back?", VAKYN
`refund_order` at 0.91, chat `ask_user`) is a question of policy: which is right is the person's
call. Several of the low-confidence ones pick `none` for a tracking question; that points at the
`track_shipment` description.

## Recommend

Say one of these, with the numbers:

| Finding | Recommendation |
|---|---|
| High agreement above a threshold, disagreements mostly below it, labels (if any) side with VAKYN or split | Switch with that threshold; below it, the chat model answers |
| Disagreements cluster on one or two option pairs | Fix those options first, run side by side again |
| Confident disagreements, no labels | Not yet: label those records, then decide |
| Labels show the chat model right where they differ | Keep the chat model for this question, or rewrite it |
| Too few lines (under ~100 per option that matters) | Keep logging; say how many more are needed |

Always add **what would change the advice**: "if the labels on the 9 disagreements go to the chat
model, keep it"; "if a week's log keeps agreement above the threshold at this level, switch".
Agreement says they pick the same, not that either is right. The threshold itself comes from
labels: [thresholds](thresholds.md).
