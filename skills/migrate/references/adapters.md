# Framework adapters

How to find each adapter in the person's code and replace it with a direct HTTP call to VAKYN
Cloud (`https://api.vakyn.com`) or the person's own server. The package names, settings and
answer shapes below are the adapters' own, checked 2026-10-09 in each package's source or
official docs; they are here so the calls can be found and their callers kept working.

The replacement is the same every time: one `decide(state, questions)` function over HTTP
([HTTP guide](../../get-started/references/http.md)), reading `VAKYN_API_KEY` and `VAKYN_BASE_URL`,
plus a few lines that hand the caller what the adapter used to return. The adapter package stays
installed only while the old path is kept for rollback.

| Adapter | Package | How to find it | What callers got back |
|---|---|---|---|
| Pydantic AI | `pydantic-ai-slim[typesafe]` 2.54 | `TypeSafeModel`, `TypeSafeProvider`, `typesafe:` model strings; reads `TYPESAFE_BASE_URL`, `TYPESAFE_API_KEY` | the agent's `output_type` object |
| Vercel AI SDK | `@ai-sdk/typesafe-ai` 3.0.17, `ai` ≥ 7.0.128 | `experimental_decide`, `typeSafeAi`, `createTypeSafeAi`, `decisionModel(`; reads `TYPESAFE_AI_BASE_URL` (with `/v1`), `TYPESAFE_AI_API_KEY` | `answers` with `boolean` answers as `probability`; confidence in `providerMetadata.typesafe` |
| TanStack AI | `@tanstack/ai-typesafe` 0.1.9 | `typesafeDecider`, `createTypesafeDecider`; key from `TYPESAFE_API_KEY`, base URL only in code | `{type: "boolean", value, probability}` for yes/no |
| LangChain | `langchain-typesafe` 0.0.1a3 (beta) | `langchain_typesafe`, `TypeSafeClassifier` (a Runnable); reads `TYPESAFE_BASE_URL`, `TYPESAFE_API_KEY` | the answers, inside a chain |
| Langfuse decision-model evaluator | Langfuse UI | an evaluator set up with the `typesafe` adapter | a Langfuse score |

## Pydantic AI

Find: `grep -rnE "TypeSafeModel|TypeSafeProvider|typesafe:jev" .` A typical call:
`Agent('typesafe:jev-latest', output_type=Handling)` or `TypeSafeModel("jev-1.13.0", provider=...)`.

Replace the agent call with `decide(...)`: each field of the `output_type` becomes a question
(an enum a `choice`, a bool a `noul`, a rating a `score`), and code builds the same `Handling`
object from the answers, so callers do not change. The method is the `convert` skill's
[output schema](../../convert/references/output-schema.md) page.

## Vercel AI SDK

Find: `grep -rnE "experimental_decide|experimental_evaluate|@ai-sdk/typesafe-ai|createTypeSafeAi|typeSafeAi|decisionModel\(" .`
A call through AI Gateway (`model: 'typesafe-ai/jev'` as a string, or `gateway.decisionModel`)
and a call through the TypeSafe provider look the same apart from `model`.

Replace `decide({ model, state, questions })` with a `fetch` POST to
`${VAKYN_BASE_URL}/v1/systemone` (the root, no `/v1` in the variable). The body changes in two
places: question `type: "boolean"` becomes `"noul"` (same `instructions`, `criteria`
`{true, false}`), and `model` goes (or is the `/v1/models` name on open-server). In the answers,
a yes/no answer's `probability` is `noul`; `confidence` is on each choice and score answer, not in
provider metadata. Before/after: [ai_sdk_before.ts](../examples/ai_sdk_before.ts),
[ai_sdk_after.ts](../examples/ai_sdk_after.ts).

## TanStack AI

Find: `grep -rnE "@tanstack/ai-typesafe|typesafeDecider|createTypesafeDecider" .`

Replace the decider with a `fetch` call. Callers that read `{type: "boolean", value, probability}`
keep working with a two-line map from VAKYN's noul answer:

```ts
const yesNo = (a: { noul: number }) => ({ type: "boolean", value: a.noul >= 0.5, probability: a.noul });
```

## LangChain

Find: `grep -rnE "langchain_typesafe|TypeSafeClassifier" .` The experimental middlewares are
built on the same class.

Replace `TypeSafeClassifier(...)` with a `RunnableLambda` around the HTTP function, so the chain
around it stays the same:

```python
from langchain_core.runnables import RunnableLambda

QUESTIONS = {"topic": {"type": "choice", "instructions": "What is state.text mainly about?",
                       "criteria": {"billing": "Charges and refunds", "other": "None of these fits"}}}
classify = RunnableLambda(lambda text: decide({"text": text}, QUESTIONS))  # decide: the HTTP guide's function
```

## Langfuse

The decision-model evaluator is set up in the Langfuse UI with the `typesafe` adapter and one of
three upstreams (TypeSafe, Vercel AI Gateway, OpenRouter). Its docs say no base URL is needed and
show no way to set one, so it cannot be pointed at VAKYN as documented. Do not claim otherwise.

Replace it with a small job that reads observations, asks VAKYN over HTTP, and writes each
answer back as a Langfuse score:

```python
import json
import os
import urllib.request

from langfuse import get_client

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")
QUESTION = {"type": "noul", "instructions": "Does state.answer answer state.question without making things up?"}
langfuse = get_client()


def judge(trace_id: str, question: str, answer: str) -> None:
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": {"question": question, "answer": answer},
                         "questions": {"grounded": QUESTION}}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        noul = json.load(r)["answers"]["grounded"]["noul"]
        request_id = r.headers.get("x-vakyn-request-id")
    langfuse.create_score(trace_id=trace_id, name="grounded", value=noul,
                          data_type="NUMERIC", comment=request_id)
```

`create_score` (Python, checked in `langfuse` 4.17 source) and `langfuse.score.create`
(TypeScript) are from Langfuse's "scores via SDK" docs. For rubric design and CI, use the `judge` skill.

## Any other adapter

Read its source or docs for: which calls it makes, how it builds the questions, what it hands
back to the caller, and which variables hold its URL and key (so they can be found and retired).
Then replace it with a small HTTP function with the same inputs and outputs the adapter had,
as with Langfuse above.
