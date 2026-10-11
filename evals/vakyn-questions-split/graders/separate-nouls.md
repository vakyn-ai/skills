---
type: llm
focus:
  source: file
  path: "post-check.json"
---

Judge only this one point; ignore everything else.
PASS if post-check.json asks about contact details (phone number, home address) and about a link to a selling site in separate `noul` questions. Contact details may be one noul or one per kind. FAIL if any noul joins the contact part with the selling-link part or with the account age.
