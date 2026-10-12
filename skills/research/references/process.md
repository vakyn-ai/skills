# Research a process described in words

Use when there is no code: the person describes how work flows today ("our team reads every email
and forwards it"). The analysis is the same; the locations are process steps instead of
`file:line`.

## 1. Write the steps down

Turn the description into numbered steps. For each step note:

- **Who or what does it** today: a person, a script, a chat model, a form.
- **Input**: what they look at (an email, a form, a photo, a record in a system).
- **Output**: a pick from a set, a yes/no, a level, a number, a lookup result, or written text.
- **How often**: per day or per week. Take it from the description; if missing, assume and say so.
- **What happens next** with the output (this sets the risk).

Number the steps as written ("Step 1: read the email"). Use those numbers as the "Where" column.

## 2. Sort each step

Apply [fit-check.md](../../start/references/fit-check.md) to each step:

| The step | Mark |
|---|---|
| picks one of a known set, gives yes/no, or a level, by reading the input | **spot** with its question type |
| writes a letter, reply, summary, note | **keep** (a person or a chat model writes it) |
| looks something up in a system, checks a date, adds up amounts | **does not fit**: code or the system does it, and the result can go into VAKYN's state |
| needs a photo, a phone call, or a document too long to read in one go | **does not fit**, with the reason |

People often bundle several judgments into one step ("reads the claim and decides what to do").
Split it into the separate judgments and list each.

## 3. Rate and rank

Use [ranking.md](ranking.md). For a process:

- **Gain** is the person time spent today (minutes per item × items a day) plus wait time for the
  customer. Say which numbers came from the description and which you assumed.
- **Effort** is usually Large for the first spot (nothing is built yet) and Medium for the next
  ones that reuse the same input. Next skill is `workflow`.
- **Risk**: the same scale. For high-risk steps, propose VAKYN as a first pass with a person
  checking unsure answers, not as a replacement.

Do not stop to ask questions before writing the report. Make reasonable assumptions, write them
under "Assumptions and open questions", and offer to update the report once the person answers.
