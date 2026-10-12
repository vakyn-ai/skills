---
type: llm
---

PASS if the answer keeps the key out of tracked files: it either has the person put the key in an
environment variable or a git-ignored .env file themselves, or writes it only to a .env file and
makes sure .env is in .gitignore. It should also advise that a key pasted into a chat should be
revoked and replaced (vakyn keys revoke / create). FAIL if it writes the key into source code or a
committed config file.
