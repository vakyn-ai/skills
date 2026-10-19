---
type: llm
focus:
  source: file
  path: "ironic.v2.request.json"
---

Judge only this one point; ignore everything else in the answer.
Judge the candidate request in ironic.v2.request.json.

PASS if it still has exactly one question named `ironic` of type `noul`, and any `criteria` it adds
use only the keys `true` and `false`. FAIL if the question is renamed, changed to another type, or
split into several questions.
