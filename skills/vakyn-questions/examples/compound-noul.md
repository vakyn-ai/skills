# Compound noul

[Weak](compound-noul.weak.json) → [fixed](compound-noul.request.json)

A polite customer asks for their money back because a blender came in the wrong color. The
request asks one `noul`: "Is the customer angry and asking for a refund?"

**Weak answer:** `noul` 0.37. Unsure, and no way to tell which half is true.

**What was wrong**

- Two propositions in one `noul`. The message clearly asks for a refund and is clearly not angry,
  so "angry and refund" is false, but the strong "refund" pulls it up and the answer lands in the
  unsure middle. Your code learns nothing it can act on.

**Fix**

- Split into two nouls, `angry` and `refund`, in the same request (they are independent).
- Added `true` / `false` descriptions where the line is a policy: a replacement or store credit is
  not a refund; a report of a problem is not anger.
- Put the text under `state.message` and named it in both questions.

**Fixed answer:** `angry` 0.00, `refund` 1.00.

**Takeaway:** combine facts in code (`angry > 0.8 and refund > 0.8`), not inside one question.
Code combines exactly; one compound question gives a blurred number.
