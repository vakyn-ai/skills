---
type: llm
---

Facts of the data: 24 labeled records. Confidence is exactly 0.6 on 6 records (3 right, 50%),
0.9 on 8 records (5 right, about 62%), 1.0 on 10 records (9 right, 90%). 17 of 24 right overall.
On this sample every group is right less often than its confidence says (too sure), most at 0.9,
but each group has 10 records or fewer, so the observed shares are very uncertain (for 5 of 8 the
true share could be anywhere from roughly 30% to 85%).

PASS only if all of these hold:
1. It shows the records grouped by confidence with, per group, the count and the observed share
   right (or right/total), matching the facts above (small rounding is fine), and compares that with
   the stated confidence (a gap, or "too sure").
2. It says 24 records (or groups of 6 to 10) are too few to judge calibration or to prove anything
   about 0.9, and asks for more labeled records (about 50 or more to start, more per group) before
   relying on it.
3. It does not accept the public benchmark as evidence: calibration has to be checked on their own
   labeled records.
4. It does not recommend auto-filing everything at 0.9 and above on this evidence (it may suggest
   a higher threshold or keeping review on until more labels exist).
FAIL if any point is missing, if it claims VAKYN is well calibrated (or badly calibrated, as a
settled fact) from these records, or if it invents records or numbers that are not in the data.
