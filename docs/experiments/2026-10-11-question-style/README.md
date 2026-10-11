# Question style tests (2026-10-11)

Two questions about how to write VAKYN requests:

1. **Field references.** Does it matter how a question names the state field it is about:
   `state.x`, a backticked path, plain words ("Bob's message") or a position ("the second
   message")?
2. **Option descriptions.** Do structured option descriptions (an object with what the option
   handles, includes and is not) beat plain one-line descriptions, and beat the same words
   written as one long string?

## Conditions

VAKYN-4B Q8_0 on open-server, one RTX 5090, requests sent one at a time, model `jev-latest`.
All messages are synthetic and written for this test.

## Results

| Script | Test | Result |
|---|---|---|
| `ab.py` `test1` | 2 messages, flat and nested state, 8 propositions, 32 `noul` per row | Every style 32/32 right; lowest p(right) 0.94 to 0.99 |
| `ab2.py` | 4 similar messages in a thread, ask about one, 128 `noul` per style | Every style 128/128 right. Lowest p(right): plain name 0.93, `state.` path 0.76, plain position 0.76, backtick 0.68 |
| `ab.py` `test2` | 20 routing messages, 5 teams | All three styles 20/20 |
| `ab3.py` | 20 harder routing messages, 5 teams | structured 18/20 (mean p(right) 0.886), long string 17/20 (0.861), plain 16/20 (0.824) |

Full output: `results.txt` (summary) and `ab-run1.txt` (first run of `ab.py`).

## What we take from it

- Plain words that name the field kept the hardest cases furthest from 0.5. `state.x` and
  backticked paths also work.
- On the harder routing set, structured descriptions got two more right than plain ones. The
  sample is small, and most of the gain comes from the extra information (what each team
  includes and does not handle), not from the format: the same words as one string got 17/20.

## Re-run

Needs a running server and a key in `VAKYN_API_KEY` (base URL from `VAKYN_BASE_URL`, default
`http://127.0.0.1:8080`):

```sh
python3 ab.py    # test 1 and test 2
python3 ab2.py   # test 1b
python3 ab3.py   # test 2b
```

Numbers can move a little between model files and machines.
