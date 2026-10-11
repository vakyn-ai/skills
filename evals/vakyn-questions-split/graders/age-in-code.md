---
type: llm
focus:
  source: file
  path: "post-check.json"
---

Judge only this one point; ignore everything else.
PASS if post-check.json has no question about the account age ("less than a week old"); the age is left to code. FAIL if VAKYN is asked about the account age.
