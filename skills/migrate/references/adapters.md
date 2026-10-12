# Framework adapters

How to point each adapter at the person's server. Checked 2026-10-09 in each package's source
or official docs, and run against a live open-server where marked. Model: `jev-latest`.

| Adapter | Package | Base URL setting | Key | Ran live |
|---|---|---|---|---|
| Pydantic AI | `pydantic-ai-slim[typesafe]` 2.54 | `TYPESAFE_BASE_URL` or `TypeSafeProvider(base_url=)` | `TYPESAFE_API_KEY` | yes |
| Vercel AI SDK | `@ai-sdk/typesafe-ai` 3.0.17, `ai` ≥ 7.0.128 | `TYPESAFE_AI_BASE_URL` or `createTypeSafeAi({ baseURL })`, **with `/v1`** | `TYPESAFE_AI_API_KEY` | yes |
| TanStack AI | `@tanstack/ai-typesafe` 0.1.9 | `typesafeDecider(model, { baseURL })`; no variable | `TYPESAFE_API_KEY` | yes |
| LangChain | `langchain-typesafe` 0.0.1a3 (beta) | `TYPESAFE_BASE_URL` or `TypeSafeClassifier(base_url=)` | `TYPESAFE_API_KEY` | yes |
| Langfuse decision-model evaluator | Langfuse UI | none documented | | no; use the wrapper below |

## Pydantic AI

`TypeSafeModel` builds its client from `TypeSafeProvider`, which reads `TYPESAFE_BASE_URL` and
`TYPESAFE_API_KEY`. With the variables set, `Agent('typesafe:jev-latest', ...)` needs no code
change. Explicit:

```python
from pydantic_ai import Agent
from pydantic_ai.models.typesafe import TypeSafeModel
from pydantic_ai.providers.typesafe import TypeSafeProvider

model = TypeSafeModel("jev-latest", provider=TypeSafeProvider(base_url=os.environ["TYPESAFE_BASE_URL"]))
agent = Agent(model, output_type=Handling)
```

A pinned name (`jev-1.13.0`) or `jev-preview` in `TypeSafeModel(...)` or the `typesafe:` string
must become `jev-latest`. Find: `grep -rnE "TypeSafeModel|TypeSafeProvider|typesafe:jev" .`

## Vercel AI SDK

The TypeSafe provider has its **own** variable names, and its base URL **ends in `/v1`**
(default `https://api.typesafe.ai/v1`; it appends `/systemone`). Without `/v1` the call goes to
`/systemone` and gets 404 (seen on open-server).

```sh
TYPESAFE_AI_BASE_URL=http://127.0.0.1:8080/v1
TYPESAFE_AI_API_KEY=vk_...
```

A call through AI Gateway (`model: 'typesafe-ai/jev'` as a string, or `gateway.decisionModel`)
becomes `typeSafeAi.decisionModel('jev-latest')`. The `decide` call, `boolean` questions and
`answers` stay the same; `confidence` is in `result.providerMetadata.typesafe.confidence`.
Before/after: [ai_sdk_before.ts](../examples/ai_sdk_before.ts), [ai_sdk_after.ts](../examples/ai_sdk_after.ts).

Find: `grep -rnE "experimental_decide|experimental_evaluate|@ai-sdk/typesafe-ai|createTypeSafeAi|typeSafeAi|decisionModel\(" .`

## TanStack AI

`typesafeDecider(model, config)` reads the key from `TYPESAFE_API_KEY` but takes the base URL
**only from code** (`baseURL`, alias `baseUrl`; no `/v1`; the adapter appends `/v1/systemone`).
Make it config:

```ts
const adapter = typesafeDecider(process.env.DECISION_MODEL ?? "jev-latest", {
  baseURL: process.env.TYPESAFE_BASE_URL, // http://127.0.0.1:8080
});
```

Answers come back as `{type: "boolean", value, probability}` for yes/no questions. Find:
`grep -rnE "@tanstack/ai-typesafe|typesafeDecider|createTypesafeDecider" .`

## LangChain

`TypeSafeClassifier` (a Runnable, beta) reads `TYPESAFE_BASE_URL` and `TYPESAFE_API_KEY`;
`base_url=`, `api_key=`, `model=` override them. Default model `jev-latest`. The experimental
middlewares are built on the same class. Find: `grep -rnE "langchain_typesafe|TypeSafeClassifier" .`

## Langfuse

The decision-model evaluator is set up in the Langfuse UI with the `typesafe` adapter and one of
three upstreams (TypeSafe, Vercel AI Gateway, OpenRouter). Its docs say no base URL is needed and
show no way to set one, so it cannot be pointed at the person's server as documented. Do not
claim otherwise; if the person's Langfuse version shows a base URL field, follow its docs.

Alternative: a small job that reads observations, asks VAKYN with the official SDK, and writes
each answer back as a Langfuse score:

```python
from langfuse import get_client
from typesafe_sdk import Noul, TypeSafeClient

langfuse, vakyn = get_client(), TypeSafeClient()  # TYPESAFE_BASE_URL / TYPESAFE_API_KEY → own server

def judge(trace_id: str, question: str, answer: str) -> None:
    r = vakyn.system_one(
        state={"question": question, "answer": answer},
        questions={"grounded": Noul(instructions="Does state.answer answer state.question without making things up?")},
    )
    langfuse.create_score(trace_id=trace_id, name="grounded", value=r.nouls["grounded"].noul,
                          data_type="NUMERIC", comment=r.request_id)
```

`create_score` (Python, checked in `langfuse` 4.17 source) and `langfuse.score.create`
(TypeScript) are from Langfuse's "scores via SDK" docs. For rubric design and CI, use the `judge` skill.

## Any other adapter

Read its source or docs for: the variable or option that sets the base URL, whether the base
URL includes `/v1`, which variable holds the key, and how the model name is passed. If there is
no base URL setting, wrap the official SDK in a small function with the same inputs and outputs
the adapter had, as with Langfuse above.
