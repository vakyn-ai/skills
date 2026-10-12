# Triage first, stop early: open only what could change the outcome

**Use when** a case comes with a list of items to investigate, each costly to open (fetch the
full article, run a research agent, pull a record), and one bad item settles the case: search hits
in supplier due diligence, alerts behind an incident, documents behind a claim.
**Not when** every item must be read anyway (a full audit), or opening is as cheap as asking.

The idea: **ask one `noul` per item, all in one request: "could this item change the outcome if
…?"**. Open the dangerous ones first, in parallel. Stop as soon as the outcome is settled, or
nothing left could change it. Record every item that was not opened, and why.

## The request

[examples/triage-first.request.json](../../examples/triage-first.request.json): the supplier, the
list of blockers and the 12 search hits (date and snippet) in the state; one `noul` per hit. Each
question **states its premise**, so identity is left to the next step: "Suppose search hit h01 in
state.hits is about the supplier in state.supplier, even if the name, place or company type
differs. Does the hit report one of the blockers in state.blockers?"

The premise matters. A first version asked "If hit h01 is about the supplier, could it stop the
onboarding?" and VAKYN-4B answered 0.06 for "Harlow Castings Inc. of Ohio fined for falsifying
safety test records" and 0.43 for a sanctions listing of "Harlow Trading LLC": it judged the name
match, not the blocker, so h01 would never have been opened. With the premise stated, they answer
0.95 and 0.98.

## The code

[examples/triage_first.py](../../examples/triage_first.py)

1. One request for all hits. A hit below `COULD_STOP_AT` (0.2) cannot change the outcome: not
   opened, with its number as the reason. Unsure counts as dangerous.
2. Order the rest by the `noul`, highest first, and open them in waves of three in parallel.
   Opening is a stub here (`open_hit`); in the app it is a fetch or a research agent.
3. Each opened hit gets a second request: `same_company` (`noul`) and `blocker` (`choice` with
   `none`). Code applies the rules: the 3-year look-back on the source date, the cut-offs.
4. After each wave: a confirmed blocker stops the review; the hits still waiting are recorded as
   "outcome already decided". An unsettled hit goes to a person.

Run on the 12 hits (VAKYN-4B, CPU-only server): h03 (winding-up petition) 0.99, h12 (an
environmental fine) 0.99, h08 (sanctions, another company) 0.98 opened first; h03 is this supplier
and a blocker, so the review stops. h01, h05 and h07 (0.95, 0.63, 0.34) were waiting and are
recorded as not opened, outcome decided; six below 0.2 were never opened. **3 of 12 opened.**
The same search without h03: six opened in two waves (h12 too old to block, the others another
company or no blocker), five below 0.2 not opened, outcome clear. **6 of 11 opened.**

## Unsure path

- Triage: unsure is dangerous. The cut-off is low on purpose; set it from labeled cases with
  the cost of a missed blocker ([cost-based cut-offs](../../../vakyn-check/references/thresholds.md#when-one-kind-of-mistake-costs-more)).
- Confirm: `same_company` or `blocker` below its cut-off → a person, with the article.
- The record per case lists every item: its triage number, opened or not, why, and the verdict.
  That record is what a reviewer reads when asking "did you look at hit 7?".

## Common mistakes

- **Folding identity into the triage question.** "Is this about our supplier and bad?" lets a
  name mismatch hide a blocker. Triage asks about the blocker under a stated premise; identity is
  checked after opening.
- **Opening in list order.** The search engine's order is not the risk order.
- **Stopping without a record.** An item not opened must say why: below the cut-off, or the
  outcome was already decided.
- **Rules in the question.** "More than three years ago does not count" is a date rule: code.
