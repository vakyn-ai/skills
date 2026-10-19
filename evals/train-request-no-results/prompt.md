---
tags: [train-request]
runs: 1
max_turns: 15
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We want VAKYN trained on our insurance claim triage (a choice between fast_track, standard,
investigate and reject). We wrote the question last week and tried it on a few claims; it seemed
fine but sometimes picks standard for claims our adjusters would investigate. We haven't labeled
anything or measured it yet. Can you write the training request to VAKYN for us?
