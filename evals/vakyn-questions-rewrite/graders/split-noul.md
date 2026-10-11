---
type: llm
focus:
  source: file
  path: "review-check.fixed.json"
---

Judge only this one point; ignore everything else.
PASS if review-check.fixed.json asks about personal information and about insults in separate questions, one proposition each. FAIL if one noul still asks about both, even if the answer recommends splitting it.
