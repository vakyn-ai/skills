"""Pick the next tool or step for a travel assistant. Standard library only, nothing to install.

VAKYN picks the step; your chat model still fills in the tool's arguments and writes replies.
Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import urllib.request

TOOLS = {  # one line per tool, from each tool's own description; no parameter schemas
    "search_flights": "Look up available flights for a route and date, without changing a booking",
    "change_booking": "Move an existing booking to another date or flight",
    "cancel_booking": "Cancel an existing booking and start a refund",
    "baggage_policy": "Look up baggage allowance and fees for a booking",
}
STEPS = {
    **TOOLS,
    "none": "No tool is needed: the assistant can answer from the conversation, or the user is just chatting",
    "ask_user": "Ask the user first: the request is vague or a detail the step needs is missing, such as which booking or the new date",
}
MIN_CONFIDENCE = 0.8  # starting value; set yours with check

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state: dict, questions: dict, timeout: float = 30.0) -> dict:
    """POST /v1/systemone; returns the answers by question name."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"]


def next_step(conversation: list[dict], steps_done: list[str]) -> str:
    answers = decide(
        {"conversation": conversation[-6:], "steps_done": steps_done},  # recent turns only
        {"next_step": {
            "type": "choice",
            "instructions": (
                "What should the travel assistant do next for the last user message in state.conversation? "
                "A tool step needs the booking and any new date to be known."
            ),
            "criteria": STEPS,
        }},
    )
    step = answers["next_step"]
    if step["choice"] not in STEPS or step["confidence"] < MIN_CONFIDENCE:
        return "chat_model_decides"  # unsure: let the chat model pick, as before
    return step["choice"]  # a tool name, "none" or "ask_user"


CONVERSATIONS = [
    [{"role": "user", "text": "I booked Berlin to Lisbon for 12 May, ref KX4P2Q."},
     {"role": "assistant", "text": "Found booking KX4P2Q: Berlin to Lisbon on 12 May, one passenger."},
     {"role": "user", "text": "Can you move it to the 19th instead? Same time of day if possible."}],
    [{"role": "user", "text": "How many bags can I bring on booking KX4P2Q?"}],
    [{"role": "user", "text": "Can you change my trip?"}],
    [{"role": "user", "text": "Thanks, that is all for today!"}],
]

for conv in CONVERSATIONS:
    step = next_step(conv, steps_done=[])
    if step in TOOLS:
        action = f"chat model fills the arguments for {step}, then the app calls it"
    elif step == "ask_user":
        action = "chat model writes one clarifying question"
    elif step == "none":
        action = "chat model replies without a tool"
    else:
        action = "chat model picks the tool itself (old path)"
    print(f"{step:18} -> {action:58} | {conv[-1]['text']}")
