# Fill a form step: which field to ask about next

**Use when** an assistant fills a form by talking with a person (a claim, an intake, an order) and
must choose which empty field to ask about next, or when to stop or hand over.
**Not when** the order is fixed: a list in code is simpler. VAKYN does not pull the values out of
the reply either; your chat model or a parser fills fields.

## The request

[examples/form-step.request.json](../../examples/form-step.request.json): the filled fields and
the person's latest reply in the state; one `choice` over the empty fields only, each with what it
is for, plus two endings: `ready_to_submit` and `needs_person` (the escape option).

Answer from a running VAKYN 4B: "A pipe burst … it is still dripping into the cupboard below" →
`emergency_help`, confidence 0.89.

## The code

[examples/form_step.py](../../examples/form_step.py)

- Code knows which fields are filled and offers only the empty ones. With none empty, it submits
  without asking.
- On a field, your chat model or a template words the question; on `needs_person`, a claims
  handler takes over.

Run on three steps: still dripping → `emergency_help`; plumber booked, tiles ruined →
`damaged_items`; "I do not understand why you need all this … it is not even my pipe!" →
`needs_person`.

## Unsure path

Below `MIN_CONFIDENCE`, ask the empty fields in their fixed order. A plain next field is a safe
fallback; a wrong hand-over is not.

## Common mistakes

- **Not saying what "next" means.** Asked only "which field next?", the same reply split between
  `emergency_help` (0.54) and `incident_date` (0.31). Adding "Ask first about what matters most for
  the person right now" gave `emergency_help` 0.90. Put the ordering principle in the question.
- **Offering filled fields.** Code removes them; the model should not track what is filled.
- **Required-field rules in the question.** "Police report only for theft" is code: decide the
  fields from `claim_type`, then ask.
- **No hand-over option.** Without `needs_person`, an upset person gets another form question.
