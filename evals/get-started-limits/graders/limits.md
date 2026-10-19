---
type: llm
---

PASS if the answer states that a choice takes at most 255 options, so 400 categories need two steps
(for example pick a category group first, then a category within it) or code narrowing the list
first, and that the state plus the longest question must stay under 32,768 tokens (65,536 for state
plus all questions), and that a request over a limit is refused with 400 rather than cut. FAIL if any
limit is wrong or it claims the server truncates.
