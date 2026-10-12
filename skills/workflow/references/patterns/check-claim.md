# Check a claim: is this statement backed by this document

**Use when** a statement must be checked against a source: marketing copy against a product spec,
an answer against a help article, a summary against a contract.
**Not when** the check is exact (a number equals a field, a date is in range): compare in code.

## The request

[examples/check-claim.request.json](../../examples/check-claim.request.json): the source under
`product_spec`, one claim under `claim`, and one `choice`:

| Option | Means |
|---|---|
| `supported` | the source states facts that make the claim true |
| `contradicted` | the source states facts that make the claim false |
| `not_enough_evidence` | the source does not say enough |

Answer from a running VAKYN 4B: "charges fully in under two hours" against a spec that says 3.5
hours → `contradicted`, confidence 0.97.

The three-way `choice` keeps "false" apart from "not stated". If you only need a gate, two nouls
work too: "Does state.product_spec state facts that make state.claim true?" and the same for false;
both low means not enough evidence.

## The code

[examples/check_claim.py](../../examples/check_claim.py)

Code splits the copy into single claims (one sentence each) and checks them concurrently, one
request per claim, the same spec in each state.

Run on four claims: under two hours → `contradicted` (0.97); "survives half an hour underwater"
→ `supported` (0.99); stereo pairing → `supported` (1.00); "80% recycled plastic" →
`not_enough_evidence` (1.00).

## Unsure path

Only `supported` above a high bar (`MIN_CONFIDENCE = 0.8`) is published. Everything else goes to
an editor with the verdict, so they start with the claims most likely to be wrong.

## Common mistakes

- **Several claims in one question.** "Waterproof, light and charges fast?" gets one blurred
  answer. One claim per request.
- **Yes or no only.** A `noul` "is it true?" mixes "the spec says otherwise" with "the spec does
  not say"; the first is a fix, the second is a question for the product team.
- **The source too long.** State plus question must stay under 32,768 tokens. Send only the
  sections that matter, or ask per section and combine in code.
- **Someone's opinion in the state.** "Legal approved this page" is not evidence about the claim.
