---
type: llm
focus:
  source: file
  path: "router.v3.request.json"
---

Judge only this one point; ignore everything else in the answer.
Judge the candidate request in router.v3.request.json.

PASS if the question is still named `team`, still a `choice`, with exactly the option keys billing,
account, shipping, product and other. FAIL if any key is renamed, added or removed.
