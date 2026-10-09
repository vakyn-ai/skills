---
type: llm
---

Facts of the data: 60 labeled records. Treating noul ≥ 0.5 as yes, 9 are wrong. Every wrong answer
has noul between 0.1 and 0.9 (distance from 0.5 at most 0.8 on the 0–1 confidence scale
abs(2*noul-1)). All 40 records with noul ≥ 0.95 or ≤ 0.05 are right; the records at 0.07, 0.08 and
0.88 are right too. So a cut-off that acts on yes at noul ≥ about 0.93–0.95 and on no at noul ≤
about 0.05–0.08 (or confidence ≥ about 0.85–0.9) has no errors and handles roughly 40–43 of 60
(about 65–72%); the rest (about 30–35%) go to a person.

PASS only if all of these hold:
1. It uses the distance from 0.5 (or separate yes and no cut-offs), not a single cut on noul
   alone such as "noul > 0.9 means flag" with everything else treated as cleared.
2. The recommended cut-off is in the range above (errors at noul 0.9 and 0.1 are excluded), with
   the share handled automatically and the share sent to a person, roughly matching the facts.
3. It shows a small table or list of candidate thresholds with coverage and error rate.
4. It checks the chosen threshold on held-out labels, or says the labels should be split to check it.
5. It says that about 40 automatically handled records with no errors cannot prove a 2% error rate
   (the true rate could be several percent; roughly 150 or more answered records without an error are
   needed), and asks for more labels before relying on it.
FAIL if any point is missing, if it recommends 0.5 or a feeling-based number, or if it invents
records or VAKYN answers.
