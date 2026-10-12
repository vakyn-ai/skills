# Rules in code, options by name

[Weak](rules-in-code.weak.json) → [fixed](rules-in-code.request.json)

A customer wants a quiet kettle, under $50 including $6 shipping, delivered by Friday 17 October.
The weak request puts all four products in one string and asks "Answer option 1, 2, 3 or 4".

**Weak answer:** `option_1` (Hushpot) at confidence 0.99. Hushpot costs $46 + $6 = $52, over
budget.

**What was wrong**

- Arithmetic and dates in the question. Price plus shipping and "arrives by Friday" are exact
  rules; VAKYN went for the quietest product and missed the sum.
- Options by position. `option_1`: "first product" means nothing on its own, and the model has to
  count through the string to match it.
- No escape option, so "nothing fits" could not be said.

**Fix**

- Code checks budget and delivery first: Hushpot (over budget) and Steelbrew (arrives 24 October)
  are dropped. Only Calmkettle and Rapidboil Pro reach VAKYN.
- The judgment left is "which is quiet", so the state holds the request and the remaining
  candidates, named by product id with a short description.
- Added `no_match`.

**Fixed answer:** `calmkettle_17` at confidence 1.00. With only Rapidboil Pro left as a candidate,
the same request answers `no_match` (0.97), so the escape option works.

**Takeaway:** code does what must be exact; VAKYN judges what needs reading. Name options by the
item's id, never by position.
