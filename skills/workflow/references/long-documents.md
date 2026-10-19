# Long documents

The state plus the longest question must stay under 32,768 tokens (about 4 characters per token,
so roughly 130,000 characters of English). Over it, the server answers `400` and cuts nothing.
Limits: [API reference](../../get-started/references/api.md).

Measure in code before sending: `len(text) / 4` is close enough to choose a path.

## Pick the relevant part

Most questions need one part of a long document. Code finds it, VAKYN judges it.

- A contract: the clause the question is about, found by heading or section number.
- A log: the lines around the error, or the last N minutes.
- An email thread: the newest message plus the one it replies to.
- A long web page: the main text, without menus and footers.

Name the part in the state (`state.refund_clause`, `state.error_lines`), so the question can point
at it. If code cannot find the part, that record goes to the unsure path.

## Split, ask per part, combine in code

When the answer can sit anywhere in the document, split it into parts that each fit, with a little
overlap so no sentence is cut in two. Ask the same question about each part, sent concurrently
([batching](batching.md)). Then combine in code:

| The question | Combine | Example |
|---|---|---|
| Does any part show it? | **any**: the highest `noul` across parts | "Does the contract allow early exit?" |
| Does every part pass? | **all**: the lowest `noul` across parts | "Is every section free of personal data?" |
| How bad is the worst part? | **max**: the highest `score` across parts | "How severe is the worst error in this log?" |

Keep the part each answer came from, so a person can check it. Apply the thresholds to the
combined number.

A `choice` over the whole document ("which team?") does not combine well part by part. Pick the
part that carries the request (the opening, the subject, the latest message) and ask once.

## Say it in the design

Write in the design sheet which path each long input takes: the part picked, or the split and how
answers combine.
