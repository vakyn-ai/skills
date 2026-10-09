---
tags: [vakyn-questions]
runs: 1
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Write, Glob, Grep, Skill]
---

Before a forum post goes live we ask VAKYN one question about it:

```json
{"type": "noul",
 "instructions": "Does this post contain a phone number or a home address, or a link to a site selling something, and was it written by an account that is less than a week old?"}
```

The answers hover around 0.5 and we can't act on them. Help me fix this. The post text and the
account's creation date are both in our database. Write the new request for this sample post and
save it as `post-check.json` in this folder:

"Selling my old road bike, barely used, great price. Message me at 555-0199 or see more photos at
bikedeals-now.example/rb22. Pickup only."
