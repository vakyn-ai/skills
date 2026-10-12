---
type: llm
---

Judge the meaning, not the exact words.

PASS if all of these hold:
1. The VAKYN side is a choice over the four teams plus an escape option (other / none), and the
   chat model is asked with the same options and the same ticket text (its current prompt may be
   an extra comparison).
2. It says, in any words, that the two agreeing does not show either is right, and it scores both
   against the `team` field where it exists.
3. The planned report covers disagreements side by side, the answers VAKYN is unsure about, time
   per call and the chat model's cost, and every answer is saved to a file.
4. It does not present VAKYN or OpenAI results as if a real run had produced them.
FAIL if any point is missing.
