# Evals

Each folder is one case for `claude plugin eval`: a `prompt.md` (what a person asks, with
frontmatter) and `graders/*.md` (how the run is scored). Name cases `<skill>-<what>` and tag them
with the skill name, so `make eval TAG=<skill>` runs one skill's cases.

```sh
make eval                      # every case, 1 run each, 4 at a time
make eval TAG=vakyn-convert    # one skill
make eval CASE='vakyn-limits'  # one case
```

`make eval` uses your Claude account (about $0.15 per case run) and then runs
`tests/eval_live.py`, which needs `VAKYN_API_KEY` and a server at `VAKYN_BASE_URL`.

## How a run works

- The agent runs in a throwaway sandbox with the plugin loaded, **no network and no environment
  variables from your shell**. It cannot reach open-server.
- So cases check behavior, and when a skill produces requests, the prompt asks the agent to **save
  each request as a `.json` file** in its folder.
- `tests/eval_live.py` reads every JSON request the agent wrote (from the run trace), runs the
  pre-send checklist on it and sends it to the real server. A request that fails either step fails
  `make eval`.
- Input files for a case go in `fixtures/` inside the case folder (copied into the agent's folder).

## Graders

| Type | Use for |
|---|---|
| `llm` | the main judgment: did the answer do the right thing. Write PASS and FAIL conditions. |
| `regex` with `match: not_contains` | things that must never appear (a key, GGUF, invented numbers) |
| `file_exists` with `path: "*.json"` | the agent saved what it was asked to save |
| `tool_used` | the agent did (or with `min: 0` / `max: 0`, did not) use a tool |

Keep every case's inputs synthetic and written for this repo.
