# Evals

Each folder is one case for `claude plugin eval`: a `prompt.md` (what a person asks, with
frontmatter) and `graders/*.md` (how the run is scored). Name cases `<skill>-<what>` and tag them
with the skill name, so `make eval TAG=<skill>` runs one skill's cases.

```sh
make eval                      # every case, 1 run each, 4 at a time
make eval TAG=vakyn-convert    # one skill
make eval CASE='vakyn-limits'  # one case (one name or glob)
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
- **Input files** (a sample app, a log): put them in `fixtures/` inside the case folder and use a
  `case.yaml` instead of `prompt.md` with `context: {add_dirs: [fixtures]}`. The agent gets them as a
  read-only extra working directory, not in its own folder, so tell it to save outputs in the current
  folder. See `evals/vakyn-research-python-app/case.yaml`. Small inputs can go inline in the prompt.
- An `llm` grader can judge a file the agent wrote: `focus: {source: file, path: <name>}`.

## Graders

| Type | Use for |
|---|---|
| `llm` | the main judgment: did the answer do the right thing. Write PASS and FAIL conditions. |
| `regex` with `match: not_contains` | things that must never appear in the final message (a key, GGUF, invented numbers); it cannot read a saved file, use `llm` with `focus` for that |
| `file_exists` with `path: "*.json"` | the agent saved what it was asked to save |
| `tool_used` | the agent used a tool; for "never used", set both `min: 0` and `max: 0` |

Keep every case's inputs synthetic and written for this repo.
