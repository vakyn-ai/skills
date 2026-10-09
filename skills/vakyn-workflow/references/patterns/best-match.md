# Pick the best match: one item from a short list

**Use when** a search, a catalog or a template library gives a few candidates and one must be
picked for this case: the help article for a question, the product for a request, the reply
template for a ticket.
**Not when** the list is long (search or filter first) or the pick follows a rule (cheapest,
newest): sort in code.

## The request

[examples/best-match.request.json](../../examples/best-match.request.json): the customer's
question in the state; one `choice` whose options are the candidates, named by their own ids
(`hc_311`), each described as "title: summary", plus `no_good_match`.

Answer from a running VAKYN 4B: "How do I stop the weekly summary emails? I still want alerts when
a payment fails." → `hc_311` (Notification settings), confidence 1.00, over the unsubscribe and
failed-payment articles.

## The code

[examples/best_match.py](../../examples/best_match.py)

- Code removes candidates that fail a hard rule (wrong language, unpublished, out of stock, over
  budget) and keeps the top 20 at most.
- The options are built per request from what is left: `{id: "title: summary"}` plus `no_good_match`.

Run on three questions: weekly summaries → `hc_311`; "My card was declined" → `hc_118`; "Can I pay
by bank transfer?" (no article covers it) → `no_good_match`, handed to a person.

## Unsure path

`no_good_match` or confidence below `MIN_CONFIDENCE` → no article is shown; the question goes to a
person or the chat model. A wrong article is worse than none.

## Common mistakes

- **Items by position.** `option_1`, "the third result" or a list in the state with "pick one of
  the above". Use the item's own id as the option name.
- **Constraints in the question.** "Under $50 and in stock" is a filter in code.
- **No `no_good_match`.** Search always returns something; the closest of five bad articles is
  still bad.
- **The search score in the state.** It pulls the pick toward the search's opinion. Give the content.
