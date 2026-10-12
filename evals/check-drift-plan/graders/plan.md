---
type: llm
---

The agent works offline with no server, records or key, so it can only write a plan and files; judge
the plan. Nothing has to have been run or saved yet; a plan that explains these steps is enough.

PASS only if the plan covers all of these:
1. A stored reference batch: a fixed set of representative records (roughly 100 to 300, covering
   every option and hard cases) whose answers are saved once on the setup they trust (the old
   model file, as production runs it) and re-run after the change, compared record by record.
   Comparing two fresh runs with nothing stored, or only eyeballing a few tickets, is not enough.
2. What is stored with the answers, at least the model name or model file, and a question text
   version or hash or request id, so a later run can tell what changed.
3. Low concurrency (1 or 2 requests in flight) for the reference and re-runs, because answers can
   move slightly between runs under concurrent load.
4. A noise tolerance: changes below a small amount (about 0.04 to 0.05) count as noise, not drift.
5. What the report shows: share of picks that changed, size of the confidence changes, records
   crossing the 0.8 threshold, and the changed records to review; with pass or fail limits the team
   sets.
6. A CI job on pull requests that change questions or prompts, which runs the check against the
   test server and fails when a limit is broken, with the key from a secret.
FAIL if any point is missing, if it says the upgrade can be trusted without such a check, or if it
invents measured numbers for this server (for example how many answers changed).
