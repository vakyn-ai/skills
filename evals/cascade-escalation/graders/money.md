---
type: llm
---

With the person's prices and the logged tokens (small 2,000 in / 150 out, big 2,000 in / 200 out):
small $0.00104 per request, big $0.0112 per request. Cascade about $8.51 per 1,000 requests,
always-big about $11.20, saving about $2.69 (24%). Break-even escalation rate about 91%
(1 − 0.00104 / 0.0112).

PASS if all hold:
1. It says the cascade still saves money, with figures that match the above within rounding
   (about $8.5 vs $11.2 per 1,000 requests, or about 24% saved).
2. It gives the break-even escalation rate (about 90–91%) or says plainly that 67% is under the
   point where the cascade stops saving.
3. It flags at least one limit: the always-big cost is estimated, VAKYN's own cost is not
   included, or 12 lines is a small sample.
Extra what-if figures (for example the cost at a lower escalation rate) are fine if labeled as such.
FAIL if a figure above is wrong beyond rounding or uses prices other than the ones given.
