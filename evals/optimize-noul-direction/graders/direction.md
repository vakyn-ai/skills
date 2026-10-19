---
type: llm
focus:
  source: file
  path: "ironic.v2.request.json"
---

Judge only this one point; ignore everything else in the answer.
Most misses (81 of 95) are false negatives: ironic tweets the question said were not ironic, often
with #not or #sarcasm, or praise for something plainly bad.

PASS if the new rule targets the false negatives: it says what should count as ironic (for example a
hashtag such as #not or #sarcasm flips the literal meaning, or praise for an obviously bad event),
in the instructions or in a `true` description. FAIL if the main rule instead makes the question
stricter (fewer tweets counted as ironic) or targets the 14 false positives first.
