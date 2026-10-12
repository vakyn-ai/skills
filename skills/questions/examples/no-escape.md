# No escape option

[Weak](no-escape.weak.json) → [fixed](no-escape.request.json)

A partnership pitch arrives through the support form. The request asks "Which team?" with three
teams and one-word descriptions.

**Weak answer:** `product` at confidence 0.95 (billing 0.01, access 0.03, product 0.97).

**What was wrong**

- No escape option. The message is not a support request, but VAKYN had to pick one of three
  teams. It picked the closest one, and picked it with high confidence.
- Labels instead of descriptions. `"product": "Product"` says nothing about what belongs there.
- The question did not name its subject, and the state was a bare string.

**Fix**

- Added `other`, described as "anything that is not a support request for these teams: sales,
  partnerships, press, job applications, spam".
- Gave each team a one-line description of what it handles.
- Put the text under `state.message` and asked "Which support team should handle state.message?".

**Fixed answer:** `other` at confidence 1.00.

**Takeaway:** confidence 0.95 on the weak request was not a sign the answer was right. Fix the
options before you trust or threshold confidence. Route `other` to a person in code.
