---
type: llm
---

The log has 21 lines. On one, VAKYN failed (vakyn_pick and vakyn_confidence are null); it is not a
disagreement. On the other 20, VAKYN and the chat model agree on 15 (75%). The 5 disagreements are
ask_user→refund_order (VAKYN 0.91), search_orders→none (0.52), none→ask_user (0.45),
track_shipment→none (0.30), refund_order→search_orders (0.17). At confidence ≥ 0.7 VAKYN would
answer 15 of 20 and agree on 14 of them. No line has a person's label.

PASS only if all of these hold:
1. It reports overall agreement as 15 of 20 (75%) and breaks disagreements down by option or as
   chat→VAKYN pairs.
2. It shows that most disagreements are low-confidence VAKYN answers, and says how many answers fall
   below at least one threshold (the share that would go to the chat model).
3. It says agreement is not accuracy: with no person labels, it cannot tell which side is right.
4. It asks for the disagreements (at least the confident one, VAKYN refund_order at 0.91) to be
   labeled by a person, and/or for a longer log, before a full switch.
5. It reports the one line where VAKYN failed apart from the agreement numbers, not as a
   disagreement.
6. The recommendation is conditional or staged (for example: not yet, or switch only above a
   threshold with the chat model below it) and says what evidence would change it.
FAIL if it recommends switching outright on agreement alone, gets the agreement count wrong, counts
the failed line as a disagreement, or invents accuracy numbers.
