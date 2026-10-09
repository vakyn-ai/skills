---
tags: [vakyn-check]
runs: 1
max_turns: 20
timeout_seconds: 420
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

We route support tickets with OpenAI today (gpt-4o-mini, key in OPENAI_API_KEY) and want to see if
VAKYN on our own server can do it. Our project is Python. Set up a test that compares the two on our
tickets and tell me what you need from me. Write the script into this folder and save the VAKYN
request it uses as a JSON file here.

Our current prompt:

> You are a support router. Read the ticket and answer with one word: billing, access, shipping or
> product.

Our tickets are in `tickets.jsonl` (4,000 lines, not in this folder yet), this format:

```jsonl
{"id": "T-1001", "from": "maria.lopez@example.com", "body": "Hi, this is Maria Lopez (+44 7700 900123). I was charged twice for order 5521."}
{"id": "T-1002", "from": "j.chen@example.com", "body": "I can't log in since the password reset, the code never arrives."}
{"id": "T-1003", "from": "sam.r@example.com", "body": "Parcel says delivered but nothing at 14 Elm Road. Sam Reed"}
{"id": "T-1004", "from": "ana@example.com", "body": "The kettle stopped heating after three days."}
{"id": "T-1005", "from": "press@example.org", "body": "I'm writing an article about online shops, can I interview your founder?"}
{"id": "T-1006", "from": "li.wei@example.com", "body": "The order never arrived so I want my money back."}
```

Some tickets also have a `team` field: the team that finally handled it.
