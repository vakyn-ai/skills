---
type: llm
focus:
  source: file
  path: "intent.v2.request.json"
---

Judge only this one point; ignore everything else in the answer.
The original request's six options are bare codes ("CRD": "CRD" and so on). Look at the candidate
request the agent saved or showed.

PASS if every one of the six options now has a description in words of what belongs in it (not just
the code repeated). FAIL if any option is still only its code or is missing.
