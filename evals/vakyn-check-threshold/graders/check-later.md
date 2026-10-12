---
type: llm
---

Judge only this one point; ignore everything else in the answer.
Facts of the data: 60 labeled records. Every wrong answer at a 0.5 cut has noul between 0.1 and 0.9. All records with noul at or above 0.95, or at or below 0.08, are right. Cut-offs that flag at about 0.91–0.95 and clear at about 0.05–0.09 have no errors and handle about 40–42 of 60 (65–70%); about 30–35% go to a person.

PASS if it checks the chosen cut-offs on held-out labels, or says the labels should be split to check them, or says they must be checked on a fresh labeled batch before going live. FAIL otherwise.
