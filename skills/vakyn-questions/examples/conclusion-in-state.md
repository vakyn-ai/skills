# Conclusion in the state

[Weak](conclusion-in-state.weak.json) → [fixed](conclusion-in-state.request.json)

A customer is comparing other tools, mentions the renewal date and asks how to export all their
data. The state also carries a CRM note: "Account health: Green. Customer is happy, no action
needed." The question rates churn risk on levels `"1"` to `"5"`.

**Weak answer:** `score` 2.38, confidence 0.39, probability spread over three levels (0.17 / 0.28 /
0.48).

**What was wrong**

- A conclusion in the state. The health note is someone's earlier verdict, and it contradicts the
  email. VAKYN weighs both, so the answer is pulled toward "happy".
- Bare numbers as levels. `"4"` gives the model nothing to compare the email against.
- The question did not say whose churn risk or over what time.

**Fix**

- Removed the health note. Added evidence instead: the plan and the open export ticket.
- Wrote five levels in words, lowest first, each describing what you would see ("compares other
  tools and asks to export data or cancel").
- Asked "How likely is the customer in state.latest_email to leave at renewal?".

**Fixed answer:** `score` 2.97, confidence 0.97, with 0.97 on level 3, "Preparing to leave".

**Takeaway:** give VAKYN the evidence, not someone's summary of it, and describe each level.
