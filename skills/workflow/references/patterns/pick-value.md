# Pick instead of generate: values, spans and line roles

**Use when** an app asks a chat model to write out a value that is already in the text: the
amount due, the due date, the sentence that states the cancellation term, the order number. Or
when pasted text lost its formatting and each line needs a role (heading, list item, paragraph).
**Not when** the value is not in the text and must be computed (code does that) or written (a
chat model or a person does that).

The idea: **code finds the candidates, VAKYN picks one, code copies it exactly.** Nothing is
generated, so nothing can be misspelled, rounded or invented.

## The request

[examples/pick-value.request.json](../../examples/pick-value.request.json): the email in the
state; one `choice` per field. Code found every amount and every date with a regular
expression. Each candidate is an option named after its value (`eur_1240_50`, `nov_14`) and
described by the value and the sentence it sits in, plus `none_of_these`.

Answer from a running VAKYN 4B, on an email with a €300 deposit, a €1,240.50 balance due by
14 November and a €25 late fee: `amount_due` → `eur_1240_50` (1.00), `due_date` → `nov_14` (1.00).

## Structure recovery

[examples/line-roles.request.json](../../examples/line-roles.request.json): the pasted text in
the state; one `choice` per line (`heading`, `list_item`, `paragraph`, `other`), with each line
quoted in its question. The options use [structured descriptions](../../../questions/references/options-and-levels.md#structured-descriptions):
what the role is and what it looks like.

Run on a pasted product page of nine lines: 8 of 9 right. The title and the two section names →
`heading`, the box contents → `list_item`, the sentences → `paragraph`, "Page 2 of 3" → `other`.
"Care guide", a list item that looks like a title, went to `heading` at confidence 0.65; below
the threshold, the code keeps it as plain text. With plain one-line descriptions the sentence
"Rinse after each use…" came back as `list_item` (0.98); the structured ones fixed it.

## The code

[examples/pick_value.py](../../examples/pick_value.py)

- `candidates()` finds every match and the sentence around it; ids come from the value, never
  from the position.
- After the pick, code returns `cands[pick]["value"]`: the text copied from the source, not
  anything the model wrote.
- `recover_structure()` asks all lines in one request and rebuilds Markdown. The words are never
  changed; only `## ` and `- ` are added.

Output: `{'amount': '€1,240.50', 'due_date': '14 November'}` and the page as Markdown.

## Unsure path

`none_of_these` or confidence below `MIN_CONFIDENCE` → the field stays empty and a person fills
it. For line roles the safe default is `paragraph`: the text stays, only the formatting is lost.

## Common mistakes

- **Candidates by position.** `option_1`, "the second amount". Name them by value.
- **Bare values as descriptions.** "€300" alone leaves the model guessing; the sentence around it
  is the evidence.
- **No `none_of_these`.** The regular expression may miss the real value, or the text may not
  state one.
- **Letting the model's text through.** The answer is an option name; the value always comes
  from code's own candidate list.
