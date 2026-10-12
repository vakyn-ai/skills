---
tags: [research]
runs: 1
max_turns: 20
timeout_seconds: 600
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We don't have any software for this yet, just people. Our insurance claims team gets about 400
claim emails a day. For each one, someone reads it and decides what kind of claim it is (car, home,
travel or health). Then they check whether all the required documents are attached. They look up
the customer's policy in our policy system to see if it was active on the date of the incident.
They decide whether the claim looks suspicious enough to send to the fraud team. Finally they write
a letter to the customer saying what happens next. Where would VAKYN fit in this? Put the result in
a report file in this folder.
