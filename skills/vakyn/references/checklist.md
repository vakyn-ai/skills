# Pre-send checklist

Run it on every request before sending it or writing it into code. Walk the list against the JSON
yourself; no script is needed. Fix every **must**; fix or consciously accept every **should**.

## Must (the server refuses otherwise)

1. Top level has `model`, `state`, `questions` and nothing else.
2. `state` is a string, object or array, not null.
3. `questions` is a non-empty object; each value has `type` and `instructions`, nothing beyond
   `type`, `instructions`, `criteria`. `instructions` is a non-empty string, or an object or list
   (see 9).
4. `type` is `noul`, `choice` or `score`.
5. `choice`: `criteria` is an object with 2–255 options.
6. `score`: `criteria` is a list of 2–10 levels, lowest first.
7. `noul`: `criteria` is absent, or an object with only the keys `true` and `false`.
8. Size: state plus the longest question under 32,768 tokens; state plus all questions under 65,536
   (about 4 characters per token).

## Should (the server accepts, the answers suffer)

9. **Every option has a description** that says what belongs in it, not just a label. A
   description, a score level and `instructions` may be a string, or an object or list when the
   boundary has parts (what it covers, what it includes, what it is not). The server shows an
   object as `key: value` lines and a list as `- item` lines. Never empty, never null.
10. **A `choice` has an escape option** (`none`, `other`, `not_enough_evidence`, `ask_user`) unless
    every possible case truly fits one of the options.
11. **Every score level is described in words.** `"1"`, `"2"`, `"3"` (or `1`, `2`, `3`) are not levels.
12. **One proposition per `noul`.** "Is it urgent and about billing?" is two questions, and so is
    "Does it break the rules?" when the rule is "personal information or insults".
13. **Questions name their subject in plain words**, not a position: "Does the agent's reply answer
    the question in the ticket?", not "Does the second text answer the first?". `state.reply` also
    works. Never refer to "option 2".
14. **The instructions carry the whole meaning.** Question names (`refund`, `team`) never reach
    the model; they are only for your code. A question named `refund` with the instructions "Is
    it?" asks nothing.
15. **The state holds evidence, not conclusions.** Put the ticket, the policy, the page; not a chat
    model's opinion of them.
16. **Rules and arithmetic are in code**, not in the question ("if the amount is over 100 and…").
17. **Snake_case question names** that the code reads answers by.
18. **Untrusted text is marked as data.** User-written text sits under a key such as `message` or
    `page_text`; instructions live only in `instructions`.
19. **Independent questions share one request; dependent ones do not.** If question B needs A's
    answer, send B in a second request with A's answer in the state, or ask B up front with its
    premise written into it ("Suppose the message is about billing…") and read it only when A
    makes the premise true ([fan-out](../../vakyn-workflow/references/patterns/fan-out.md)).
