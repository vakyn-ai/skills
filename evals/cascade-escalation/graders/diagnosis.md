---
type: llm
---

Facts from the log: 12 cascade lines; 4 accepted, 8 escalated (67%): 7 `unsupported` at high
VAKYN confidence (0.92–0.99) and 1 `off_topic`. Each escalated `unsupported` draft adds a specific
time, number or promise (within 24 hours, within 2 hours, 30% off, within 15 minutes, 3 business
days, by 6 am, within 48 hours); the big model's answers then passed the check.

PASS if all hold:
1. It gives the escalation rate as 8 of 12 (67%, two thirds) and says most escalations are
   `unsupported` (7) with one `off_topic`.
2. It names the likely cause as the small model adding details (times, numbers, promises) the
   sources do not back, and notes VAKYN was confident on these (not borderline).
3. Its fix is on the small model's side (a stricter prompt, a stronger small model) and/or
   checking drafts against the sources; it does not advise lowering the threshold to cut
   escalations (saying not to lower it is fine).
FAIL if any of these is missing or wrong.
