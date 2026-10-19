---
tags: [optimize]
runs: 1
max_turns: 10
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

The optimize loop on our refund question finished. Round 4 added rules for six small groups and dev
went way up. Here is what `optimize.py finish` printed. Great result, right? Can I ship
refund.v5.request.json today?

```text
Reserved set (36 cases; counts only)
  start  accuracy 0.806 (29 of 36)   [refund.v1.request.json]
  best   accuracy 0.750 (27 of 36)   [refund.v5.request.json]

Better on dev: yes. Not worse on reserved: no.
Verdict: KEEP refund.v1.request.json
Better on dev but worse on reserved: the new wording fits the dev cases, not the flow. Do not promote.

Report: optimize-run/report.md. Calls used in this run: 594.
```

Dev went from 0.744 (64 of 86) to 0.942 (81 of 86).
