---
tags: [optimize]
runs: 1
max_turns: 15
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Skill]
---

I want to use the VAKYN optimize skill to tune our support router question (options billing,
account, shipping, other). These are all the labeled tickets we have. Is this enough to start? If
not, tell me what to label next. Don't run anything yet.

```jsonl
{"id": "r001", "text": "Charged twice for May.", "label": "billing"}
{"id": "r002", "text": "Need a VAT invoice for order 512.", "label": "billing"}
{"id": "r003", "text": "Refund for the cancelled order please.", "label": "billing"}
{"id": "r004", "text": "My card payment failed, how do I pay?", "label": "billing"}
{"id": "r005", "text": "Why did my price go up?", "label": "billing"}
{"id": "r006", "text": "Invoice has the wrong company name.", "label": "billing"}
{"id": "r007", "text": "I was billed after cancelling.", "label": "billing"}
{"id": "r008", "text": "Can I pay by bank transfer?", "label": "billing"}
{"id": "r009", "text": "Discount code wasn't applied to my bill.", "label": "billing"}
{"id": "r010", "text": "Remove my old card from the account payments.", "label": "billing"}
{"id": "r011", "text": "Where is my refund from last week?", "label": "billing"}
{"id": "r012", "text": "Yearly plan charged at the monthly price.", "label": "billing"}
{"id": "r013", "text": "Can't log in.", "label": "account"}
{"id": "r014", "text": "Reset my password please.", "label": "account"}
{"id": "r015", "text": "Change my email address.", "label": "account"}
{"id": "r016", "text": "Two-factor code never arrives.", "label": "account"}
{"id": "r017", "text": "Delete my account.", "label": "account"}
{"id": "r018", "text": "Add a team member.", "label": "account"}
{"id": "r019", "text": "Locked out after too many tries.", "label": "account"}
{"id": "r020", "text": "Change my username.", "label": "account"}
{"id": "r021", "text": "How do I turn on 2FA?", "label": "account"}
{"id": "r022", "text": "Profile picture won't upload.", "label": "account"}
{"id": "r023", "text": "Where is my parcel?", "label": "shipping"}
{"id": "r024", "text": "Tracking hasn't moved in 5 days.", "label": "shipping"}
{"id": "r025", "text": "Parcel arrived damaged.", "label": "shipping"}
{"id": "r026", "text": "Wrong item delivered.", "label": "shipping"}
{"id": "r027", "text": "Can I change the delivery address?", "label": "shipping"}
{"id": "r028", "text": "Courier left it at the wrong house.", "label": "shipping"}
{"id": "r029", "text": "Are you hiring?", "label": "other"}
{"id": "r030", "text": "Who do I talk to about a partnership?", "label": "other"}
```
