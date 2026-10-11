# Turn a task into a design

The person describes a task in plain words: "we get 400 repair requests a week and someone reads
each one to decide who goes and how soon". Produce a design they can run.

## 1. The design sheet

Write this back before any code. It is short enough to agree on in one reply.

| Part | Write |
|---|---|
| Decisions | Each judgment as one sentence, with its type: "which trade (`choice`)", "how urgent (`score`)" |
| Code rules | Everything exact: sums, dates, thresholds, lookups, required fields, "on-call if emergency" |
| Kept elsewhere | Text to write (replies, summaries, tool arguments): the chat model or a person |
| State | Each field, where it comes from (ticket body, customer record, last 3 messages) |
| Requests | Which questions share one request, which wait for an earlier answer |
| Unsure path | Per decision: the threshold setting and where unsure answers go |
| Volume | Records per day or per batch, so the concurrency cap is set |

Ask only what the sheet cannot be written without (usually: the options or teams, and where unsure
answers should go). Fill the rest with a clear default and say so.

## 2. Questions

Follow the `vakyn-questions` rules ([question types](../../vakyn-questions/references/question-types.md),
[options and levels](../../vakyn-questions/references/options-and-levels.md)):

- one judgment per question; several facts that can all be true → one `noul` each;
- `choice` options in snake_case with a one-line description and an escape option;
- `score` levels described by what you would observe, lowest first;
- each question names its subject in plain words ("the customer's message"; `state.message` also
  works), never a position.

## 3. The state builder

A function in the person's code, `build_state(record) -> dict`, that copies evidence from their
own data ([design the state](../../vakyn-questions/references/state.md)):

- the text being judged, under its own key (`message`, `claim`, `agent_reply`);
- facts that help judge it (plan, product, steps already done), already worked out by code;
- nothing that is a conclusion (a chat model's summary, "looks fine, approve");
- short: the last few turns, the relevant section, the filtered candidates.

Name where each field comes from (a table column, an API, the form). If a needed fact is not
available, say so and add a `not_enough_evidence` option instead of guessing.

## 4. The code

Python or TypeScript, whichever the project uses, with the official SDK
([SDK guide](../../vakyn/references/sdk.md)). Start from the closest pattern's example. Every
design has:

- the options and levels as named constants, shared by the request and the checks;
- `build_state`, one function per request, and the code rules after the answers;
- a check that a `choice` pick is one of the offered options;
- the thresholds as named settings with a comment that they are tuned later;
- the request id logged with the answer;
- the [batching](batching.md) shape for the volume.

## 5. Show the result

Give the person: the design sheet, each request as a `.json` file, the code file, and one line per
decision on what happens when VAKYN is unsure. If a server is reachable, send each request and
show the real answers. If not, say so; never invent answers.
