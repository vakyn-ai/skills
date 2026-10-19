# The proposal

`vakyn-proposal.md`, in the person's project. Plain words, under **5,000 characters** (the contact
form's limit), one use case. The person reads it before anything is sent. Full sample:
[vakyn-proposal.sample.md](../examples/vakyn-proposal.sample.md).

## Template

```markdown
# Training request: <the decision, in a few words>

**From:** <company or "an individual developer">, <role of the person who owns the decision>
**Runs on:** VAKYN Cloud (<region>) | our own servers (<hardware>, <connected or not>)
**Model used so far:** vakyn-fast | vakyn-max

## The decision
<What is decided, by whom today, and what happens after. Two or three sentences.>

Question: `<name>` (<noul | choice | score>)
- `<option>`: <one line>
- ...

State: <fields and what they hold>. Language: <...>. Length: <...>.

Made-up examples (not real records):
- "<a short invented input>" → `<right answer>`
- ...

## Where VAKYN stands (measured on our labeled cases)
Source: <file names>. Wording tuned with the optimize loop: <yes, N rounds | no>.

| Set | Cases | Right | Accuracy |
|---|---|---|---|
| Reserved, before tuning | ... | ... | ... |
| Reserved, after tuning | ... | ... | ... |

Still wrong or unsure, after tuning:
- <option pair or slice>: <count> of <count> (<what these cases have in common>)
- ...

## What we need
- Target: <accuracy, or share sent to a person>
- Volume: <per day or month>; answer within <time>
- Value: <what a right answer saves, or a wrong one costs>
- Constraints: <personal data, GDPR / HIPAA, region, no connection out>

## What we can share
<N> labeled cases, labeled by <who>, shareable <under a DPA | only as made-up look-alikes>.
Option counts: <option>: <n>, ...

## Contact
<name, email> (filled in by the person)
```

## Writing it

- **Lead with the losing cells.** The loop trains "exactly there": the more precisely the proposal
  names where VAKYN misses (which options it mixes up, which kind of document), the more useful it
  is. Counts beat adjectives.
- **Made-up examples only.** Write three to five short inputs that show the pattern of the losing
  cells, invented for the proposal. Never copy a record, even shortened. Say they are made up.
- **Every number has a source.** Name the file. Accuracy from reserved or held-out cases, never
  from the dev set alone. No numbers: write "not measured yet" and leave the table out.
- **No promises asked for or made.** Do not ask VAKYN for a guaranteed accuracy, and do not write
  what training will achieve.
- **Short.** Under 5,000 characters; check with `wc -c vakyn-proposal.md`. Cut examples first,
  then losing cells beyond the top five.

## Privacy

What leaves the machine is what the person pastes or attaches, and nothing else. Before they send:

1. Read the proposal with them, line by line.
2. Point out what may be sensitive: customer or product names, internal team names, volumes,
   revenue, the name of a system. Offer a neutral word for each ("a retailer", "our CRM").
3. Confirm the examples are invented, not shortened real records.
4. Personal or health data in their flow: say that the labeled cases are shared only after VAKYN
   replies and the terms are agreed (a DPA for GDPR, a BAA for HIPAA), never in this message.
