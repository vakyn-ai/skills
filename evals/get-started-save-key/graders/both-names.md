---
type: llm
---

Judge only this one point; ignore everything else in the answer.

PASS if it sets both the VAKYN_ variables and the TYPESAFE_ variables (API key and base URL
https://api.vakyn.com), or explains that the SDKs read TYPESAFE_API_KEY and the scripts VAKYN_API_KEY.
FAIL if only one of the two names is mentioned.
