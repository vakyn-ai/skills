---
type: llm
focus:
  source: file
  path: "router.v3.request.json"
---

Judge only this one point; ignore everything else in the answer.
The other groups have one case each (shipping -> product, other -> product, product -> other) and
should not get their own rules. The previous descriptions were:
shipping "Deliveries, tracking, wrong or damaged parcels"; product "How the product works and
product faults"; other "Anything none of the teams above handle".

PASS if the descriptions of shipping, product and other are unchanged (or changed only trivially,
without a new rule) and the changes are about billing and account. FAIL if new rules were added
for the single-case groups or for shipping, product or other.
