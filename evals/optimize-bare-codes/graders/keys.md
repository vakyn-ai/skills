---
type: llm
focus:
  source: file
  path: "intent.v2.request.json"
---

Judge only this one point; ignore everything else in the answer.
Judge the candidate request in intent.v2.request.json.

PASS if the question is still named `intent`, is still a `choice`, and its option keys are exactly
CRD, DSP, TRF, FEE, ACC and OTH (same spelling and case, none added, none removed). FAIL if any key
is renamed (for example to "card" or "other"), added or removed, or the question is renamed.
