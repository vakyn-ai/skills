---
type: llm
focus:
  source: file
  path: "intent.v2.request.json"
---

Judge only this one point; ignore everything else in the answer.
Judge the candidate request in intent.v2.request.json.

PASS if the new wording describes kinds of messages in general terms and does not paste the
listed dev messages (for example "Why was I charged 5 for using a cash machine abroad?") into the
instructions or descriptions. Short made-up examples are fine. FAIL if one or more dev messages
are copied into the wording.
