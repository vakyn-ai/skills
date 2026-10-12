# Report template

Write the report as `vakyn-research.md` at the root of the person's repo (or the current folder
when there is no code). Fill every section; write "none found" rather than dropping one. Keep it
plain: short sentences, numbers with their source.

```markdown
# Where VAKYN can help: <app or process name>

Researched <date> from <code at commit abc123 | a process description | code and call logs from <dates>>.
No code was changed and no calls were made.

## Summary

1. **<spot>**: <one line: what it decides, why it is first>.
2. **<spot>**: <one line>.
3. **<spot>**: <one line>.

<One sentence on what stays with the chat model (the keep list).>

## Ranked spots

| # | Where | Decides | Question type | Gain | Risk | Effort | Priority | Next skill |
|---|---|---|---|---|---|---|---|---|
| 1 | `src/triage.py:22` | spam or real request | `noul` | High (3) | Medium (1) | Small (0) | 5 | `convert` |

Priority = 2 × gain − risk − effort (gain High 3 / Medium 2 / Low 1; risk and effort High or
Large 2 / Medium 1 / Low or Small 0). Ties go to the lower risk.

## Spot details

### 1. <name> (`file:line` or process step)

- **Decides:** <the judgment, in one sentence>.
- **Today:** <model>, <calls a day> (<log | code | assumed>), <tokens per call>, <cost a day or
  month>, <wait time or "background">.
- **VAKYN question:** `<type>`; <options or levels in brief, with the escape option>. State: <what
  evidence goes in>.
- **Risk:** <what a wrong answer does downstream>. <How unsure answers are handled: person, chat
  model, review queue>.
- **Effort:** <Small | Medium | Large>: <what changes>.
- **Next:** `convert` <for an existing prompt or tool list> | `workflow` <to build it
  fresh>.

## Keep with the chat model

| Where | What it writes | Why |
|---|---|---|
| `src/replies.py:11` | first reply to the customer | free text |

## Does not fit

| Where | What it does | Why not |
|---|---|---|
| <spot> | <...> | needs live data / free text / evidence over 32,768 tokens / arithmetic |

## Assumptions and open questions

- <Every assumed number, with what it rests on.>
- <Questions for the person: volumes, prices, who reads the result.>

## Next steps

1. Pick one or more spots from the table.
2. Run the named skill on it: `convert` for an existing prompt or tool list,
   `workflow` to design a new step. `questions` helps write the questions.
3. Test on about 30 of your own records with `check` before switching anything.
```

A finished example: [examples/helpdesk-py/vakyn-research.example.md](../examples/helpdesk-py/vakyn-research.example.md).
