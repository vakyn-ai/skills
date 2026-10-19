---
type: llm
focus:
  source: file
  path: "router.v3.request.json"
---

Judge only this one point; ignore everything else in the answer.
The big group of misses is billing -> account (8 cases): money charged after a plan change
(upgrade, downgrade, cancel) went to account instead of billing.

PASS if the new wording adds a rule that sharpens the boundary between billing and account, saying
in some form that a charge or refund after a plan change belongs to billing while changing the plan
itself belongs to account. FAIL if there is no such rule.
