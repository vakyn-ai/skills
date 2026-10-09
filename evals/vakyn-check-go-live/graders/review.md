---
type: llm
---

The code has these problems: (a) the API key is written in the code; (b) `timeout=None`, so a call
can hang forever; (c) no handling of 429 (full queue, `retry-after`) or other errors: `r.json()` is
read without checking the status; (d) three independent questions about the same ticket are sent as
three requests instead of one; (e) `asyncio.gather` over every ticket has no cap on concurrent calls,
while the server queues 32 requests by default (`--max-queue`) shared by both app servers; (f) no
fallback when the server is down; (g) no logging of request ids, answers, confidence or model name;
(h) the 0.5 thresholds are guesses, not set from labeled examples; (i) plain HTTP to another machine
(10.0.4.12).

PASS only if the review covers (a) with advice to move the key to an environment variable or secret
store AND to revoke and replace it (it was in code), plus at least six of (b)–(i), each with a
concrete fix. FAIL if it misses (a), (b), (c) or (d), or if it suggests raising `--max-queue` or
retrying in a tight loop as the only answer to load.
