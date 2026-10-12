---
type: llm
---

Judge only this one point; ignore everything else in the answer.
Facts of the data: 24 labeled records. Confidence 0.6 on 6 records (3 right), 0.9 on 8 records (5 right), 1.0 on 10 records (9 right). 17 of 24 right. Every group is right less often than its confidence on this sample, but each group has 10 records or fewer.

PASS if it says these 24 records (or groups of 6 to 10) are too few to settle calibration and asks for more labeled records before relying on it. FAIL otherwise.
