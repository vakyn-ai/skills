---
tags: [vakyn-check]
runs: 1
max_turns: 15
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We use VAKYN to pick the expense category for receipts (a `choice` with travel, meals, software,
office, other). Our finance lead checked 24 receipts by hand (label = the right category). A lot of
answers come back at 0.9. Is 0.9 really 90%? The vendor of another tool told us their public
benchmark shows these models are well calibrated, so can we just trust the number and auto-file
everything at 0.9 and above?

```jsonl
{"id": "e07", "vakyn_pick": "software", "vakyn_confidence": 0.9, "label": "software"}
{"id": "e17", "vakyn_pick": "software", "vakyn_confidence": 1.0, "label": "software"}
{"id": "e22", "vakyn_pick": "software", "vakyn_confidence": 1.0, "label": "software"}
{"id": "e15", "vakyn_pick": "travel", "vakyn_confidence": 1.0, "label": "travel"}
{"id": "e02", "vakyn_pick": "software", "vakyn_confidence": 0.6, "label": "software"}
{"id": "e06", "vakyn_pick": "meals", "vakyn_confidence": 0.6, "label": "travel"}
{"id": "e20", "vakyn_pick": "travel", "vakyn_confidence": 1.0, "label": "travel"}
{"id": "e11", "vakyn_pick": "meals", "vakyn_confidence": 0.9, "label": "meals"}
{"id": "e10", "vakyn_pick": "travel", "vakyn_confidence": 0.9, "label": "travel"}
{"id": "e14", "vakyn_pick": "other", "vakyn_confidence": 0.9, "label": "office"}
{"id": "e24", "vakyn_pick": "other", "vakyn_confidence": 1.0, "label": "office"}
{"id": "e13", "vakyn_pick": "office", "vakyn_confidence": 0.9, "label": "software"}
{"id": "e04", "vakyn_pick": "other", "vakyn_confidence": 0.6, "label": "office"}
{"id": "e09", "vakyn_pick": "other", "vakyn_confidence": 0.9, "label": "other"}
{"id": "e21", "vakyn_pick": "meals", "vakyn_confidence": 1.0, "label": "meals"}
{"id": "e23", "vakyn_pick": "office", "vakyn_confidence": 1.0, "label": "office"}
{"id": "e01", "vakyn_pick": "meals", "vakyn_confidence": 0.6, "label": "meals"}
{"id": "e03", "vakyn_pick": "office", "vakyn_confidence": 0.6, "label": "office"}
{"id": "e16", "vakyn_pick": "meals", "vakyn_confidence": 1.0, "label": "meals"}
{"id": "e12", "vakyn_pick": "software", "vakyn_confidence": 0.9, "label": "office"}
{"id": "e05", "vakyn_pick": "travel", "vakyn_confidence": 0.6, "label": "meals"}
{"id": "e18", "vakyn_pick": "office", "vakyn_confidence": 1.0, "label": "office"}
{"id": "e19", "vakyn_pick": "other", "vakyn_confidence": 1.0, "label": "other"}
{"id": "e08", "vakyn_pick": "office", "vakyn_confidence": 0.9, "label": "office"}
```
