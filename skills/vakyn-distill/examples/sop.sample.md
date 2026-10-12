# Supplier onboarding review (sample procedure)

Synthetic procedure for the `vakyn-distill` examples. An agent follows it today for every email
that reaches the supplier inbox. Version `sop-2026-09`.

## 1. Intake

Read the email. Continue only if it is an application from a new supplier. Close the case as
`not_an_application` when it is a sales pitch, an invoice or payment question, or a change request
from a supplier already on file (forward those to the supplier desk).

## 2. Required documents

The supplier portal lists what was uploaded, one slot per document, with its issue date.

- Every supplier: registration certificate, tax certificate issued in the last 12 months, bank
  letter on the bank's letterhead.
- Services and logistics suppliers: an insurance certificate that has not expired.
- Suppliers that will handle personal data of our staff or customers: a signed data processing
  agreement.

A document that is out of date counts as missing. Any missing document: outcome
`request_documents`, listing what is missing.

## 3. Category and terms

From the application text, set the category: `goods` (physical products), `services` (work done
on our sites or for our staff), `software` (licenses, hosted tools, data services) or `logistics`
(transport, storage, customs). Note whether the supplier will handle personal data.

Standard payment terms are 30 or 45 days after invoice. Shorter terms, payment before delivery,
deposits, or an early-payment discount need finance approval: outcome `escalate_finance`.

## 4. Watch-list screening

The screening tool returns possible matches by name. Most are other companies with similar names.
For each match, decide whether it could be the applicant: a similar name **and** at least one of the
same country, the same address or street, or a person who appears in both. Names are similar when
they share their main distinctive word, whatever the legal form (Ltd, GmbH, SRL) and the other words.

For every match that could be the applicant, pull the company registry record and compare the
registration number, the registered address and the directors. If one match is the applicant,
stop: outcome `escalate_compliance`. Never approve a supplier with an open match. If you cannot
tell, the outcome is `escalate_compliance` too.

## 5. Bank account

The bank letter's country must be the registered country. Any other country: outcome
`escalate_compliance`.

## 6. Outcome

Use the first that applies: `not_an_application`, `escalate_compliance`, `request_documents`,
`escalate_finance`, `approve`. Record the category, the personal-data answer, the payment-terms
answer, the matched screening entry (or none) and the missing documents.
