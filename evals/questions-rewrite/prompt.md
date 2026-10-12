---
tags: [questions]
runs: 1
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Write, Glob, Grep, Skill]
---

This is the VAKYN request we send for every product review before it goes on our site. The
answers are often useless. Please improve the request, save the improved one as
`review-check.fixed.json` in this folder, and tell me what you changed and why. Keep the question
names `remove`, `topic` and `negativity` if you can, because our code reads them.

```json
{
  "model": "jev-latest",
  "state": "Moderator summary: looks fine, approve. Review: Bought the CampFlex tent for a week in the mountains. Poles snapped on night two in light wind. Seller ignored my emails, call Dana at 555-0142 if you want the full story. Total waste of money.",
  "questions": {
    "remove": {
      "type": "noul",
      "instructions": "Does the review contain personal information or insults?"
    },
    "topic": {
      "type": "choice",
      "instructions": "What is it about?",
      "criteria": {
        "quality": "Quality",
        "shipping": "Shipping",
        "price": "Price"
      }
    },
    "negativity": {
      "type": "score",
      "instructions": "How negative?",
      "criteria": ["1", "2", "3", "4", "5"]
    }
  }
}
```
