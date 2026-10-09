---
type: llm
focus: {source: file, path: vakyn-drift.yml}
---

The file is a GitHub Actions workflow.
PASS only if: it runs on pull requests (limited to paths with questions or prompts is fine, all
pull requests is also fine); it runs a script that re-runs a stored reference batch against the
test server and compares with the stored answers; the job fails when a limit is broken (non-zero
exit); and the API key comes from a GitHub secret, never written in the file.
FAIL if any of these is missing or a key value is written in the file.
