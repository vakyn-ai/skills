# Training request: routing bank support messages to the right team

<!-- Sample for the train-request skill. Results come from the optimize sample files; the bank, volumes and counts under "What we need" and "What we can share" are made up. -->

**From:** a retail bank (sample), head of customer support operations
**Runs on:** VAKYN Cloud (EU)
**Model used so far:** vakyn-fast

## The decision
Every message from a customer goes to one of five teams, or to a general queue. Today a person reads
each one; with VAKYN the message is routed when confidence is 0.8 or more, and goes to a person
below that.

Question: `intent` (choice)
- `CRD`: the card itself: lost, stolen, blocked, declined, replaced, PIN
- `DSP`: a payment the customer wants reversed or questions
- `TRF`: sending or receiving money, payees, account numbers
- `FEE`: what the bank charges and why
- `ACC`: signing in, app problems, personal details
- `OTH`: anything else

State: `message`, the customer's message. Language: English. Length: one to three sentences.

Made-up examples (not real records):
- "My card was used in two shops abroad but it is still in my pocket." → `DSP`
- "What do you charge to send a new card by courier?" → `FEE`
- "The card reader says my card is not valid since this morning." → `CRD`

## Where VAKYN stands (measured on our labeled cases)
Source: `optimize-run/report.md`, `cases.sample.jsonl` (64 labeled messages, 44 dev, 20 reserved).
Wording tuned with the optimize loop: yes, 1 round (every option described).

| Set | Cases | Right | Accuracy |
|---|---|---|---|
| Reserved, before tuning | 20 | 13 | 0.650 |
| Reserved, after tuning | 20 | 17 | 0.850 |

Still wrong after tuning (dev set):
- `DSP -> CRD`: 1 (a card-detail fraud where the customer still has the card)
- `FEE -> CRD`: 1 (a question about the price of a card service)

The card is mentioned in both: when a message names the card and a payment or a price, VAKYN leans to
`CRD`.

## What we need
- Target: 95% right among messages routed automatically, with at most 20% sent to a person
- Volume: about 4,000 messages a day, peaks of 600 an hour; answer within 2 seconds
- Value: a wrongly routed fraud report waits a day in the wrong queue
- Constraints: messages hold personal data (GDPR); processing in the EU

## What we can share
About 2,000 labeled messages, labeled by our support team leads, shareable under a DPA.
Option counts: CRD 410, DSP 380, TRF 520, FEE 230, ACC 300, OTH 160.

## Contact
(name, email: filled in before sending)
