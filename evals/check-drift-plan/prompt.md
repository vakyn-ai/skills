---
tags: [check]
runs: 1
max_turns: 20
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We upgraded the model file on our VAKYN test server last night: the new build is a smaller
quantization to save memory. Production still runs the old file. Our app asks three questions per
support ticket (team, urgency, wants_refund) and acts on its own at confidence 0.8 and above. Our
developers also reword those questions in pull requests now and then, and nobody checks what that
does. How do we make sure the upgrade, and future question edits, don't silently change the
answers? We use GitHub Actions. Give me the plan, and save the CI workflow as `vakyn-drift.yml`
in this folder. Our test server is at http://vakyn-test.internal:8080.
