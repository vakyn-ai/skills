---
type: llm
---

Judge only this one point; ignore everything else in the answer.
Facts: the option `other` has only 2 labeled cases (fewer than about 5).

PASS if the answer points out that `other` has too few cases (only 2) and asks for more of them
(at least about 3 more, or a number that brings it to 5 or more). FAIL if it does not mention the
`other` option's low count.
