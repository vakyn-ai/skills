# Pre-send checklist

Run it on every request before sending it or writing it into code. Walk the list against the JSON
yourself; no script is needed. Fix every **must**; fix or consciously accept every **should**.

## Must (the server refuses otherwise)

1. Top level has `model`, `state`, `questions` and nothing else.
2. `state` is a string, object or array, not null.
3. `questions` is a non-empty object; each value has `type` and `instructions`, nothing beyond
   `type`, `instructions`, `criteria`.
4. `type` is `noul`, `choice` or `score`.
5. `choice`: `criteria` is an object with 2–255 options.
6. `score`: `criteria` is a list of 2–10 levels, lowest first.
7. `noul`: `criteria` is absent, or an object with only the keys `true` and `false`.
8. Size: state plus the longest question under 32,768 tokens; state plus all questions under 65,536
   (about 4 characters per token).

## Should (the server accepts, the answers suffer)

9. **Every option has a one-line description** that says what belongs in it, not just a label.
10. **A `choice` has an escape option** (`none`, `other`, `not_enough_evidence`, `ask_user`) unless
    every possible case truly fits one of the options.
11. **Every score level is described in words.** `"1"`, `"2"`, `"3"` are not levels.
12. **One proposition per `noul`.** "Is it urgent and about billing?" is two questions.
13. **Questions name their subject**, not a position: "Does `state.reply` answer the question in
    `state.ticket`?", not "Does the second text answer the first?". Never refer to "option 2".
14. **The state holds evidence, not conclusions.** Put the ticket, the policy, the page; not a chat
    model's opinion of them.
15. **Rules and arithmetic are in code**, not in the question ("if the amount is over 100 and…").
16. **Snake_case question names** that the code reads answers by.
17. **Untrusted text is marked as data.** User-written text sits under a key such as `message` or
    `page_text`; instructions live only in `instructions`.
18. **Independent questions share one request; dependent ones do not.** If question B needs A's
    answer, send B in a second request with A's answer in the state.
