---
name: share
description: "Turn a VAKYN decision into a short playground link (vakyn.com/p/...) that someone else opens in the VAKYN console to see the request, run it and debug it. Use when someone wants to share a request, show a colleague or support a wrong or unsure answer, open their decision in the playground, or get a link or the JSON for a request. Works from a request file or JSON, from code that calls VAKYN (POST /v1/systemone), or from a decision described in words. Writing the questions from scratch: questions. A chat-model prompt or tool list: convert first."
---

# VAKYN share: a short playground link for a decision

The person has a decision (a state and its questions) and wants someone else to open it in the
VAKYN playground: to see the exact request, run it, change it and find out why an answer is wrong
or unsure. This skill builds the request JSON and, with an API key, a short link such as
`https://vakyn.com/p/k3x9m2pa`. Anyone signed in to VAKYN can open the link; running it charges
the organization of the person who runs it. Links are free and do not expire.

## Steps

1. **Find the decision.** One of:
   - a VAKYN request file or JSON: use it as it is;
   - code that calls `POST /v1/systemone`: take the `state` and `questions` it sends for the case
     in hand (the record that got the odd answer, if there is one), with real values, not variable
     names;
   - a decision described in words: write the questions with the `questions` skill's rules (an
     escape option, options and levels that describe themselves);
   - a chat-model prompt or tool list: run `convert` first, then come back.
2. **Write `vakyn-request.json`** next to their code: `state`, `questions`, and `model` only when
   they picked one. Check it with the `questions` skill's checklist. Never put an API key, a
   password or data the person did not choose to share into it; ask before including personal data.
3. **Make the link** when `VAKYN_API_KEY` is set (see [save the key](../get-started/references/cloud.md#save-the-key)):
   `python3 examples/share_link.py vakyn-request.json` prints the link. Or with curl:

   ```sh
   curl -s https://api.vakyn.com/v1/playground-links \
     -H "Authorization: Bearer $VAKYN_API_KEY" \
     -H "Content-Type: application/json" \
     -d @vakyn-request.json
   ```

   The answer is `{"id": "...", "url": "https://vakyn.com/p/..."}`. Give the person the `url`.
4. **No key:** give them the JSON file and say: sign in at vakyn.com/console/playground, or create
   a key at vakyn.com/console/keys and run step 3. The JSON is also what to paste into an LLM or a
   support message.
5. **Say what the other person sees:** the playground with the same state and questions, ready to
   run. To remove a link: `DELETE /v1/playground-links/<id>` with a key of the same organization.

## Rules

- One link per decision; for many records, pick the one that shows the problem.
- The link holds the request, never the key. Answers are not stored in the link: the person who
  opens it runs it again.
- Making a link is free; running it in the playground is a normal, charged call.
