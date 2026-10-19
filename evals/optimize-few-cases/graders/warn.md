---
type: llm
---

Judge only this one point; ignore everything else in the answer.
Facts: 30 labeled cases (billing 12, account 10, shipping 6, other 2). The skill asks for at least
about 50 labeled cases.

PASS if the answer warns that 30 is too few for a reliable result (for example that a gain of one or
two cases would be noise, or the reserved set would be tiny) and proposes labeling about 20 or more
additional cases (to reach about 50 or more). FAIL if it says 30 is enough, or gives no number.
