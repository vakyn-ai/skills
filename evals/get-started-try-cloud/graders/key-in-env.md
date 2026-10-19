---
type: llm
---

PASS if the answer tells the person to keep the API key in an environment variable (VAKYN_API_KEY,
or TYPESAFE_API_KEY for the SDKs) or a git-ignored .env file, and not to paste it into the chat.
FAIL if it asks for the key in the chat, or suggests writing it into code or a tracked file.
