# Grouping misses by kind

A round adds one rule per **group** of misses, not one per case. Grouping is what keeps the rules
general: ten cases that fail the same way need one sentence, and a case that fails alone is
usually noise or a wrong label.

`optimize.py` prints the groups on the dev set, biggest first, with a few cases each.

## Per question type

| Type | Group by | Example group |
|---|---|---|
| `choice` | the pair (right option → picked option) | `DSP -> CRD: 4` (payments the customer did not make, picked as card problems) |
| `noul` | false positives (said true, label false) vs false negatives (said false, label true) | `false negative: 7`, `false positive: 1` |
| `score` | too high vs too low (and by how many levels) | `too high: 6` |

## Reading a group

1. **Read three to five cases** of the group, side by side with the option descriptions (or the
   `true` / `false` descriptions, or the levels) the model saw.
2. **Name what the cases share** in one line: "all mention a lost card and a payment they did not
   make", "sarcasm with a positive word and a hashtag", "complaints with polite wording".
3. **Find the cause** in [diagnose](../../questions/references/diagnose.md):

| What the group shows | Usual cause | Rule to write |
|---|---|---|
| Codes or one-word labels picked almost at random | Bare or coded options (`"CRD": "CRD"`) | Describe every option in one line: what belongs in it |
| One pair dominates (`A -> B` many times, `B -> A` some) | The boundary between A and B is not said | One sentence on the boundary, in both descriptions or the instructions |
| A cue that flips the meaning (a hashtag, "thanks a lot", quotes) | The model reads the cue literally | State what the cue means in this flow |
| Mostly one direction for a `noul` | `true` / `false` not described, or the bar is unclear | Describe the side that is missed (`true`: "counts even when…") |
| `score` too high or too low across the board | Levels not described by what you would observe | Describe each level with what the input shows at that level |
| Cases that fit no option | No escape option | Ask the person; adding an option changes the keys |
| Cases whose deciding fact is not in the state | Missing evidence | Not a wording fix: change the state (`questions` skill) or accept the miss |

## When not to write a rule

- **One case alone**: check the label first. A wrong label is fixed in the cases file, and the
  person decides; never relabel to make the wording look better.
- **The deciding fact is missing** from the state: no wording can fix it. Say so.
- **The group needs arithmetic or a date** ("over 30 days"): compute it in code and pass the
  result ([state](../../questions/references/state.md#move-exact-work-into-code)).
- **The fix would rename or add an option**: ask the person first; see the rules in the skill.

## Two-direction groups

For `choice`, look at both directions of a pair before writing. `DSP -> CRD: 4` and
`CRD -> DSP: 1` is one boundary: write the rule once, from the side that is missed more, and check
that the reverse group does not grow next round. For `noul`, a rule that fixes false negatives
often adds false positives; the score on dev shows whether the trade is worth it.
