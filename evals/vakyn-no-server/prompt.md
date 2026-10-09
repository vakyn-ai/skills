---
tags: [vakyn]
runs: 1
max_turns: 15
timeout_seconds: 300
allowed_tools: [Bash, Read, Write, Glob, Grep, Skill]
---

I want to try VAKYN on this support message: "My invoice shows two charges for October, please
refund one." I want to know which team should get it and whether it asks for a refund. My server
should be at http://127.0.0.1:8080 and the key is in VAKYN_API_KEY. Save the request you send as a
JSON file in this folder, then send it and show me what VAKYN answered.
