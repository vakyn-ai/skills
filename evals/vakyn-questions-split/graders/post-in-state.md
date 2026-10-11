---
type: llm
focus:
  source: file
  path: "post-check.json"
---

Judge only this one point; ignore everything else.
PASS if the post text sits in the state under its own key (for example `post` or `post_text`) and the questions refer to the post. FAIL if the post text is missing or mixed into the instructions.
