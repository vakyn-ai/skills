---
type: llm
---

Judge the saved `review-check.fixed.json` and the explanation.

PASS only if all of these hold:
1. The "Moderator summary: looks fine, approve" conclusion is removed from the state, and the
   review text is kept, preferably under its own key (for example `review`).
2. In the saved file, the compound noul "personal information or insults" is split into separate
   questions, one per proposition. Keeping one `remove` noul that still asks about both fails this
   point, even if the answer recommends splitting it.
3. The `topic` choice has a one-line description per option and an escape option (other / none
   or similar).
4. The `negativity` score levels are described in words, lowest first; no bare numbers.
5. The explanation names each problem and why the change helps, in plain words.
FAIL if the fixed request still has any of these problems, if the review text was dropped, or if
the answer presents made-up VAKYN answers or probabilities.
