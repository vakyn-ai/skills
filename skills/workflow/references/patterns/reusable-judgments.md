# Judgments as reusable data: score once, rank many ways

**Use when** the same items are sorted, filtered or ranked in many ways: listings by quiet,
light and condition; products by fit for several uses; support replies by several qualities. The
person (or a user, with sliders and filters) changes what matters often.
**Not when** each item is judged once for one decision (use [route](route.md) or
[rubric](rubric.md)).

The idea: **ask each dimension once per item, store the raw probabilities, and let code combine
them.** Changing a weight, a filter or a sort order never calls the server. Only a changed item
is asked again.

## The request

[examples/judgments.request.json](../../examples/judgments.request.json): the listing text in
the state; one `score` per dimension (quiet, light, condition) and a `noul` for "pets allowed".
Each scale has a level for "not described", so a silent listing lands in the middle instead of
at the bottom.

Answer from a running VAKYN 4B, on a courtyard flat with big south windows and a new kitchen:
quiet 2.99, light 2.99, condition 1.99 ("mixed: some parts new"), pets 0.99.

## The code

[examples/judgments.py](../../examples/judgments.py)

- `judge()` asks once per listing and stores a row: every score with its probabilities and
  confidence, the `noul`, and the request id.
- `rank()` reads only the stored rows. Weights and filters (`need_pets`) are arguments, so a
  slider in the UI moves the order without a request.
- `features()` turns a row into numbers (one per level, plus the `noul`), ready for a classical
  model such as logistic regression trained on the person's outcomes. Optional.

Run on three listings: quiet first → flat_17, flat_31, flat_22; condition first → flat_17,
flat_22, flat_31 (flat_22, noisy but new, moves up); pets required → flat_22 drops out.

## Unsure path

Store the confidence with each score. In the UI, mark a low-confidence dimension as "not sure"
rather than hiding the item. When ranking, an unsure score can count at its mean, or the item can
go below sure ones; that is a product choice, made in code.

## Common mistakes

- **Asking for the ranking.** "Which of these ten is quietest?" must be asked again for every
  change. Score each item once instead.
- **Storing only the pick.** Keep the probabilities: a later weight, a filter at a new cut-off or
  a classical model all need them.
- **Mixing dimensions.** "Bright and quiet" is two scores; combine them in code with the
  person's weights.
- **Old judgments on new text.** Store a hash of the text with the row and ask again when it
  changes.
