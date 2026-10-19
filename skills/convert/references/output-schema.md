# Convert an output schema into VAKYN questions

Many apps ask a chat model to fill a typed object: OpenAI structured outputs (`response_format`),
`instructor` (`response_model`), Zod with the Vercel AI SDK (`generateObject`), an Anthropic tool
used only as a schema, or JSON mode with the shape written in the prompt. The schema already
lists the decisions: every enum, boolean and rating in it is a question VAKYN can answer. The
free text stays with the chat model. Code rebuilds the same typed object, so the code after the
call does not change.

Worked examples, both run against a VAKYN 4B with the chat model stubbed:

| Before | After | Request |
|---|---|---|
| [schema-pydantic-before.py](../examples/schema-pydantic-before.py): OpenAI + Pydantic ticket triage | [schema_pydantic_after.py](../examples/schema_pydantic_after.py) | [schema-pydantic.request.json](../examples/schema-pydantic.request.json) |
| [schema-zod-before.ts](../examples/schema-zod-before.ts): Zod + `generateObject` listing review | [schema_zod_after.ts](../examples/schema_zod_after.ts) | [schema-zod.request.json](../examples/schema-zod.request.json) |

## 1. Find the schema and its descriptions

| The app uses | The schema is | Descriptions live in |
|---|---|---|
| OpenAI `chat.completions.parse(response_format=Model)` or `responses.parse(text_format=Model)` | the Pydantic model | `Field(description=...)`, the class docstring, comments |
| OpenAI `response_format={"type": "json_schema", ...}` | the JSON Schema under `json_schema.schema` | `description` on each property |
| OpenAI JSON mode (`{"type": "json_object"}`) | the prompt text | the prompt: use the [sort table](prompt-sort.md) |
| `instructor` (`response_model=Model`) | the Pydantic model | as for Pydantic |
| Zod with `generateObject({schema})` or `generateText` with `Output.object` | the Zod object | `.describe(...)`, comments |
| Anthropic, one tool forced with `tool_choice: {"type": "tool", "name": ...}` | that tool's `input_schema` | `description` on each property |
| TypeScript types passed to a schema generator | the type | `/** ... */` comments |

An Anthropic tool forced by name is a schema, not a tool pick: compile its fields here. A
tool list where the chat model chooses is a [tool pick](tool-pick.md).

## 2. Map each field

| Field shape | Becomes | How |
|---|---|---|
| `Enum`, `Literal["a", "b"]`, `z.enum`, a union of string literals, JSON Schema `enum` | **`choice`** | one option per value, named exactly as the value; add an escape option |
| `bool`, `z.boolean()`, `"type": "boolean"` | **`noul`** | `true` and `false` described from the field description |
| an ordered enum (`low`, `medium`, `high`) or a 1–N rating (`Field(ge=1, le=5)`, `z.number().min(1).max(4)`) | **`score`** | one level per step, lowest first, each described in words |
| a list of enum values (`list[Tag]`, `z.array(z.enum(...))`) | one **`noul` per value** | each label is its own yes/no question; code builds the list |
| a nested object | its fields, **flattened** | named questions such as `seller_looks_like_business`; code nests them again |
| a free-text string (summary, reply, title, reason) | **keep** with the chat model | the chat model writes it, as before |
| a number, date, ID, amount or name taken from the text | **not VAKYN** | code if it is exact; if code can find the candidates, [pick instead of generate](../../workflow/references/patterns/pick-value.md); otherwise keep |
| a value computed from other fields (a total, a priority from rules) | **code** | after the answers come back |

Notes:

- **Option names are the enum values.** Code maps an answer back with no lookup table. If a value
  is not a plain word (`"Account Access"`), name the option in snake_case and map it in code.
- **Escape option.** Add `other`, `none` or `cannot_tell` when the enum has none and a forced pick
  would be wrong (spam, an empty record, a case outside every value). An escape answer is not a
  valid enum value, so code treats it like an unsure answer (step 4).
- **Ratings need words.** "1 = angry, 5 = delighted" is two ends, not five levels. Write each
  level, or ask the person what 2 and 4 mean. Never send bare numbers: a level is a description
  ([score levels](../../questions/references/options-and-levels.md#score-levels)).
- **A rating with no clear order** (`Field(ge=1, le=10)` with no description) gets a question to
  the person before it becomes a `score`: what does each step look like?
- **Fields that depend on each other** ("reason, only when rejected") stay separate questions;
  code applies the condition. Questions in one request cannot see each other's answers.

## 3. Write the questions

- **The field description is the criteria.** Split it into option descriptions, `true`/`false`
  descriptions or level descriptions. Use the docstring and comments too. When a field has no
  description, write one from how the app uses the value and **ask the person to confirm it**.
- **The question text carries the meaning.** The question's name (`urgent`) is never sent to
  the model. Write the whole question: "Is the problem in state.ticket urgent for the support
  team?", with `true` and `false` saying what urgent means.
- **One request for the whole object.** All questions see the same state: the record the chat
  model got, under its own key (`ticket`, `listing`), without the old system prompt.
- Follow the [question checklist](../../get-started/references/checklist.md) and save the request as a
  `.json` file.

Show the person a field table, one row per field, every field accounted for:

```
| Field                       | Type             | Becomes                                  |
|-----------------------------|------------------|------------------------------------------|
| category                    | Category enum    | choice, 4 values + other                 |
| urgent                      | bool             | noul, true/false from the description    |
| sentiment                   | int 1–5          | score, 5 levels in words; level + 1      |
| summary                     | str              | keep: chat model                         |
```

## 4. Rebuild the typed object in code

1. Call VAKYN once. Read each answer by question name.
2. Turn each answer into the field's value:
   - `choice` → the option name, if it is one of the enum values and its `confidence` is at or
     above the threshold;
   - `noul` → `True` at or above the yes cut-off, `False` at or below the no cut-off, unsure
     between them;
   - `score` → the level mapped to the field's scale (level 0 is rating 1), if its `confidence`
     is at or above the threshold;
   - a list → built from its nouls, only when every label is answered;
   - a nested object → built from its flattened answers.

   Threshold and cut-off starting values: [thresholds](../../check/references/thresholds.md).
3. **Unsure fields go to the chat model**, in the same call that writes the free text: narrow the
   old schema to the kept fields plus the unsure ones (Pydantic `create_model` from the model's
   own fields, Zod `.pick(...)`), so their types and descriptions stay the same. Or send the
   record to a review queue; say which.
4. **Validate with the original schema** (`TicketTriage(**values)`, `ListingReview.parse(...)`).
   The caller gets the same type as before.
5. **Return the confidence beside each field** and where each field came from (`vakyn` or
   `chat`), next to the object, not inside it: a small wrapper such as `Triaged(value,
   confidence, source, request_id)`.

Run it **side by side first**: the old structured-output call is used, as before; VAKYN's answer
for each field is logged next to the chat model's as JSON lines. Switch with an environment
variable (`VAKYN_SCHEMA_MODE=vakyn`) once the `check` skill shows the two agree where it
matters. Check the code parses (`python3 -m py_compile`, `npx tsc --noEmit`).
