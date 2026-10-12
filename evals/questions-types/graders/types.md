---
type: llm
---

PASS only if all of these hold:
1. Role fit is a `choice` over the four roles that also has an escape option (for example none,
   other, no_fit or not_enough_evidence).
2. "More than 5 years of experience" is computed in code from the job dates (sum and compare), not
   asked as a VAKYN question.
3. Cover letter quality is a `score` with levels described in words, lowest first (a sketch of
   the levels is enough).
4. "Mentions salary and relocation" is split into two separate `noul` questions (combined in code
   if needed), not one noul.
5. The rejection email is not a VAKYN question: it stays with a chat model or a person (VAKYN's
   answers may feed it).
FAIL if any point is missing or contradicted, for example a single noul for salary and relocation,
a VAKYN question for the 5-year threshold, a choice without an escape option, or VAKYN writing the
email. The "has work permit" field needs no question; mentioning that is fine but not required.
