---
type: llm
---

PASS only if all of these hold:
1. The compound question is split: the contact-details part (phone number, home address) and the
   selling-link part are separate `noul` questions. Contact details may be one noul ("personal
   contact details such as a phone number or home address") or one noul each.
2. The account-age check ("less than a week old") is done in code from the creation date, not
   asked of VAKYN.
3. The post text is in the state under its own key (for example `post`), and the questions name it.
4. The answer says the parts are combined in code (for example hold the post if any check is
   likely and the account is new), not inside one question.
FAIL if any noul in the saved request still joins the contact part with the selling-link part or the account age, if VAKYN is asked
about the account age, or if the answer presents made-up VAKYN probabilities as results.
