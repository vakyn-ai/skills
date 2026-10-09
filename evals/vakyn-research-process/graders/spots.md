---
type: llm
focus:
  source: file
  path: "vakyn-research.md"
---

Judge the report in vakyn-research.md. The described
process has these steps:
- claim type (car, home, travel, health): a decision, `choice`, ideally with an "other" option;
- required documents attached: a decision, `noul` (one per document is also fine);
- suspicious, send to the fraud team: a decision (`noul` or `score`), rated higher risk, with a
  person checking flagged or unsure claims;
- policy active on the incident date: does NOT fit VAKYN alone (a lookup and a date check that code
  or the policy system does; its result may go into VAKYN's state);
- the letter to the customer: writing, marked keep.

PASS if the three decision steps are listed as spots with fitting question types, the policy check
is marked as not fitting (or as code/lookup), the letter is marked keep, the spots are ranked with
gain, risk and effort, and the next skill named is vakyn-workflow (vakyn-questions or vakyn-check
may also appear). FAIL if the letter or the policy date check is proposed as a VAKYN decision, if a
decision step is missing, or if there is no ranking.
