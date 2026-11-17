---
type: llm
---

Judge only this one point; ignore everything else in the answer.

PASS if it sets VAKYN_API_KEY (and, if it sets a base URL at all, VAKYN_BASE_URL with
https://api.vakyn.com). FAIL if it does not name VAKYN_API_KEY, or tells the person to set other
variable names for the key.
