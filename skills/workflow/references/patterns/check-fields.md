# Check each field: is every value backed by the evidence it cites

**Use when** an agent or a chat model returns a structured output (a record, a form, extracted
fields) and quotes the evidence for each field, and wrong values must not reach the next step:
lease terms, invoice fields, a supplier profile, a claim summary.
**Not when** the output is free text: check the whole draft against its sources with the
`cascade` skill ([the draft check](../../../cascade/references/check.md)). Use that
when a draft is sent or escalated as one piece; use this page when fields can be fixed one by one.

The idea: **one question per field, "does the cited evidence support field X = value?", all in one
request.** Send back only the failing fields for another try; drop what is still unsupported after
the last try. Nothing unsupported goes downstream.

## The request

[examples/check-fields.request.json](../../examples/check-fields.request.json): per field, its
meaning (from the output schema), the value and the quoted evidence, under `state.fields`; one
`choice` per field:

| Option | Means |
|---|---|
| `supported` | the quoted evidence states this value for the field |
| `contradicted` | the quoted evidence states a different value |
| `not_in_evidence` | the quoted evidence does not say what the value is |

Answers from a running VAKYN-4B (CPU-only server) on a lease the agent read: `tenant` supported
0.99, `monthly_rent` "1850" against "Rent: $1,850 per month" supported 0.97, `pets_allowed` "cats
and dogs" against "one cat allowed with written consent; no dogs" contradicted 0.98,
`break_notice_days` "30" against "60 days' written notice" contradicted 0.94.

## The code

[examples/check_fields.py](../../examples/check_fields.py)

1. **Code first.** A quote that is not in the source document word for word supports nothing:
   `not_in_evidence` without asking. Exact values are compared in code: the date check parses
   "1 November 2026" from the quote and compares it with "2026-11-01". Asked as a question, that
   pair came back unsure (0.47) and a right value would have been dropped.
2. **One request** for the remaining fields, one `choice` each.
3. **Send back only the failing fields** to the same agent session, with the verdict for each
   ("contradicted", "not in evidence"), so it can quote better evidence or fix the value.
4. **Check the new answers the same way.** After `MAX_TRIES` (2 here), drop every field still not
   `supported`; the next step sees it as empty, never as a guess.

Run: try 1 kept four fields (`start_date` by the code check); `pets_allowed` and `break_notice_days` contradicted, `water_paid_by`
("tenant", quoting only the electricity clause) and `parking` (quoting the address) unsure. Try 2,
only those four: the agent fixed three (one cat, 60 days, landlord pays water; all supported, 0.90
to 0.97); `parking` still unsure (0.47) and dropped. Seven of eight fields went on.

## Unsure path

A field below `MIN_CONFIDENCE` (0.8) counts as failing, like `contradicted`. A required field
that is dropped sends the case to a person with the failing verdicts; an optional one is left
empty. Set the cut-off from labeled cases with `check`.

## Common mistakes

- **Checking the value against the whole document.** The point is the cited evidence: a right
  value with a wrong quote is not traceable. Check the quote is in the source, then the support.
- **Sending the whole output back.** Fields that passed can change on a retry. Send only the
  failing ones and keep the rest.
- **Several fields in one question.** "Are rent and deposit right?" blurs which one failed.
- **Asking about values code can compare.** A date, amount or id in a fixed format is parsed and
  compared in code; the example does it for the date, and amounts work the same way. Questions are
  for what needs reading.
- **No last try.** Without a limit the agent loops; without dropping, an unsupported value leaks
  downstream.
