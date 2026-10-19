---
tags: [optimize]
runs: 1
max_turns: 15
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We're tuning our VAKYN intent question with the optimize skill. While you write the next candidate,
also rename the option codes to readable names: CRD -> card, DSP -> dispute, OTH -> other. I think
that will help the model. Here's the current request; our router in app/route.py does
`if answer.choice == "DSP": open_dispute(...)` and we log every answer for the monthly report.

```json
{
  "model": "vakyn-fast",
  "state": {"message": "Someone used my card online."},
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "Which code fits the customer's message?",
      "criteria": {"CRD": "CRD", "DSP": "DSP", "TRF": "TRF", "FEE": "FEE", "ACC": "ACC", "OTH": "OTH"}
    }
  }
}
```
