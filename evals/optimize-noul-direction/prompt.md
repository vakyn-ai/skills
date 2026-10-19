---
tags: [optimize]
runs: 1
max_turns: 20
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We flag ironic tweets with a VAKYN noul and I'm running the optimize loop on 400 labeled tweets
(threshold 0.5). Here is the current request and the misses from `optimize.py start`. Write the
next candidate as ironic.v2.request.json in this folder and tell me what rule you added and why.

```json
{
  "model": "vakyn-fast",
  "state": {"tweet": "Love waiting 40 minutes for a bus. Great start to the day."},
  "questions": {
    "ironic": {"type": "noul", "instructions": "Is the tweet ironic?"}
  }
}
```

```text
Current wording on dev: accuracy 0.661 (185 of 280), average precision 0.702
Misses on dev, grouped by kind (write one rule per group, biggest first):
  false negative (said false, label true): 81
    t0112 (0.21): {"tweet": "So glad my phone died right before the meeting #not"}
    t0347 (0.33): {"tweet": "Monday again. My favourite. #sarcasm"}
    t0901 (0.28): {"tweet": "Oh good, another update that moves every button. Thanks so much."}
  false positive (said true, label false): 14
    t0420 (0.58): {"tweet": "Rain all week, perfect for finishing my book :)"}
    t0611 (0.55): {"tweet": "Can't believe how good this concert was!!!"}
    t0733 (0.61): {"tweet": "Of course I'll help you move, that's what friends are for"}
```
