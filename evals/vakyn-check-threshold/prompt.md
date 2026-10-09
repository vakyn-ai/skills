---
tags: [vakyn-check]
runs: 1
max_turns: 15
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We use a VAKYN noul to flag customer messages that threaten legal action ("Does state.message
threaten legal action against us?"). Flagged and cleared messages are handled automatically; the
rest go to a person. I ran 60 past messages through VAKYN and our legal team labeled them (label =
true means it really is a legal threat). We can live with at most 2% wrong among the messages we
handle automatically. Where should we set the threshold, and how much goes to a person?

```jsonl
{"id": "m01", "noul": 0.05, "label": false}
{"id": "m02", "noul": 0.03, "label": false}
{"id": "m03", "noul": 0.01, "label": false}
{"id": "m04", "noul": 0.0, "label": false}
{"id": "m05", "noul": 0.15, "label": true}
{"id": "m06", "noul": 0.0, "label": false}
{"id": "m07", "noul": 0.99, "label": true}
{"id": "m08", "noul": 0.01, "label": false}
{"id": "m09", "noul": 0.99, "label": true}
{"id": "m10", "noul": 0.65, "label": true}
{"id": "m11", "noul": 0.99, "label": true}
{"id": "m12", "noul": 0.98, "label": true}
{"id": "m13", "noul": 0.97, "label": true}
{"id": "m14", "noul": 0.5, "label": false}
{"id": "m15", "noul": 0.04, "label": false}
{"id": "m16", "noul": 0.95, "label": true}
{"id": "m17", "noul": 0.01, "label": false}
{"id": "m18", "noul": 0.04, "label": false}
{"id": "m19", "noul": 0.02, "label": false}
{"id": "m20", "noul": 0.97, "label": true}
{"id": "m21", "noul": 0.8, "label": false}
{"id": "m22", "noul": 0.04, "label": false}
{"id": "m23", "noul": 0.07, "label": false}
{"id": "m24", "noul": 0.12, "label": false}
{"id": "m25", "noul": 0.03, "label": false}
{"id": "m26", "noul": 0.02, "label": false}
{"id": "m27", "noul": 0.35, "label": true}
{"id": "m28", "noul": 0.98, "label": true}
{"id": "m29", "noul": 0.01, "label": false}
{"id": "m30", "noul": 0.88, "label": true}
{"id": "m31", "noul": 0.95, "label": true}
{"id": "m32", "noul": 0.45, "label": true}
{"id": "m33", "noul": 0.55, "label": true}
{"id": "m34", "noul": 0.03, "label": false}
{"id": "m35", "noul": 0.02, "label": false}
{"id": "m36", "noul": 0.4, "label": false}
{"id": "m37", "noul": 0.75, "label": true}
{"id": "m38", "noul": 0.96, "label": true}
{"id": "m39", "noul": 0.02, "label": false}
{"id": "m40", "noul": 0.85, "label": true}
{"id": "m41", "noul": 0.7, "label": false}
{"id": "m42", "noul": 0.1, "label": true}
{"id": "m43", "noul": 0.6, "label": false}
{"id": "m44", "noul": 0.98, "label": true}
{"id": "m45", "noul": 0.01, "label": false}
{"id": "m46", "noul": 0.01, "label": false}
{"id": "m47", "noul": 0.0, "label": false}
{"id": "m48", "noul": 0.3, "label": false}
{"id": "m49", "noul": 0.99, "label": true}
{"id": "m50", "noul": 0.2, "label": false}
{"id": "m51", "noul": 0.96, "label": true}
{"id": "m52", "noul": 0.08, "label": false}
{"id": "m53", "noul": 0.9, "label": false}
{"id": "m54", "noul": 0.05, "label": false}
{"id": "m55", "noul": 0.03, "label": false}
{"id": "m56", "noul": 0.01, "label": false}
{"id": "m57", "noul": 0.97, "label": true}
{"id": "m58", "noul": 0.0, "label": false}
{"id": "m59", "noul": 0.02, "label": false}
{"id": "m60", "noul": 0.02, "label": false}
```
