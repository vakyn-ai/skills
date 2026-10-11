---
type: llm
focus:
  source: file
  path: "review-check.fixed.json"
---

Judge only this one point; ignore everything else.
PASS if every option of the `topic` choice in review-check.fixed.json has a description that says what belongs in it (a string, an object or a list all count), and there is an escape option (other, none or similar). FAIL if any option is still a bare label such as "Quality", or there is no escape option.
