# Calibration: does "0.9" mean right 9 times in 10?

Calibration asks one thing: on the person's own records, when VAKYN says 0.9, is it right about
9 times in 10? It is a check on what the confidence number means, so thresholds and the unsure
path rest on something real. What confidence is: [confidence](../../questions/references/confidence.md).

## Only their own labeled records

- **Confidence is not accuracy on a different set of records.** A model can be well calibrated on
  one kind of text and too sure on another. Their tickets, their questions, their options: that is
  the only place the number means anything.
- **Never judge it with public benchmarks** or someone else's data. Only records from the real flow,
  labeled by a person (not by a chat model).
- **Calibration changes with the setup.** Redo it after any change to the question, the options,
  the state builder or the model file, and check those changes with a [drift check](drift.md).

## What you need

The same labeled file the [threshold page](thresholds.md#what-you-need) uses: one line per record,
`{"id", "vakyn_pick", "vakyn_confidence", "label"}` for `choice` and `score`, `{"id", "noul",
"label": true|false}` for `noul`, and `question` when one log holds several questions. How many
records: [sample sizes](thresholds.md#starting-values-and-sample-sizes). Calibration needs more than a
threshold does, because each group of the table needs enough records of its own.

## The reliability table

Group the records by the number VAKYN gave, then compare it with what happened:

| Column | `choice` / `score` | `noul` |
|---|---|---|
| Groups by | `confidence` (bands such as 0.5–0.7, …, 0.95–1.0) | the `noul` value itself, 0 to 1 (both sides) |
| Stated | mean confidence in the group | mean `noul` in the group |
| Observed | share VAKYN got right | share a person labeled true |
| Gap | stated minus observed: above 0 means too sure | above 0 means it says yes more readily than people do |

Also show the count per group and a 95% range for the observed share. A group with few records has
a wide range; do not read calibration from it.

**Calibration error** is the gap of each group, weighted by its share of the records. Read it in
plain words: "stated confidence is off by about N points, on average, from how often VAKYN is right".
Say the direction too (too sure or too modest).

## Steps

1. Check there are enough labeled records ([sample sizes](thresholds.md#starting-values-and-sample-sizes)).
   With fewer than 50, show the table but say it cannot judge calibration.
2. Per question, build the table and the calibration error.
3. Mark every group with too few records (the script marks fewer than 30) and read nothing from it.
4. Say what it means for the threshold: a group that is too sure near the threshold means a higher
   threshold, or more labels there. Pick the threshold itself on the [threshold page](thresholds.md).
5. A chart is optional (when matplotlib is installed); the text table always comes first.

Script for their project: [calibration.py](../examples/calibration.py) (standard library only):
`python3 calibration.py labeled.jsonl [--question team] [--chart reliability.png]`.

## Example (sample file)

`python3 calibration.py labeled.sample.jsonl` on [labeled.sample.jsonl](../examples/labeled.sample.jsonl)
(79 support tickets, real VAKYN answers, one `choice` question):

```text
group         records  mean confidence         share right     gap  95% range of observed
[0.00, 0.50]        3             0.44                0.67   -0.23  0.21 to 0.94  too few
(0.50, 0.70]        7             0.61                0.43   +0.18  0.16 to 0.75  too few
(0.70, 0.80]        4             0.77                0.25   +0.52  0.05 to 0.70  too few
(0.80, 0.90]        4             0.85                0.75   +0.10  0.30 to 0.95  too few
(0.90, 0.95]        4             0.94                0.75   +0.19  0.30 to 0.95  too few
(0.95, 1.00]       57             1.00                0.98   +0.01  0.91 to 1.00

Calibration error (weighted mean gap): 0.075 over 79 records.
Plain words: stated confidence is off by about 7 points, on average, from how often VAKYN is right; on balance confidence sits above accuracy (too sure by 6 points).
5 group(s) have fewer than 30 records: their share can move a lot with more labels (see the 95% range). Do not read calibration from those groups.
```

How to read it: only the top group has enough records. There, 0.95 and above was right 56 times in
57, which matches. Below 0.95 every group is too small: the gaps look large, but their 95% ranges
are wide (0.25 right at 0.77 could be anything from 0.05 to 0.70). The honest summary is "above 0.95
it holds on this sample; below it, we do not know yet; label more records with confidence under
0.95". The 7-point calibration error comes mostly from those small groups, so it is not a finding.

## Mistakes to avoid

- Claiming "well calibrated" or "too sure" from a group of a handful of records.
- Calibrating on records that do not come from the real flow, or on labels a chat model made.
- Reading accuracy straight off confidence ("it says 0.9, so 90% right") without this table.
- Fixing a bad gap by reshaping the numbers in code. Fix the question first
  ([diagnose](../../questions/references/diagnose.md)), then set the threshold from labels.
