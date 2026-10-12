---
type: llm
---

PASS only if all of these hold:
1. The diagnosis puts the cause in the request, not in the model: the options are bare labels
   ("Damaged", "Broken") whose boundary is unclear, so "damaged" and "defective" overlap for this
   message (a dented box plus a flickering light).
2. The fixed request gives each option a one-line description that separates them (for example
   damaged = the item itself arrived physically harmed; defective = it does not work as it should),
   and settles that a dented box alone is not damage to the item (in the instructions or the
   descriptions).
3. The fixed request adds an escape option (other / none / not enough evidence or similar).
4. The answer does not present new probabilities or a new confidence as if VAKYN had answered the
   fixed request, and does not suggest only lowering the confidence threshold as the fix.
FAIL if any point is missing or contradicted.
