---
tags: [optimize]
runs: 1
max_turns: 20
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

I'm tuning the wording of our VAKYN routing question with the optimize loop. Here is the request
(intent.v1.request.json), and the misses `optimize.py start` printed on the dev set. Our code
branches on the codes CRD, DSP, TRF, FEE, ACC and OTH. Write the next candidate for round 1 and
save it as intent.v2.request.json in this folder, and tell me the --rule lines to pass to `try`.

```json
{
  "model": "vakyn-fast",
  "state": {"message": "I lost my debit card on the train this morning. Please block it."},
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "Which code fits the customer's message?",
      "criteria": {"CRD": "CRD", "DSP": "DSP", "TRF": "TRF", "FEE": "FEE", "ACC": "ACC", "OTH": "OTH"}
    }
  }
}
```

```text
Current wording on dev: accuracy 0.523 (23 of 44)
Misses on dev, grouped by kind (write one rule per group, biggest first):
  FEE -> DSP: 5
    c035 (0.62): {"message": "Why was I charged 5 for using a cash machine abroad?"}
    c039 (0.55): {"message": "I was charged an overdraft fee even though I was only overdrawn for one day. Is that right?"}
    c042 (0.48): {"message": "Your app says no fees but I got charged 2.50 for a transfer. Why?"}
  ACC -> OTH: 4
    c047 (0.51): {"message": "How do I change the email address on my account?"}
    c051 (0.44): {"message": "How do I change my address? I moved house last week."}
    c053 (0.40): {"message": "The app keeps crashing when I open the statements page."}
  TRF -> OTH: 4
    c028 (0.47): {"message": "What's the most I can send in one transfer per day?"}
    c031 (0.52): {"message": "How do I add a new payee so I can send money to my sister?"}
    c034 (0.49): {"message": "I need the IBAN and SWIFT code so my client can pay me from abroad."}
  CRD -> DSP: 3
    c003 (0.58): {"message": "The card machine keeps saying my card is declined, but I have money in the account."}
    c008 (0.46): {"message": "My card expires next month and the new one hasn't come yet."}
    c010 (0.50): {"message": "I want to order a second card for my partner on the same account."}
  DSP -> CRD: 3
    c019 (0.61): {"message": "My card is still in my wallet but there are three payments in another country I didn't make."}
    c021 (0.57): {"message": "Someone used my card details online last night. I still have the card. What do I do about the payments?"}
    c013 (0.45): {"message": "I was charged twice for the same hotel booking. One of them should be returned."}
```
