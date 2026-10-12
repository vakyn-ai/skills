---
type: llm
focus:
  source: file
  path: "review-check.fixed.json"
---

Look only at the `state` in this JSON file.
PASS if the state contains the customer's review of the CampFlex tent and the words
"Moderator summary" appear nowhere in the state. Otherwise FAIL.
